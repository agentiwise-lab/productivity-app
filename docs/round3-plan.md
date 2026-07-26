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

**🔬 RCA questions to answer against the live box (logs + code):**
1. When Linear is connected, does the app actually call `POST /feed/refresh`? Does `SourceSync` poll Linear? Does `linear.assigned_to_me()` succeed, fail, or return empty? (Check box journal + the SyncReport `failed`/`per_source`.) Is "no data" a real pull failure or genuinely zero assigned issues?
2. Is there a **timing race** — does `refresh()` fire before the Linear account is usable (Composio still finalizing), so the backfill runs against a not-yet-active account and silently returns empty/fails?
3. Does the backfill need the `connections` row / identity that finalize now writes *asynchronously* (P0 fix backgrounded provisioning)? Could backgrounding have made the on-connect backfill race the row write?
4. Which sources SHOULD get real-time **triggers** vs be **poll-only**, and **which trigger slugs** per source map to our task categories? 🔬 Research Composio trigger slugs per toolkit (LINEAR_*, GMAIL_*, GOOGLECALENDAR_*, GOOGLEDOCS_*) via `composio search`; only provision the ones that produce items we tier (e.g. Linear issue-assigned; Gmail new/important message; Docs comment/mention/share). Every provisioned slug needs a matching ingest `_MAPPER`.

**Fixes (design after RCA):**
- **Reliable data-on-connect:** guarantee that connecting a source pulls and shows its data (fix the race / ensure `refresh()` targets the new source after it is truly active; consider a per-source targeted sync rather than a full refresh).
- **Provision triggers for every source that should have them** (extend `_TRIGGERS` + add the matching ingest mappers), so Composio pushes updates without waiting for a manual refresh. Aligned with the triage matrix (only categories we act on).
- **Refresh cadence:** decide how backfill-only sources (Gmail/Calendar/Linear if kept as poll) refresh while the user is in the app (on focus? interval? on tab open?). 🔬 Research + decide; the user is fine with "whenever Composio pushes, we update" for triggered sources.

---

## Part C — Google Docs integration (NOT implemented today; build fully) 🔬

Confirmed not wired: Google Docs has an auth-config slot (connectable) and 3 **dead** rules entries (`docs_mention`, `docs_comment`, `docs_edited`), but **no integration client** (`factory.py` has no `google_docs`), **no poller, no trigger, no ingest mapper**. User connected it, commented in a doc, refreshed — nothing appeared, and no trigger was created.

Build it end to end:
- Integration client (`ComposioGoogleDocsService`) + factory method. 🔬 Research the Composio Google Docs read/trigger actions.
- Trigger slugs for mention / comment-mentioning-me / share-or-access-request → add to `_TRIGGERS[GOOGLE_DOCS]` + ingest `_MAPPERS` → `RawEvent(source="google_docs", reason=..., url, title, body=comment text, deadline parsed from content)`.
- Triage: matrix rows above (mentions/comments/share → floor `can_wait`, never `later`; LLM lifts on deadline).
- Later tab: include Google Docs once it emits.
- RGR for mappers + bands.

---

## Part D — Calendar / Day tab 🔬 **RCA REQUIRED**

**Symptoms (live testing):**
- User has **4 meetings scheduled**, but the Day tab shows **"no meetings today"**, nothing highlighted on the day-ring outer circle. So the **calendar day pull is not working / not displaying**. (The feed side partly works: a `calendar_starting` meeting shows under Urgent when Urgent is tapped — so `/day` vs the feed are diverging.)
- When a meeting is **in progress**, the default Day view (nothing selected) shows "no meetings today" instead of the current meeting. Only tapping Urgent reveals "wiki testing meeting is going on".

**🔬 RCA questions:**
1. Does `GET /day` (`calendar.day` read) return the 4 meetings? Is the Calendar account connected + the day read succeeding? Why does the day-ring get nothing while the feed has a calendar item?
2. Is it a pull failure, an identity/account issue, or a display bug in `YourDayScreen` (meetings present but not rendered)?

**Fixes (design after RCA):**
- Make the calendar day pull work (meetings populate the ring + the meetings section).
- Day default view: when a meeting is in progress, show **"in progress" + the next one**; when none is in progress, show the **next** meeting. Never show "no meetings today" when meetings exist.

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
