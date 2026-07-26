# Real-time feed + connect UX plan (RCA-grounded)

Date: 2026-07-26. Follows the classification redesign ([classification-redesign-plan.md](classification-redesign-plan.md)). Every root cause below was verified against live backend logs, the Supabase rows, and a live Composio probe (a real GitHub issue created and timed end to end). File:line references are to the current tree.

**Status: DRAFT — for review + approval. Crucial decisions flagged at the end.**

---

## The evidence

- **Webhook path works and is fast.** Probe: GitHub issue created `14:29:54` → `POST /webhooks/composio` `14:30:16` (22s, Composio's own trigger latency) → `classify_item` `14:30:18`. So a triggered event reaches the stored feed in ~24s.
- **`/feed/refresh` fires every ~5–8 min, never on connect.** Session timeline: `14:01:57 → 14:06:42 → 14:12:31 → 14:20:44`, each landing the *previous* connect's data. There is **no refresh timer in the app**; the gaps are just whenever the user next triggered a full refresh.
- **Composio account propagation delay is real.** Gmail linked ~`14:10` but every refresh returned `ActionExecute_ConnectedAccountNotFound` for gmail until `14:20`. Partly upstream; we can mitigate, not eliminate.
- **Linear "all urgent" is correct data**, not a bug: 9 rows have overdue due dates (→ urgent), 6 have none (→ can_wait), exactly per the locked Linear rule.

---

## Architecture decision (the north star)

**Do not periodically re-poll providers.** A timer that fires `/feed/refresh` every N seconds is the heavy, wrong design. Instead, three distinct mechanisms, each matched to its cost:

1. **Heavy provider sync (`POST /feed/refresh` = poll every provider + classify)** runs **only**:
   - once on **connect** (made reliable — see Cluster A), and
   - on **manual pull-to-refresh** (user-initiated).
2. **Ongoing real-time updates come from webhook triggers.** A trigger (GitHub issue-assigned, Slack DM/channel, Gmail new message, Calendar starting-soon) already appends its item to the stored feed via `ingest → classify_item` (shipped in the redesign). Nothing periodic needed for these.
3. **The client surfaces webhook-appended items with a cheap `GET /feed` read** — a single DB read, not a provider re-poll — on **app launch and on foreground**. This is the minimal thing that lets a webhook-delivered item become visible without a heavy sync. (See Crucial Decision 1.)

Net: the feed is a durable store that webhooks keep current; the app reads it cheaply when opened, and only pays the heavy provider sync on connect or explicit pull.

---

## Cluster A — Reliable refresh-on-connect + cheap foreground read (issues 2, 3, 9)

**Root cause.** `connectSource` (`App.tsx:428-446`) does call `refresh()` and set the pill, but only inside a 15×1s poll loop that usually times out before it catches `connected` on web OAuth (no reliable redirect back). The foreground/focus handler (`App.tsx:298-319`) only calls `loadSources()` — it re-reads connection status, never the feed. There is no refresh timer. So Day/To-dos serve stale stored rows until a manual Day pull-to-refresh (and To-dos has no pull-to-refresh at all). Day + To-dos read stored `/feed`; Activity reads live `/sources`; Later reads live `/later` — which is why only the latter two look instant.

**Fix.**
- Track the connected-source set across `loadSources()`. When a source **flips** disconnected→connected (detected in the foreground handler or the status poll), fire **one** full `refresh()` (feed + `/feed/refresh` + day + later + activity) and start the pill. This catches the web-OAuth case the 15×1s loop misses.
- Keep a **bounded post-connect retry** (e.g. re-run `/feed/refresh` a few times over ~90s) so a source still propagating on Composio's side fills in without user action. Stop early once that source reports rows.
- On **foreground/launch**, do a cheap `GET /feed` read (`load()`), so webhook-appended items surface. **Not** a `/feed/refresh`, **not** a timer.
- Give **To-dos** a pull-to-refresh (parity with Day).

**Seam.** The connect-detection lives in the sources-reconciliation path; `refresh()` and `load()` are the existing contracts. No backend change.

---

## Cluster B — Global syncing pill above the footer (issues 1, 11)

**Root cause.** `syncing` state (`App.tsx:163`) is set only in the fragile connect-success branch (`App.tsx:438`), counts down a fixed **4s** (`App.tsx:462-473`) decoupled from the ~40s Gmail backfill, and renders only on the You screen (`YouScreen.tsx:232-250`). So it usually never shows on web OAuth, and when it does it is gone before data lands.

**Fix.** A single **global pill**, centered, pinned just above the footer, visible on every tab, with a spinner and "Syncing {source}…". Lifecycle driven by the **refresh/backfill lifecycle**, not a timer: it appears when a connect-refresh starts and clears when that refresh completes and the source's held/pending count reaches 0 (`RefreshResult.held`, already on the wire). Navigation stays free while it shows.

**Seam.** New presentational `SyncPill` component + a `syncing` state machine in `App.tsx` fed by the refresh lifecycle. No backend change (the `held` count already ships).

---

## Cluster C — Activity "could not read this source right now" (issue 4)

**Root cause.** Not a server error — `GET /sources/{provider}` always returns 200 with `unavailable` appended (`stats.py:164-181`). The failure is the client 60s `DASHBOARD_TIMEOUT_MS` (`client.ts:30`) aborting. The Activity overview fires **all** connected sources' dashboards in parallel (`ActivityScreen.tsx:74-87`). GitHub's board runs `repo_activity` ≈ **27 GitHub calls, 24 concurrent** (`composio_github.py:307-371`), throttled by GitHub Search limits; Linear runs `my_issues`, **up to 20 serial paginated calls** (`linear.py:260-299`). Under overview contention they cross 60s → abort → the string at `ActivityScreen.tsx:80-84`. Drill-in is one uncontended call and hits the warm 60s server cache (`stats.py:117,144-151`), so it works; backing out re-fires the burst.

**Fix (options, pick in review).**
- **Overview cheap, drill-in rich:** overview shows only the cheap summary (`activity_summary`, 2 calls) and headline counts; defer `repo_activity` / full Linear stats to the drill-in. Biggest win, changes overview richness.
- **Bound the heavy reads:** cap Linear pagination for the dashboard (e.g. first 2–3 pages) and reduce GitHub `repo_activity` fan-out (fewer repos, longer cache); add a server-side soft time budget so a source returns partial-with-`unavailable` instead of running to 60s.
- **Frontend:** sequence the overview calls (small concurrency) instead of all-at-once, and on abort show a retry/"still loading" state rather than a hard error.

**Seam.** `stats.py` per-source builders, `composio_github.py.repo_activity`, `linear.py.my_issues` (a bounded variant), `ActivityScreen.tsx` fetch orchestration.

---

## Cluster D — Calendar current-day-only + timing copy (issues 6, 8)

**Root cause.** Backend: `event_to_raw_event` uses an 18h rolling window (`calendar.py:101`, `DAY_AHEAD = 18h` at `calendar.py:31`) with **no calendar-day boundary and no user tz**, so tomorrow-1:15pm enters as `calendar_meeting` tiered "today". Frontend: the "next in N" copy (`YourDayScreen.tsx:332`) is fed by `ahead` (filtered only `end>now`, not day-filtered), while the count uses the correctly day-filtered `todayMeetings` (`YourDayScreen.tsx:111-114`) — hence "No meetings today, next in 17h". The ring also gets unfiltered `meetings` (`YourDayScreen.tsx:157`).

**Fix.**
- Backend: constrain `calendar_meeting` to the user's **calendar day** (thread the user tz — the same tz the feed already receives — into the calendar poll / `event_to_raw_event`). Keep invites (`needsAction`) regardless of day; keep in-progress meetings.
- Frontend: day-filter `ahead` and the ring the same way `todayMeetings` already is; fix "next in N" to only consider today (see Crucial Decision 5 for the tomorrow case).

**Seam.** `calendar.py` (tz param), the calendar poll caller, `YourDayScreen.tsx` (reuse the existing day filter).

---

## Cluster E — UI polish (issues 5, 10)

- **Name row (issue 5).** The You header already shows the name (`YouScreen.tsx:98,112`); the bug is the separate name row (`YouScreen.tsx:116-140`). Add a `right` slot to `ScreenHeader` (`Chrome.tsx:26-46`), render an inline "Edit" (name set) / "Add your name" (absent) chip there, and delete the row. No standalone name listing either way.
- **Later collapsed header (issue 10).** Delete `CollapsedTitle` at `LaterScreen.tsx:313` (purely a sticky mini-title; safe), and drop the now-dead scroll plumbing. (See Crucial Decision 6 re: the Day screen's collapsed header.)

---

## Not in scope / not bugs

- **Linear no trigger (issue 7):** by design — Linear triggers need a `team_id` unknown at connect, so Linear is poll-only. Deterministic tiering means the connect-refresh + manual pull fully cover it (no model, no webhook needed). Optionally provision per-team Linear triggers later (Crucial Decision 2).
- **Linear "all urgent":** correct overdue data, not a defect.

---

## Crucial decisions (please confirm)

1. **Cheap foreground `GET /feed` read.** You rejected periodic polling — agreed. But with zero client re-read, a webhook-appended item never becomes visible until the next connect/manual pull. I propose a single cheap `GET /feed` (DB read, no provider poll) on app launch + foreground. Not a timer. **OK?**
2. **Poll-only staleness (Linear + GitHub notifications).** With no periodic sync, Linear changes and GitHub review-requests/mentions that happen *after* connect won't appear until the next connect or a manual pull. Accept that (rely on manual pull), or invest in Linear per-team triggers + treating GitHub notifications via a foreground read? **Recommend: accept for now.**
3. **Composio propagation delay.** The first post-connect refresh can fail for a source for up to ~10 min (upstream). Mitigation is a bounded retry over ~90s; beyond that it fills on next foreground/pull. Cannot fully eliminate. **Accept the bounded-retry mitigation?**
4. **Activity overview scope (Cluster C).** Move the heavy GitHub/Linear stats to drill-in and keep the overview to cheap summaries — the overview gets lighter but reliable. **OK, or keep rich overview with bounded reads + a soft budget?**
5. **"Next in N" when the next meeting is tomorrow.** Label it "Tomorrow 1:15pm" or hide it entirely from the day view? **Which?**
6. **Collapsed sticky header.** Remove from Later (confirmed). Also remove the "Good evening" collapsed header from the Day screen, or Later only?
7. **Pill lifecycle.** Pill clears when the connect-refresh completes and the source's `held` count hits 0. If a source is still propagating on Composio's side past the retry window, the pill clears anyway (data fills later on foreground) rather than spinning forever. **OK?**

---

## Suggested build order

1. Cluster E (quick, isolated). 2. Cluster A + B (the core lag + pill, one coherent change to the connect/refresh lifecycle). 3. Cluster D. 4. Cluster C. Each with tests where backend logic changes (RGR), each deployed to EC2 and verified live via the logging + browser loop.
