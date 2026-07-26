# Round 3 plan — triage matrix, data pipeline, triggers, Google Docs, calendar, Later, post-connect UX

Date: 2026-07-26. Builds on [rca-round2.md](rca-round2.md).

**IMPORTANT — RCA status.** Only Part A (triage) was root-caused in round 2. Parts **B, D, E-calendar, and F below were NOT properly RCA'd** — they came from live testing feedback and must be **RCA'd first (against the live box + code), then planned, then implemented.** Do not implement B/D/F from the notes here alone; the notes are leads, not conclusions. **Research every point marked 🔬 before deciding.**

Fix order: **B (data pipeline + triggers) is the critical one** — it causes data inconsistency (user connects a source, sees nothing). Then A (triage), C (Google Docs), D (calendar/day), E (Later), F (post-connect UX).

---

## Part A — Triage: bands + clamp (RCA done; design ready)

Four tiers, ordered `later(0) < can_wait(1) < today(2) < urgent(3)`. Each `(source, reason)` maps to a deterministic **band** `(floor, ceiling, default, runs_llm)` that the user owns; the LLM rates the item; final tier = `clamp(llm_tier or default, floor, ceiling)`. One lookup table + one clamp — no if/else ladder. Kills all three round-2 triage root causes (branchy rules, LLM demoting below the floor via `llm_tier or rule_tier`, prompt that forces deadlines to `today`).

**STEP 0 (before coding): show the user this matrix and let them confirm/adjust each cell.**

| Source | Signal / reason | Floor | Ceiling | LLM? | Default |
|---|---|---|---|---|---|
| GitHub | security alert / CI failure on my PR | urgent | urgent | no | urgent |
| GitHub | review_requested / approval_requested | today | urgent | yes | today |
| GitHub | changes_requested | today | urgent | yes | today |
| GitHub | assigned issue | today | urgent | yes | today |
| GitHub | notification / mention | can_wait | urgent | yes | can_wait |
| Slack | direct message | can_wait | urgent | yes | today |
| Slack | channel mention | can_wait | urgent | yes | can_wait |
| Gmail | message | later | urgent | yes | can_wait |
| Linear | assigned issue | today | urgent | yes | today |
| Calendar | meeting/event | can_wait | urgent | yes | today |
| Google Docs | mention | can_wait | urgent | yes | can_wait |
| Google Docs | comment mentioning me | can_wait | urgent | yes | can_wait |
| Google Docs | share / access request | can_wait | urgent | yes | can_wait |

Implementation: `TIER_BANDS` table (single source of truth) → `rules.py` becomes a lookup; `effective_tier` (`ranking.py:40`) becomes `clamp(llm_tier or band.default, floor, ceiling)` (add `clamp()` to `tiers.py`; `at_least()` already exists); simplify the `classifier.py` SYSTEM_PROMPT to just "rate urgency", band enforces policy. RGR: table-driven.

---

## Part B — Data pipeline + per-source triggers 🔬 **RCA REQUIRED — this is the critical bug**

**Symptoms (live testing):**
- Connect **Linear** → the connection status updates instantly (the P0 status fix works), but **no data appears** on Day / To-dos. Activity shows "0 open, 0 completed".
- **No triggers are created** for Linear / Calendar / Google Docs on connect. (Confirmed in code: `TriggerProvisioner._TRIGGERS` only has GitHub + Slack.) GitHub and Slack triggers *are* created on connect (user saw Slack triggers created Jul 26 ~9:53).
- Manual pull-to-refresh **does** pull data (user saw "1 urgent, 3 by EOD" after a manual refresh) — so backfill works on refresh but the on-connect path does not surface it.
- Slack: shows data in Activity but not in To-dos (maybe genuinely empty — needs confirming, not assumed).

**What the code says today (facts, to ground the RCA):**
- Real-time push (trigger + ingest mapper) exists **only for GitHub + Slack**. Linear/Gmail/Calendar have **no trigger and no ingest mapper** — they reach the feed *only* via the backfill poll in `SourceSync.refresh` (`sync.py`: polls github `list_notifications`, linear `assigned_to_me`, gmail `actionable`, calendar `pending`, slack `unread`). Google Docs is polled by nothing.
- My round-2 connect fix added `void refresh()` in `connectSource` on `status==='connected'`, which *should* run the backfill for the newly connected source.

**✅ RCA DONE — root cause is permanent caching of a FAILED identity resolution (NOT the async-finalize race).**

`SourceSync` → `linear.assigned_to_me()` → `current_user_id()` (`linear.py:219-230`) guards on `if self._me is _UNSET`; on any exception it sets `self._me = None`. `None` is not `_UNSET`, so Composio is **never re-queried for the life of the service instance.** The factory (`factory.py:67-71`) memoises that instance per `(toolkit, user_id)` for the whole process with no invalidation. The app fires `refresh()` on every mount (`App.tsx:274-276`) — so the FIRST refresh runs *before* Linear is connected, Composio throws `ConnectedAccountNotFound`, `self._me` freezes to `None`, and Linear is dead until the process restarts. Manual refresh reuses the poisoned instance → also empty. Live proof: process uv[57144], `could not resolve the Linear user` at 04:41:45 (first/only real Composio call), Linear connected 04:56, then every later refresh logs only `skipping Linear: no assignee id` with no re-resolve; `feed_items`: gmail 13, github 1, slack 1, calendar 1, **linear 0**.

**The async-finalize race is REFUTED:** `finalize` writes the `connections` row **synchronously** via `mark_active` (`connections.py:191-197`) *before* backgrounding only the trigger-provision/prune half (`:203-205`). And the Linear poll doesn't consult `identity_for` at all — it resolves the assignee from Composio directly. So the P0 backgrounding is not the cause.

**Fix (minimal):** in `current_user_id()`, memoise **only a successful** id; on exception leave `self._me` as `_UNSET` (or a distinct "retry" sentinel) so the next refresh re-queries once the account is executable → self-healing. **Audit the sibling services memoised through the same factory for the identical failure-caching pattern** — Slack channel-map, Calendar own-email (`factory.py` cache is shared by sync/stats/later). This one fix likely also explains the "connect → nothing, refresh later → still nothing" for other sources whenever the app refreshed before that source was connected.

**Trigger slugs per source: RESEARCH DONE (2026-07-26).** Exact Composio findings:
- **Gmail — clean win:** `GMAIL_NEW_GMAIL_MESSAGE` (poll, empty-config-safe; optional `query:"is:important is:unread"`). Payload: `sender, subject, preview, message_text, thread_id, label_ids`. Provision + one mapper.
- **Calendar — clean win:** `GOOGLECALENDAR_EVENT_STARTING_SOON_TRIGGER` (poll, empty-config-safe; defaults: 10 min before start, 60-min window, 2-min poll). Payload: `event_id, summary, start_timestamp, html_link, attendees`. Provision + one mapper. (Note: this is the real-time "meeting starting" push; distinct from the `/day` ring pull — see Part D.)
- **Linear — BLOCKED:** there is **no `LINEAR_ISSUE_ASSIGNED*` trigger.** The proxy is `LINEAR_ISSUE_UPDATED_TRIGGER`, but **every Linear trigger requires a `team_id` in config, unknown at connect time** — same blocker class as the excluded GitHub repo-notification trigger. So Linear **cannot be auto-provisioned** without first resolving the user's teams (extra "list my teams" call → one trigger per team). **Decision:** keep Linear **poll-only** for now (backfill via `SourceSync`), defer team-resolved triggers. Also note Linear nests the issue under `data.data` (envelope has `action/type/url/data`), and `_SLUG_PROVIDER`/`_PROVIDERS` in `ingest.py` need a `LINEAR`→`linear` entry if ever mapped.
- **Google Docs — no trigger (see Part C):** deliver via Gmail notifications.

So the trigger plan is: **add Gmail + Calendar triggers** (both empty-config, both need a new ingest `_MAPPER` + `_SLUG_PROVIDER`/`_PROVIDERS` prefix entries in `ingest.py`). Linear + Docs stay poll-only. Every mapper must populate `RawEvent` (required: `source, source_ref, reason, subject_type, title, url, repo` — `repo` is required even for non-GitHub, pass `""` or a synthetic context).

**Fixes (design after RCA):**
- **Reliable data-on-connect:** guarantee that connecting a source pulls and shows its data (fix the race / ensure `refresh()` targets the new source after it is truly active; consider a per-source targeted sync rather than a full refresh).
- **Provision triggers for every source that should have them** (extend `_TRIGGERS` + add the matching ingest mappers), so Composio pushes updates without waiting for a manual refresh. Aligned with the triage matrix (only categories we act on).
- **Refresh cadence:** decide how backfill-only sources (Gmail/Calendar/Linear if kept as poll) refresh while the user is in the app (on focus? interval? on tab open?). 🔬 Research + decide; the user is fine with "whenever Composio pushes, we update" for triggered sources.

---

## Part C — Google Docs: no trigger path exists (RESEARCH DONE — decision needed) ⚠️

**Composio trigger research (done 2026-07-26):** Google Docs has **NO comment / mention / share trigger.** The only GOOGLEDOCS triggers are document-lifecycle polls (`GOOGLEDOCS_DOCUMENT_UPDATED_TRIGGER` etc.) whose payload is doc metadata (`id, name, modifiedTime, lastModifyingUser, shared`) with **no per-user comment/mention data**. So the feature the user asked for (someone comments-mentions-me / requests access) **cannot be built from a Docs trigger.**

**The real delivery path is Gmail.** Google itself sends these as emails: a comment-mention arrives from `comments-noreply@docs.google.com` ("X mentioned you in a comment in <doc>"), a share/access request from `drive-shares-noreply@google.com`. So Google Docs mentions/comments/shares ride in on the **Gmail source** (`GMAIL_NEW_GMAIL_MESSAGE`, which IS provisionable). 🔬 Confirm the exact sender addresses live, then either (a) tag those Gmail items with a `google_docs` reason via a sender-sniffing branch in the Gmail mapper, or (b) leave them as Gmail items tiered by the matrix. Recommend (a) so the card reads as a Docs mention, not a generic email.

**Decision for the user:** drop the standalone Google Docs client/trigger build (there's nothing to build against) and deliver Docs mentions/comments/shares through Gmail-notification sniffing. This removes Part C's `ComposioGoogleDocsService` + Docs-trigger work entirely and folds it into the Gmail mapper. Matrix rows 11-13 still apply — just sourced from Gmail.

---

## Part D — Calendar / Day tab ✅ **RCA DONE — one-line wiring bug**

**Root cause (confirmed, code + live box):** `GET /day` (`main.py:415-432`) reads a **`calendar=` closure param** that `composition.py` **never passes** → it's always `None` → `get_day` short-circuits to `return []` at `main.py:418-419` and never makes a single Composio call. The feed works because it reads the **per-user integrations factory** (`self._integrations.calendar(user_id)` in `sync.py:91-93`), which composition DOES wire (`integrations=`). Pure wiring divergence — not timezone, not display, not identity. Live journal confirms every `GET /day` returns 200 with zero calendar activity.

**Fix (minimal, one place):** make `get_day` read from the per-user factory like the feed does — `cal = resolved_integrations.calendar(user_id)` — and delete the dead standalone `calendar` param + its `_StaticIntegrations` shim so the two paths can't diverge again. `day_window()` already returns a wide UTC window (−18h/+30h) and the client filters to the device day.

**In-progress / next display:** **no client change needed.** `YourDayScreen` logic is already correct — `ahead` includes in-progress meetings (`end > now`), index 0 renders highlighted, `daySummary` says "next now" when `gap <= 0`. It shows "No meetings today" today *only* because `meetings` is `[]` from the empty `/day`. Fixing the pull fixes the display automatically.

**RGR:** failing test first — `FakeIntegrations.calendar(user_id)` returns a fake whose `day_window()` yields meetings; assert `GET /day` returns them. Add a composition-level wiring assertion so the gap can't regress (current tests inject `calendar=` directly, which masked it).

---

## Part E — Later tab (RCA done in round 2; frontend direct)

- Rows open a **detail modal** (add a `laterRowToFeedRow` adapter, tier `noise`, open `DetailSheet`), external link only from the sheet's Open button.
- Selector chips **derived from connected sources** (`status==='connected' && source!=='calendar'`), not the hardcoded `SOURCES` const; default to the first connected source. Include Google Docs once it emits.
- `bring_back` scoped to `status==='snoozed'` only.
- Slack-in-Later: low priority (DMs already on Home). Optional: read Slack channel mentions instead.

---

## Part F — Post-connect UX 🔬 **DESIGN REQUIRED**

After connecting a source, data is not instant (backfill runs, or the first trigger poll is ~2 min out). The user should *know* data is being pulled for that integration — but the user does **not** want a blocking loader. 🔬 Design the affordance: e.g. a per-source "syncing…" pill on the You/Activity connection row that clears when the first data lands, or a subtle banner. Decide and spec it before building.

---

## Verify (every part)
- Reset the GitHub (and any test) integration for a clean run: delete Composio accounts + triggers + `connections`/`feed_items` rows for user `cf54cdda-1065-4119-bebf-44a6f1edfd5f`. **NEVER delete the `public.users` row** for `vicky@agentiwise.com`.
- Live-test each source: connect → status flips fast → **data actually appears** → triggers exist → items land in the right tiers.

## Environment
Box `ssh productivity_app_test` — **the SSH egress IP rotates**, so first re-add the current egress IP to security group `sg-0d374ba0556b75951` (region ap-southeast-2) port 22. Backend at `/home/ec2-user/productivity-app`; deploy changed files via tar + `sudo systemctl restart productivity-backend`; app at `https://52-64-67-235.sslip.io` (Caddy + sslip.io — Composio webhook delivery needs the hostname, not the bare IP). Backend suite has 3 pre-existing time-bomb JWT test failures (hardcoded `NOW`) unrelated to this work. All six sources have auth configs set on the box (all connectable); only GitHub + Slack are wired end-to-end today.
