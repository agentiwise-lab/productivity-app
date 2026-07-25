# Fix Plan — Testing Findings

Date: 2026-07-25. Companion to `docs/testing-log.md` (BUG-1 … BUG-11 + the name feature). This does the root-cause analysis, collapses the findings into a few underlying causes, and lays out the fix sequence following the repo's conventions (Interface-First seams, Deep Modules, Tracer Bullet, Red-Green-Refactor for backend).

The deployment itself is **not** in scope here — the raw-IP HTTPS backend receives, verifies, and ingests webhooks correctly (proven). Every finding below is application logic.

---

## 1. RCA — 11 findings, 4 root causes

### RC-1 — The event pipeline is half-built (the core defect)
The app implements the **inbound** half (webhook route + signature verify + ingest mappers + feed store — all proven working) but not the **subscription** half: **nothing creates Composio triggers.** `connections.py` only calls `connected_accounts.link`; `triggers.create` exists nowhere. `ingest.py`'s `_MAPPERS` enumerate the exact slugs the app expects (`GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER`, the Slack ones, …) but no code ever creates them.

- Explains **BUG-8** (no triggers) and **BUG-1** (polling never delivers) — same root. BUG-1 was never an upstream Composio problem; there was simply nothing to poll. The `pg-test` triggers only ever existed because they were made by hand via the API/dashboard.
- **Impact:** the product's core loop (connect → activity → feed) is broken at exactly one missing step.

### RC-2 — The connect lifecycle is timing-coupled, not reconciled
Connection **finalization** (resolve identity, write `public.connections`, and — after RC-1 — provision triggers, dedupe attempts) runs **only inside the transient status poll**, gated on "the poll happened to be running the moment Composio flipped to `ACTIVE`." Slow web OAuth (Composio's "Taking you back…" interstitial, no deep-link return) misses that window.

- Explains **BUG-9** (`public.connections` never written), **BUG-10** (UI needs manual refresh), **BUG-11** (stale `INITIATED`/`INITIALIZING` attempts accumulate).
- Note: `list_sources` reads live Composio status, so the *source list* can show "connected" without a DB row — but ingest's `identity_for`, `disconnect`, and Slack's identity all read the row, so the missing row is a real integrity gap (GitHub ingest tolerates a missing identity; Slack does not).

### RC-3 — The webhook route is not fault-isolated
`main.py:460` does `return ingest_service.handle(envelope)` with no guard. Signature failures become 401, but any **exception inside `ingest.handle`** becomes a **500**, and Composio retries a 500 → redelivery amplification.

- Explains **BUG-2** (500 → retry loop) and **BUG-3** (a non-UUID `user_id` raises Postgres `22P02` → 500). The route's stated intent ("unhandled → 200 so Composio doesn't retry") is only half-enforced.

### RC-4 — Frontend flow/labeling gaps (independent, lower impact)
- **BUG-7:** Day empty-state "Open You" is wired to `connectSource('github')` (App.tsx:426) instead of navigating to the You tab.
- **BUG-10 (frontend side):** no re-poll on focus after the OAuth tab on web.
- **BUG-4:** spinner flash — empty state waits on `/feed/refresh` instead of rendering immediately when the feed is empty.

Plus two non-root items: **BUG-5** (Cursor auto-update wiped Full Disk Access — ops/doc, no code) and **BUG-6** (expo-secure-store web fallback — already fixed, needs commit). And the **display-name** enhancement.

---

## 2. Priorities

| Priority | Why | Findings |
|---|---|---|
| **P0** | Product's core loop is dead without it | RC-1 (BUG-8, BUG-1), RC-2 persistence (BUG-9) |
| **P1** | Robustness / correctness | RC-3 (BUG-2, BUG-3), RC-2 reconcile+dedupe (BUG-10 backend, BUG-11) |
| **P2** | UX polish + enhancement | BUG-7, BUG-4, BUG-10 (frontend), name feature |
| **Done / ops** | — | BUG-6 (commit), BUG-5 (document) |

---

## 3. Fix plan by cluster

### Cluster A (P0) — Close the event loop: trigger provisioning + reliable finalize

This is the one that makes "connect GitHub → assign an issue → it appears in the feed" actually work. Fixes RC-1 and RC-2 together, because they're the same code path (connect finalize).

**Seams (Interface-First) — define these contracts before implementing:**
1. `TriggerProvisioner` — `provision(user_id, source, connected_account_id) -> None`, **idempotent** (create the source's trigger(s) only if absent). Encapsulates the per-source slug + config map.
2. Extend `ConnectionService` with `finalize(user_id, source) -> SourceInfo` — the single idempotent reconcile: read Composio status; on `ACTIVE`, resolve identity → `mark_active` (write the row) → `provision` triggers → dedupe stale attempts. Callable from **both** the status poll and `list_sources`, safe to call repeatedly.

**Per-source trigger map** (align with the existing `ingest._MAPPERS`):
- GitHub → `GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER` (+ `GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER` if desired)
- Slack → `SLACK_DIRECT_MESSAGE_RECEIVED`, `SLACK_CHANNEL_MESSAGE_RECEIVED`
- (Calendar / Linear / Gmail / Docs added as their mappers land)

Trigger config: sensible poll interval (**not 60 min** — that's what made testing look dead; use the source's default, ~2 min). Pass `user_id` (project has 2FA) and the connected-account id.

**Tracer bullet:** GitHub only, end to end — connect GitHub → `finalize` writes the row + creates the assigned-issue trigger → assign an issue → webhook → ingest → feed row → feed shows it. Prove that single path, then expand to the other sources.

**Red-Green-Refactor:** test `TriggerProvisioner` and `finalize` against a `FakeComposio` (contract-level, idempotency + "creates the right slugs" + "writes the row on ACTIVE"), then implement. No live Composio in tests.

**Dedupe (BUG-11):** in `finalize`, after an `ACTIVE` is confirmed, delete the other non-active attempts for that (user, toolkit).

**Acceptance criteria (Cluster A + the Cluster C focus re-poll):**
1. After authorizing GitHub, the app shows the source as **connected on its own — no manual refresh, no re-navigation** (this is the explicit BUG-10 requirement). The backend makes this possible (idempotent `finalize` reconciles + persists on any `/connections` read); the frontend triggers it by re-polling on focus/visibility when the user returns from the OAuth tab.
2. A `public.connections` row exists for (user, github) after connect (BUG-9).
3. The GitHub assigned-issue trigger exists under the user's UUID (BUG-8), with a sane poll interval (not 60 min).
4. Only one live connected account per (user, toolkit); stale `INITIATED`/`INITIALIZING` attempts removed (BUG-11).
5. Assigning yourself an issue produces a feed row within the poll interval — the full loop (BUG-1).

### Cluster B (P1) — Webhook fault isolation (RC-3)

- Wrap `ingest_service.handle` in the route: catch, log, and return **200** with `IngestResult(handled=False, reason=...)` so a malformed/unexpected event can't trigger a Composio redelivery loop.
- Make `identity_for` tolerant of a missing/invalid user (return an empty `Identity` rather than letting a bad `user_id` raise) so BUG-3's `22P02` and any unknown user degrade gracefully.
- RGR: a webhook with a bad/non-UUID `user_id` and a malformed payload each return 200, not 500.

### Cluster C (P2) — Connect-flow UX

- **BUG-7:** Day empty-state `onConnect` → `navigation.navigate('You')` (App.tsx:426); the You screen already does per-provider connect.
- **BUG-10 (frontend):** re-poll `/connections/{p}/status` on app focus/visibility after the OAuth tab (web has no deep-link return). Combined with Cluster A's idempotent `finalize`, this makes the UI update without a manual refresh.
- **BUG-4:** render the empty state as soon as `/feed` returns empty with no connections, instead of blocking on `/feed/refresh`.

Frontend = implement directly (no TDD).

### Cluster D — Commit + ops

- Commit **BUG-6** (`tokenStore.ts` web fallback) and the `mobile/.env` prod-URL change (or revert `.env` if it shouldn't be committed).
- **BUG-5:** document in `commands.sh` / README that the repo on `~/Desktop` loses file access when Cursor auto-updates; fix = re-grant Full Disk Access or move the repo off Desktop.

### Cluster E — Display-name feature

- `users.name` (nullable); `PATCH /me` to set it; a signup step or post-signup prompt; editable field on the You tab; Day greeting shows "Good evening, {name}" when set, no name otherwise. Backend RGR for the endpoint; frontend direct.

---

## 4. Sequencing

1. **Cluster A tracer bullet (GitHub)** — the one change that revives the product. Do first, prove end to end on the live box.
2. **Cluster B** — small, isolates the webhook from redelivery storms; land right after A so real deliveries are safe.
3. **Finish Cluster A** — remaining sources + dedupe.
4. **Cluster C** (UX) and **Cluster E** (name) — parallelizable, lower risk.
5. **Cluster D** — commit the already-made fixes; document the ops gotcha.

---

## 5. Bug → fix traceability

| Finding | Root cause | Cluster | Priority |
|---|---|---|---|
| BUG-1 polling never delivers | RC-1 | A | P0 |
| BUG-8 no triggers created | RC-1 | A | P0 |
| BUG-9 connections not persisted | RC-2 | A | P0 |
| BUG-10 needs manual refresh | RC-2 / RC-4 | A + C | P1/P2 |
| BUG-11 stale connect attempts | RC-2 | A | P1 |
| BUG-2 500 → redelivery loop | RC-3 | B | P1 |
| BUG-3 non-UUID user 500 | RC-3 | B | P1 |
| BUG-7 "Open You" mis-wired | RC-4 | C | P2 |
| BUG-4 spinner flash | RC-4 | C | P2 |
| BUG-6 secure-store on web | — (fixed) | D | done |
| BUG-5 Cursor TCC EPERM | — (ops) | D | ops |
| Name feature | — | E | P2 |
