# RCA — Testing Round 2

Date: 2026-07-26. Four issues surfaced in live UI testing (connect flow, name prompt, triage, Later tab). Investigated by three parallel read-only agents plus direct analysis. Priority: fix **Issue 1** and **Issue 2** first; **Issue 3** and **Issue 4** are root-caused here and fixed next.

---

## Issue 1 (P0) — Name prompt fires on every launch

**Symptom:** the post-signup name modal opens every time the app loads, not just at first signup.

**Root cause:** `App.tsx` `loadProfile()` opens the modal whenever `profile.name` is null, guarded only by an in-session `useRef` (`autoPrompted`) that resets on every fresh mount. So the trigger is "no name yet" (a *persistent server state*) instead of "just signed up" (a *one-time event*). A user who never sets a name is prompted every launch.

**Fix (signup-only):** add a `justSignedUp` signal to `AuthContext` — set inside `register` (not `login` or session-restore) — and have `App` open the prompt once on that signal, then acknowledge/clear it. Remove the null-name auto-open from `loadProfile` (it keeps only setting the name for the greeting + You tab; the You tab "Add your name" affordance remains for setting it later).

---

## Issue 2 (P0) — After connecting: slow status flip + feed stays empty

**Symptom:** (a) connection status takes ~15–20s to read "connected"; (b) existing messages (Slack) don't appear until a manual pull-to-refresh.

**Root cause (a) latency** — three effects, in order of contribution:
1. **Composio's server-side token exchange.** `openAuthSessionAsync` returns on redirect, but Composio flips the account `INITIATED → ACTIVE` afterward. Until then `finalize()` finds no live account and returns `DISCONNECTED`. *This is the dominant term and is not client-fixable.*
2. **`finalize()` heavy work on the deciding poll** (`connections.py`): on the poll where the account first reads ACTIVE it runs, serially on the critical path, `_resolve_identity` (live `tools.execute`), `_provisioner.provision` (`triggers.list_active` + a `create` per slug), and `_discard` (a `delete` per stale attempt) — ~3–5s of serial Composio round-trips before it returns `connected`. *Fixable.*
3. The 1s client poll interval quantizes it.

**Root cause (b) empty feed:** `connectSource`'s success branch calls only `loadSources()` (status + counts). It never calls `api.refresh()` (the `SourceSync` backfill that pulls existing provider messages) or `load()`. Existing Slack backlog reaches the feed *only* via `POST /feed/refresh`, which runs only on mount and pull-to-refresh. So the backlog is never fetched on connect; triggers only cover *future* pushed events.

**Fixes:**
- **(a)** In `finalize()`, once the account is ACTIVE and the row is written (`mark_active`), return `CONNECTED` immediately and run `provision` + `_discard` on a **background runner** injected into `DefaultConnectionService` (sync fallback in tests). `_heal` + the idempotent provisioner already make late/repeated provisioning safe. Keep identity resolution synchronous (it's the data the row needs; one call). Residual latency is Composio's own lag — acknowledge it.
- **(b)** In `connectSource` success branch, after `loadSources()` call `void refresh()` (which runs `api.refresh()` then reloads `/feed`), and add `refresh` to the deps. This backfills the newly connected source on its own.

---

## Issue 3 (P1) — Nothing reaches the Urgent tier

**Symptom:** assigned GitHub issues and emails/DMs with a stated deadline / "urgent" land in Can-wait / Adjourn; Urgent stays empty.

**Root cause — three compounding layers (all server-side; app bucketing is correct):**
1. **Rules never mark an assignment urgent.** `reason="assign"` → `RuleVerdict(tier=TODAY, needs_llm=True)` (`rules.py`). `is_blocking=True` only adds `+300` to the *score* (`ranking.py`), which can't cross the tier-weight gap (`URGENT=1000` vs `TODAY=100`) — so a "someone is waiting on you" item is unreachable in Urgent via score.
2. **The LLM prompt under-calls urgent by design** (`classifier.py` SYSTEM_PROMPT): "A stated future deadline ('by tomorrow EOD') means today, never urgent"; ties break to today; the only promotion path is "a direct question with no deadline." The `is_blocking` signal is passed as `is_direct` but no prompt line references it. So the deadline/"urgent" email literally cannot reach Urgent.
3. **Combination logic lets the LLM demote below the rule floor:** `effective_tier` is `tier = item.llm_tier or item.rule_tier` (`ranking.py:40`) — the LLM verdict fully overwrites, including when lower. So an assigned issue floored at TODAY gets overwritten to `can_wait`. Contradicts `tiers.py` (which ships an unused `at_least()` helper meant for exactly this).

**Fixes (priority order):**
1. `ranking.py` `effective_tier` → `at_least(item.llm_tier, item.rule_tier)` so the LLM can promote but not demote below the rule floor (one-liner; explains the assigned-issue → can_wait symptom). Optionally scope the floor to blocking/assigned reasons so a slipped newsletter can still be demoted.
2. `classifier.py` SYSTEM_PROMPT: let an imminent deadline (≤~24h) **combined with explicit urgency language** ("urgent", "blocker", "ASAP", "blocking others") be urgent; broaden the urgent path beyond "direct question with no deadline." (Unblocks the deadline email.)
3. Optional/product: if "a named person is explicitly waiting on you" (`is_blocking`) should read urgent, put that in the **tier** path (rules or `effective_tier`), not the score.

---

## Issue 4 (P1) — Later tab

Note: there are **two "Later" concepts**. The Later **tab** (`LaterScreen`) is a live provider stream rendered with `Row`. The Later **group** (feed items with `tier=noise` or `status=snoozed`) lives in To-dos and opens `DetailSheet` — that's where "bring back" is.

**(a) Later-tab rows open the link, not a modal.** `App.tsx` wires `onOpen={(url) => Linking.openURL(url)}`; the row `onPress` calls it directly. And `LaterRow` has no `tier`/`status`/`id`, so it can't drive `DetailSheet` (which dereferences `row.tier`, `row.status`, etc.) as-is.
- *Fix:* adapt `LaterRow → FeedRow` (defaults: `tier:'noise'`, `status:'unread'`, `type_tag:'fyi'`, `id:source_ref`), then open a `DetailSheet` from the Later tab (its `candidates()` for noise → `[OPEN, BRING_BACK, MARK_READ]`; the sheet's Open button becomes the only path to the link).

**(b) Nothing from Slack in Later.** `LaterService` *does* iterate Slack, but `slack.unread()` is **DM-only** (`SLACK_SEARCH_MESSAGES`, `is:dm`), and DMs are exactly what the webhook already puts on Home — and Later subtracts everything on Home (`on_home`). Slack's Later universe is a subset of Home → collapses to empty. (Compounding: `search.messages` needs a user token with `search:read`; a bot-token connection errors and `unread()` swallows it to `[]`.)
- *Fix:* give Slack a Later source that isn't already on Home — read channel messages/mentions (the pile that deliberately doesn't reach Home) instead of DMs; or narrow `on_home` to `status==unread` only. Verify the Slack scope.

**(c) Hardcoded selector chips.** `LaterScreen` has a module constant `SOURCES` (gmail/slack/linear/github), rendered verbatim — so Linear shows even when disconnected. `LaterScreen` never receives the connection list.
- *Fix:* pass `sources: SourceInfo[]` and derive chips from `status==='connected' && source!=='calendar'`; initialize the selected source to the first connected one.

**(d) "Bring back" — what it is.** Un-defer: `api.snooze(id, now)` (a snooze that already expired), promoting a snoozed/noise item back to live. Surfaced by `candidates()` only when `status==='snoozed' || tier==='noise'`, on the Later **group** in To-dos (not the Later tab). Placement is sensible (inverse of Snooze). Caveat: for a pure `noise` item (never snoozed) it's fuzzy — the tier is recomputed on reload, so "coming back" depends on the rules. *Recommendation:* scope `bring_back` to `status==='snoozed'` only; don't add it to Later-tab rows (they have no persisted feed id).

---

## Fix order

1. **Issue 1** (frontend) — signup-only prompt.
2. **Issue 2** (backend finalize async + frontend auto-refresh) — the connect UX.
3. **Issue 3** — `effective_tier` floor (one-liner) + prompt.
4. **Issue 4** — Later modal + Slack source + dynamic chips (+ optional bring_back scoping).
