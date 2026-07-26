# Real-time feed + connect UX plan (RCA-grounded, reviewed v2)

Date: 2026-07-26. Follows the classification redesign ([classification-redesign-plan.md](classification-redesign-plan.md)). Root causes verified against live backend logs, Supabase rows, and a live Composio probe (a real GitHub issue created and timed). Reviewed 2026-07-26 by three compound-engineering agents (architecture, flow-completeness, simplicity); v2 folds in their findings — the mitigations are leaner and three real gaps (disconnect purge, cold-start heavy sync, `held`-as-pill-signal) are fixed.

**Status: REVIEWED — awaiting approval. Crucial decisions at the end.**

---

## The evidence

- **Webhook path works, ~24s.** Probe: issue created `14:29:54` → `/webhooks/composio` `14:30:16` → `classify_item` `14:30:18`.
- **`/feed/refresh` fires every ~5–8 min, never on connect.** Timeline `14:01 → 14:06 → 14:12 → 14:20`; no refresh timer exists.
- **Composio propagation delay is real** (Gmail unusable ~10 min post-link). Mitigate, not eliminate.
- **Linear "all urgent" is correct overdue data**, not a bug.

## North star (validated by all three reviews)

The stored feed is the source of truth. Webhooks keep it current (`ingest → classify_item`); the client re-reads it cheaply. **No periodic provider polling.** Dedup/ordering between a webhook item and the connect-refresh is safe — both collapse on `(user_id, source_ref)` at `upsert` (`feed_repository.py:97`), ranking recomputed at read (`feed.py:198`).

- **Heavy sync (`POST /feed/refresh` = poll all providers + classify)** runs only on **connect** (made reliable) and **manual pull-to-refresh**.
- **Cheap `GET /feed`** (a DB read, `load()`) runs on **launch, foreground, and tab-switch to Day/To-dos** — this is what surfaces webhook-appended rows. Not a timer, not a provider poll.

---

## Cluster A — Reliable connect-refresh + cheap reads (issues 2, 3, 9)

**Root cause.** `connectSource` (`App.tsx:428-446`) fires `refresh()` only inside a 15×1s poll that usually times out on web OAuth; the foreground handler (`App.tsx:298-319`) only calls `loadSources()`, never the feed; no refresh timer. Day/To-dos read stored `/feed`; Activity/Later read live endpoints — hence the split.

**Fix (leaned).**
1. **Flip-detection with a hydration guard.** Track connected sources by `connected_account_id` (`SourceInfo`, already on the wire), not the `status` string. The **first** `loadSources()` of a session establishes the baseline **without firing** anything (so a cold launch, where the skeleton starts all-disconnected, is not read as N fresh connects). Only a genuine new `connected_account_id` on a later read counts as a connect → fires one `refresh()` + starts the pill. This also ignores `expired→connected` reconciliation.
2. **Single-flight `refresh()`.** Guard so concurrent connects and a pull-during-connect coalesce into one in-flight sweep instead of N overlapping full-provider polls.
3. **Cheap `load()` (`GET /feed`) on foreground and on tab-switch to Day/To-dos**, so a webhook item that landed while backgrounded or while on another tab is seen.
4. **To-dos gets pull-to-refresh** (parity with Day).
5. **One deferred retry, not a loop.** If the just-connected source landed **zero rows** in the connect-refresh, schedule a single re-`refresh()` ~30–45s later (covers the short propagation slice). Longer propagation is covered by the next foreground/pull. (See Decision 3 for the backgrounding caveat.)
6. **Cold-start is a cheap read, not a heavy sweep.** Today the mount effect runs a full `refresh()` every launch (`App.tsx:280-282`) — contradicts the north star. Change mount to `load()`; heavy sync stays reserved for connect + pull. (See Decision 1.)

**Seam.** All client-side (`App.tsx`); the `refresh()`/`load()` contracts are unchanged.

## Cluster B — Global syncing pill above the footer (issues 1, 11)

**Root cause.** `syncing` set only in the fragile connect branch, fixed 4s countdown (`App.tsx:462-473`) decoupled from the ~40s backfill, rendered only on You (`YouScreen.tsx:232-250`).

**Fix (leaned — all three reviews rejected `held` gating).** State = `syncingSources: Set<Source>`. `connectSource` adds the source before the connect-`refresh()` and removes it in a `finally` (extended over the single deferred retry if used). A presentational `SyncPill` renders globally, centered just above the footer, with a spinner ("Syncing…" or the source names). **No countdown, no `held`/`per_source` gating** — the completion signal is the `refresh()` promise resolving. The pill means "we tried"; a source still propagating past the retry is covered by the later foreground read (Decision 7).

**Seam.** New `SyncPill` component + `syncingSources` state in `App.tsx`. No backend change; delete the `secs` field, the countdown effect, and the `held` plumbing from the pill.

## Cluster C — Activity "could not read" (issue 4)

**Root cause.** Server always returns 200; the failure is the client 60s `DASHBOARD_TIMEOUT_MS` (`client.ts:30`) aborting. The overview fires every source's dashboard in parallel (`ActivityScreen.tsx:74-87`); GitHub's `repo_activity` ≈ 27 calls / 24-wide (`composio_github.py:307`) and Linear's `my_issues` up to 20 serial pages (`linear.py:260`) cross 60s under contention. Drill-in is one uncontended call + warm 60s cache (`stats.py:117,146`).

**Fix (leaned — one approach, not three).** Make the **overview lite**: it requests summary-level data only (`activity_summary` = 2 calls, already wired at `stats.py:214`), via a `?detail=summary` param (or a lite board variant) on `GET /sources/{provider}`. The **drill-in stays rich** (unchanged endpoint call with full `repo_activity`/stats). The heavy work leaves the contended path entirely, so the overview cannot approach 60s. **Dropped as YAGNI:** the server soft-time-budget and the GitHub fan-out / Linear pagination tuning (a Linear-pagination cap is a deferrable drill-in cost optimization, not needed for issue 4).

**Seam.** `stats.py` (a summary-only build path), `main.py` `/sources/{provider}` (accept `detail`), `client.ts`/`ActivityScreen.tsx` (overview passes `detail=summary`, drill-in doesn't).

## Cluster D — Calendar current-day-only + timing copy (issues 6, 8)

**Root cause.** Backend feed leak: 18h rolling window, no day boundary (`calendar.py:101`, `DAY_AHEAD=18h`). Frontend copy: "next in N" (`YourDayScreen.tsx:332`) fed by `ahead` (filtered only `end>now`), while the count uses day-filtered `todayMeetings` — mismatch; ring gets unfiltered meetings (`YourDayScreen.tsx:157`).

**Fix (leaned — no tz plumbing into the poll).** The calendar band already receives `tz` at read time (`tier_bands.py:89`, `_calendar_tier`), and the Linear band right below it already does `now.astimezone(tz).date()` (`tier_bands.py:104-116`). So:
- **Backend, read-time:** drop a `calendar_meeting` whose start is not the user's local today (mirror the Linear band, reusing the `tz` already flowing to `effective_tier` / the passed-meeting drop in `feed.list_feed`); keep `calendar_invite` (needsAction) regardless of day. **No change to the poll, `event_to_raw_event`, or `/day`.**
- **Frontend:** derive `next` from a day-filtered `ahead` and pass day-filtered meetings to `DayRing` (mirror the existing `todayMeetings` filter). `/day` staying wide is correct — the client owns the day boundary by design (`calendar.py:271-279`).

**Seam.** `tier_bands.py` (calendar-day check) or `feed.py` list_feed drop; `YourDayScreen.tsx` (day-filter `ahead`+ring).

## Cluster E — UI polish (issues 5, 10)

- **Name row.** Header already shows the name (`YouScreen.tsx:98,112`); delete the separate row (`YouScreen.tsx:116-140`). Add a `right` slot to `ScreenHeader` (`Chrome.tsx:26-46`) with an inline "Edit" (name set) / "Add your name" (absent) chip.
- **Later collapsed header.** `CollapsedTitle` is **shared** — the Day screen imports it too (`YourDayScreen.tsx:21`), so delete only the **usage** in Later (`LaterScreen.tsx:313`), not the symbol (unless Decision 6 removes it from Day as well).

## Cluster G — Live feed stream (append to an open screen, NEW)

**Requirement (Vicky):** when a trigger pings the backend while the app is open on Home/To-dos, the new item must **append live**, not wait for the next foreground/tab-switch. Not needed for Later.

**Design (rides on the Redis work):**
- `GET /feed/stream` — an SSE endpoint per user, same pattern as `/later`.
- On webhook ingest, after `classify_item`, publish the classified row to Redis channel `feed:{user_id}:events`.
- `/feed/stream` subscribes to that channel and forwards each new row; the open Home/To-dos screen **appends** it — dedup by `source_ref`, apply the action-ledger overlay, re-rank — with no full refresh and no polling.
- Held items are not published until classified (the webhook classifies first). Later does not subscribe.

**Seam:** new `/feed/stream` route + a Redis pub/sub publish in the webhook ingest path; a client SSE subscription on Home/To-dos that appends to the in-memory feed. Depends on Redis (Cluster 3 / Phase 0).

## Cluster F — Disconnect purges stored rows (NEW, from flow review)

**Root cause.** `disconnect` (`connections.py:230-240`) removes the Composio account + connection row but **never deletes that source's `feed_items`**, so they keep showing on Day/To-dos, keep counting, and stay in the Later exclusion set after a disconnect.

**Fix.** On `disconnect`, purge stored feed items for `(user_id, source)` and clear any pill/counts for it. Add a repo method `delete_by_source(user_id, source)`; call it from `ConnectionService.disconnect`.

**Seam.** `feed_repository.py` (both impls) + `connections.py`.

## Small robustness (from arch review)

- `_classify_soon` (`ingest.py:229-241`): if the background submit itself throws (pool saturated), the webhook item is left held forever. Mark it attempted (visible at ceiling) before/around the submit so the poll-only safety net still applies.

## Not in scope / not bugs

- Linear no-trigger (poll-only by design; deterministic tiering covers it). Linear per-team triggers + GitHub-notification foreground reads stay **deferred** (Decision 2) — do not let them creep in.
- Linear "all urgent" = real overdue data.

---

## Crucial decisions (please confirm)

1. **Cold-start + foreground are cheap `GET /feed`, not heavy sync.** Heavy provider sync runs only on connect + manual pull. Consequence: on app open, poll-only sources (Linear, GitHub notifications) show their last-synced state until you pull; webhook sources are current. This is the north star made literal — confirm you want cold-start to stop doing a full sweep.
2. **Poll-only staleness accepted** (Linear/GitHub-notification changes after connect wait for the next connect or manual pull). Recommend accept; defer Linear triggers.
3. **Propagation retry = one deferred client retry (~30–45s) for a zero-row source.** Lean, but a client timer can be suspended if you background the app right after OAuth; the longer tail then falls to foreground/pull. Accept the lean version, or invest in a backend per-source retry (more machinery, survives backgrounding)?
4. **Activity overview goes lite** (summary only), rich on drill-in. Overview becomes lighter but reliable. OK?
5. **"Next in N" when the next meeting is tomorrow** — label it "Tomorrow 1:15pm" or hide it from the day view?
6. **Collapsed sticky header** — remove from Later (confirmed). Also from the Day screen ("Good evening" on scroll), or Later only? (Determines whether the shared `CollapsedTitle` symbol can be deleted.)
7. **Pill = "we tried", cleared when the connect-refresh resolves.** A source still propagating past the retry clears the pill anyway (data fills on next foreground) rather than spinning. A failed source (`ConnectedAccountNotFound`) is indistinguishable from a genuine 0-item source in the pill. Acceptable, or should a still-connecting source show a distinct soft state?

---

## Build order

1. **E** (isolated, quick) + **F** (disconnect purge, small, high correctness value).
2. **A + B** (the core lag + pill — one coherent connect/refresh lifecycle change; fix the hydration guard and drop `held`-gating first, per the reviews).
3. **D** (calendar).
4. **C** (Activity lite overview).

Backend changes follow RGR; each cluster deploys to EC2 and is verified live via the logging + browser loop.
