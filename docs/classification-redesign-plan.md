# Classification redesign — plan (reviewed, v2)

Date: 2026-07-26. Supersedes the triage notes in [round3-plan.md](round3-plan.md) Part A. Reviewed by three compound-engineering agents (spec-flow, architecture, simplicity) on 2026-07-26; this v2 folds in their findings.

**Status: LOCKED — all decisions made (2026-07-26). Ready to implement.**

### Final decisions
- **A — Timezone:** use the **user's timezone** for all "today"/"end_of_day" math (Linear due dates, calendar). Thread a per-user tz into `now`/`end_of_day`. (There is none in the stack today — new plumbing.)
- **B — Failure fallback:** on LLM failure/give-up, show the item at the **band CEILING** (not the floor), with no reason. For every LLM signal the ceiling is `urgent`, so an un-classifiable item surfaces prominently rather than being buried — Vicky's call: when the model can't judge it, err toward surfacing. (No `fallback` column needed; use `band.ceiling`.)
- **C — Synchronous classification:** **yes, classify synchronously** — items must appear already in their correct tier, never as a placeholder. `/feed/refresh` classifies inline (bounded). The webhook has one infra constraint (below): it must ack Composio's delivery first, then classify the single pushed item immediately, so the item still appears already-classified ~1s later, never unclassified.

---

## The requirement (unchanged)

**Never show a placeholder tier or a blank reason for an item the LLM is meant to classify.** A deterministic item (rule/clock/due-date fixes the tier) appears instantly; an LLM item appears only once it has a real tier + reason.

## The key correction from review: this is a *visibility* requirement, not a *synchrony* one

The whole requirement is met by **one read-time filter**: `list_feed` excludes rows where `needs_llm and llm_tier is None and not yet attempted`. Once un-classified items can't reach a screen, *when* classification runs no longer affects correctness. So we do **not** rewrite everything to be synchronous. Classification stays a background pass; the filter is the guarantee. (All three reviews independently reached this.)

This deletes the riskiest pieces of the v1 plan: synchronous webhook classification (Composio retry-storm coupling delivery to LLM latency), the bounded-inline-timeout sub-mechanism, and the "sync everywhere" rewrite of `classifier.py`/`sync.py`.

---

## The keystone fix: an explicit "attempted" marker (resolves the central v1 bug)

v1 had a fatal collision: "hold until classified" and "on failure show at floor" **both keyed on `llm_tier is None`**, so a held item and a failed item were byte-for-byte identical — the filter would either hide both (failure never shows) or show both (hold defeated). On a model outage every email/Slack/mention item would vanish with no way back.

**Fix — three visible states, distinguished by a marker, not by `llm_tier is None` alone:**

| State | Condition | Shown? | Tier | Reason |
|---|---|---|---|---|
| Held (not yet classified) | `needs_llm` and `llm_tier is None` and **not attempted** | **no** | — | — |
| Classified | `llm_tier is not None` | yes | `llm_tier` (clamped) | LLM reason |
| Failed / gave up | attempted, still no `llm_tier` | yes | **`band.ceiling`** (Decision B) | none |

Add a marker to `feed_items` — e.g. `llm_attempted_at timestamptz` (or reuse `tier_source`: set it to a terminal value after a failed attempt). `list_feed`'s hide predicate becomes: `needs_llm and llm_tier is None and llm_attempted_at is None`. The classifier sets `llm_attempted_at` on every batch it processes, success or fail. A failed item is therefore *attempted* → visible at **`band.ceiling`** (urgent for LLM signals); a never-touched item is held. This single marker also unblocks the webhook-failure and content-change cases below. (`effective_tier` reads the ceiling from the item's band when `llm_attempted_at is not None and llm_tier is None`.)

---

## Part 1 — Model the policy as ONE tagged union, not two dicts

v1 said "split `TIER_BANDS` into deterministic vs LLM shapes." Review: doing that as **two dicts** fragments the "one table is the policy" seam and forces every consumer (`rules.classify`, `ranking.effective_tier`) to branch on which shape it got. Instead, keep **one table** whose value is a tagged union:

```
Policy =
  | Deterministic(tier: Tier | tier_fn(item, now) -> Tier,  tag,  reason_template)
  | Banded(floor: Tier,  ceiling: Tier,  tag,  fallback: Tier)   # runs_llm is implied by being Banded
```

- `band_for(signal) -> Policy` stays the single lookup. `runs_llm` becomes `isinstance(policy, Banded)` — the boolean disappears.
- `Deterministic` carries **either a fixed tier or a read-time function** (`tier_fn`). Calendar and Linear supply a function; security_alert supplies a fixed tier. This folds the read-time tiering into the table so `effective_tier` has **one** branch ("policy is Deterministic-with-fn → call it"), not a growing list of `if source == "calendar" / "linear" / …` special-cases (the anti-pattern the band table was built to kill).
- The misleading `Band(N,N,C)` fake-ceiling rows go away because deterministic rows no longer carry floor/ceiling at all.

## Part 2 — Synchronous classification (Decision C), with the filter as the safety net

Classification is synchronous — an item appears already in its correct tier, never as a placeholder. The read-time filter is kept as the **guard** (so no transient held item can ever leak), not as a substitute for sync.

- **`list_feed`** hides held items (`needs_llm and llm_tier is None and llm_attempted_at is None`). One enforcement point, server-side, testable with a fake repo.
- **`/feed/refresh`** classifies **inline, bounded** (single-user, capped batches / wall-clock — measure a first Gmail sync to set the cap so it doesn't block 60–120s past a client timeout). Deterministic items paint immediately; LLM items are classified before the response returns; anything past the cap stays held and is swept by the next refresh (or shown at ceiling if attempted). The syncing pill covers the wait.
- **Webhook — the one infra constraint.** Composio treats a slow/failed HTTP response as a delivery failure and **retry-storms** (the existing route at `main.py:497-503` already swallows errors into a 200 for exactly this reason). So the webhook **cannot block its HTTP response on the model.** Instead: `handle` ingests and returns 200 immediately, then **classifies that single item right after** (a background task / `run_in_threadpool` fired on the way out). The item is held by the filter until that ~1s classify lands, then appears already-classified. **Net user-visible result is identical to synchronous** — the item never shows as a placeholder — but Composio's delivery is never coupled to model latency. On failure it shows at `band.ceiling` immediately (no waiting for a manual refresh).
- Add a **single-item classify** method (`classify_item(user_id, item)`); the webhook path must NOT call `classify_pending` — that's a whole-user 200-item sweep, so one DM would re-classify the entire backlog inside the request.
- Correct the "daily budget" language: `daily_budget` is today a **per-pass limit of 200**, not a running daily counter. Don't add logic for a counter that doesn't exist (build a real daily cap only if wanted — separate decision).

## Part 3 — Linear: deterministic, read-time (via the `Deterministic(tier_fn)` variant)

Ignore priority. `_linear_tier(item, now)` (a `tier_fn` in the table, not a hardcoded `effective_tier` branch):

```
if task is completed:              drop (unchanged)
elif due_date is None:             can_wait
elif due_date <= end_of_<today>:   urgent      # today or overdue, still open
else (future due date):            can_wait     # flips to urgent when the day arrives
```

- Delete the Linear priority/LLM rows (`linear_urgent/high/due/in_progress`) from the table. Linear never runs the LLM.
- `_linear_tier` **fully owns** Linear tiering — it must bypass the generic `effective_tier` deadline/stale-demotion block (otherwise the 24h "urgent went stale → today" rule would demote a legitimately overdue task). Keep `deadline = end_of_day(due)` populated so retention (`list_by_user`: "deadline not null → never ages out") keeps overdue tasks alive.
- **`end_of_today` is computed in the user's timezone (Decision A)**, not UTC — same tz plumbing calendar will use. `end_of_day(due)` likewise interprets a date-only Linear due date against the user's tz.

## Part 4 — Reasons

- LLM rows: reason comes from the model (as today).
- Deterministic rows: **only where it adds information the card doesn't already show.** Reviews agree most templates just restate the tag/title ("Security alert on your code" over an ALERT-tagged urgent card adds nothing). The one case that carries new info is Linear's date line ("Overdue since 24 Jul"). So: ship deterministic rows with **no template except Linear's date line**, and let the modal simply omit the "why" box when reason is empty (which it must do anyway for the failure case). Add more templates later only if a specific card tests confusing. **If** we instead keep a full template map, it must be **exhaustive** over every `Deterministic` signal or those cards render blank.

---

## Part 5 — GitHub comment body (already coded, fold in)

`list_notifications` enriches each notification with the real issue body (`GITHUB_GET_AN_ISSUE`) or the specific comment (`GITHUB_GET_AN_ISSUE_COMMENT` when `latest_comment_url` is a `/comments/` URL), bounded + parallel, fallback to the synthetic description. Tests pass. Ship with this redesign.

---

## Correctness & rollout items surfaced by review (all must be handled)

- **Content-hash change (H1):** on refetch with changed content both repos null `llm_tier/summary/reason`. Under the new filter a **visible, classified card would vanish mid-session** (a Slack thread gains a reply). Fix: on content change, mark-attempted and keep it visible at the fallback tier (or reclassify before it can be hidden) — never drop it back into the held state.
- **Deploy migration (H2):** the moment the filter ships, every existing `needs_llm && llm_tier is None` row goes invisible, and stored Linear rows carrying now-deleted signals mis-band to `UNKNOWN`. Ship a backfill: recompute Linear deterministic tiers + set `needs_llm=False` on them; grandfather pre-deploy held rows as attempted→visible.
- **Cache (H4):** `InMemoryClassificationCache` is per-process, cold on restart, not shared across workers. On the (bounded-sync) refresh path a cold cache re-hits the model for everything. Back it with the DB (the row already persists `llm_tier/summary/reason` by content_hash) and read-through.
- **Pill (M1):** "sync done" no longer means "feed complete" — held/overflow items are simply absent. Extend `SyncReport` with a held/unclassified count so the UI can show "still classifying N" instead of a clean finish.
- **Purge (M3):** `purge_expired` deletes on `occurred_at < now-30d` regardless of state — a backfilled old-but-held item can be purged before ever being seen. Exclude never-shown items, or key purge on `created_at`.
- **Event loop (L1):** the webhook route is `async def`; any blocking model call would block the whole loop. (Moot if webhook stays async per Part 2, but note it.)

---

## Files this touches (implementer map)

`tier_bands.py` (tagged-union Policy; drop Linear LLM rows; `fallback`/`tier_fn`/`reason_template` fields) · `rules.py` (return the Policy) · `ranking.py` (`effective_tier`: one Deterministic-fn branch; `_linear_tier`; `_calendar_tier` folds in) · `classifier.py` (`classify_item`; set `llm_attempted_at`; write `fallback` on give-up; DB-backed cache) · `sync.py` (bounded sync on refresh; held count in `SyncReport`) · `feed.py` (`list_feed` hide predicate; content-change keeps-visible) · `ingest.py` (webhook stays async; out-of-band classify trigger) · `supabase_feed_repository.py` + migration (`llm_attempted_at` column; purge excludes held; content-change path) · `composio_github.py` (enrichment, done) · a one-time backfill migration.

## Still open (implementation research, not product decisions)
- Exact bound for the sync-on-refresh pass (max batches / wall-clock) — measure a first Gmail sync.
- Mechanism for the post-ack webhook classify (FastAPI `BackgroundTasks` vs `run_in_threadpool` vs a small queue) — all give "ack first, classify the one item ~1s later".
