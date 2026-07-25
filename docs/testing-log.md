# Testing Log — Raw-IP deployment + app E2E

Date: 2026-07-25. Running log of what was tested, what worked, and the bugs found while validating the production backend (EC2, raw-IP HTTPS) against the local Expo app.

## Environment under test

- **Backend:** EC2 `t3.medium` (`i-0890354b08bca1c00`), `https://52.64.67.235` served by nginx with a **Let's Encrypt IP certificate** (issued via **lego**, not certbot). systemd unit `productivity-backend`, `AUTH_MODE=own`.
- **Mobile:** local Expo **web** (`http://localhost:8081`), `EXPO_PUBLIC_API_URL=https://52.64.67.235`, `EXPO_PUBLIC_AUTH_MODE=own`. CORS allowlisted for localhost ports on the backend.
- **DB:** Supabase project `nmglxvlkterckxurrhnb` (storage only, self-owned auth).

## Verified working (no bug)

- Trusted **HTTPS on the raw Elastic IP** — externally cert-validated (`ssl_verify_result=0`).
- Composio **accepts an IP-literal webhook URL**.
- Backend **receives + HMAC-verifies** a signed Composio webhook over the raw IP.
- **Ingest stores a feed item** for a real UUID user (rule-tier `today`, `type_tag=assigned`).
- **Signup E2E:** `otp/send → otp/verify → register (201) → feed/connections/refresh (200)`. DB records correct: 1 user, 1 refresh token, 1 consumed OTP, 0 feed/connections for a fresh account.

---

## BUG-1 — Composio trigger polling never fires (delivery blocked) — **BLOCKER, upstream (Composio)**

**Symptom:** Issues assigned to the connected GitHub account never produced a webhook delivery to the backend; the feed stayed empty.

**How we tested:**
- Assigned issues to the connected account, then watched the backend for `POST /webhooks/composio` (live `journalctl` tail).
- Inspected the trigger instance's internal `state` (`seen_ids`, `last_synced_at`) via the Composio SDK.
- Queried GitHub *as the connected account* (`GITHUB_LIST_ISSUES_ASSIGNED_TO_THE_AUTHENTICATED_USER`) to confirm the assignments were actually visible.

**What we tried, and what it showed:**
1. **Assign already-existing issues** → no fire. Polling triggers are **edge-triggered**: a (re)sync baselines whatever is currently assigned into `seen_ids` and only fires on items appearing *after*. Pre-existing assignments are adopted as baseline, never delivered.
2. **Lower the poll interval 60 → 1 min** (via `triggers.create` upsert; needed `user_id` due to project 2FA) → config updated, but **`last_synced_at` stayed frozen** at the upsert time for 10+ minutes. The poller was not actually running on the configured cadence.
3. **Disable → re-enable the trigger** → forced exactly **one** sync (advanced `last_synced_at` once, baselined the 5 assigned issues into `seen_ids`), then **stalled again**. No recurring poll.
4. **Assign a fresh issue** afterward → still no delivery, because the recurring poll never runs to detect the new edge.

**Root cause / findings:**
- **Composio is not running the background poll for this project's triggers.** `last_synced_at` never advances on its own; the GitHub triggers show **no "last triggered"** in the dashboard; even Slack (which shows a stale "14 min ago") never delivered to the box.
- The 7 connected accounts + 4 triggers lived under a **`pg-test-…` playground Composio user**, created via API/dashboard — **not** through the app's own connect flow. `public.connections` was empty.

**Status / resolution path:** Upstream Composio polling issue for this test project. Cleared all `pg-test` connections + triggers, and re-testing by connecting **through the app** under a real UUID user, which should create properly-wired, delivering triggers. (Composio *delivery* itself is proven to work — see the synthetic test below.)

---

## BUG-2 — Webhook route returns 500 on any ingest error → Composio redelivery loop — **hardening**

**Found via:** sending a correctly-signed synthetic webhook to `/webhooks/composio`.

**Detail:** `backend/main.py:460` does `return ingest_service.handle(envelope)` with no try/except. The route catches *signature* failures (→ 401) but **not** exceptions inside `ingest.handle` (→ 500). The route's own docstring says unhandled events should return 200 precisely so Composio does not retry — but an ingest *exception* bypasses that and returns 500, which makes Composio **retry the delivery repeatedly** (unbounded redelivery amplification).

**Fix:** wrap `ingest_service.handle` in a try/except that logs and returns 200 (or a 4xx that Composio treats as terminal), so a malformed/unexpected event can't trigger a redelivery storm.

---

## BUG-3 — Non-UUID Composio `user_id` crashes ingest (500) — **data / robustness**

**Found via:** the first synthetic webhook used the `pg-test-86b8d0d9-…` Composio user id.

**Detail:** `metadata.user_id` flows into `supabase_connections_repository.identity_for`, which queries `connections` by `user_id` (a **uuid** column). A non-UUID id (the `pg-test` playground user) makes Postgres raise `invalid input syntax for type uuid (22P02)` → unhandled → **500**. Re-sending the *same* signed webhook with a real UUID user (`2dccd276-…`) returned **200 `{"handled":true,"reason":"ingested"}`** and stored a `feed_items` row — so the backend logic is correct; only a non-UUID id breaks it. Related to BUG-2 (the 500 should be swallowed regardless).

---

## BUG-4 — Signup shows a loading-spinner flash before the empty state — **frontend, minor**

**Observed:** on first successful signup, the screen showed a brief loading circle, then correctly rendered the "Connect your first tool" empty state.

**Detail:** after `POST /auth/register (201)`, the app fires `GET /feed`, `GET /connections`, and `POST /feed/refresh` (~4s total), showing a spinner throughout, before rendering. The empty state itself is **correct** (0 connections, 0 feed items — DB-confirmed). The flash is a UX-polish item: consider rendering the empty state immediately when `/feed` returns empty and there are no connections, rather than waiting on `/feed/refresh`.

**Severity:** cosmetic. Not blocking.

---

## BUG-5 — Expo web `EPERM` reading `package.json` after Cursor auto-update — **env, resolved**

**Symptom:** `npx expo start` web served HTTP 500: `EPERM: operation not permitted, open '.../mobile/package.json'`, even though the file is `-rw-r--r--` and readable from another shell.

**Root cause:** the project lives under `~/Desktop` (a macOS TCC-protected folder). **Cursor auto-updated** (its `.app` bundle timestamp was reset), which **invalidated its Full Disk Access grant**, so the Metro process launched from Cursor lost permission to read Desktop files. (Mac had not rebooted — up 9 days — so not an OS update.)

**Fix:** re-grant **Full Disk Access** to Cursor (toggle off/on, then fully quit + reopen), or move the repo off `~/Desktop` to immunize against future app updates.

---

## BUG-6 — `expo-secure-store` unavailable on web crashes token load — **frontend, fixed**

**Symptom:** on web, `TypeError: ExpoSecureStore.default.getValueWithKeyAsync is not a function` at `tokenStore.ts` (`SecureStore.getItemAsync`).

**Root cause:** `expo-secure-store` is native-only (iOS Keychain / Android Keystore); it has no web implementation. The self-owned auth (`f4d2329`) stores tokens via SecureStore, which breaks in the browser.

**Fix (applied, uncommitted):** added a platform fallback in `mobile/src/auth/tokenStore.ts` — on web use `localStorage`, on device keep the keychain. Native behavior unchanged.

**Note:** other native-only modules will also gap on web — notably **push notifications (`expo-notifications`)** must be tested on a device / dev build, not the browser.

---

## BUG-7 — "Open You" on the Day empty state starts GitHub connect instead of opening the You tab — **frontend**

**Observed:** on the Day page empty state ("Connect your first tool"), clicking **"Open You"** launches the GitHub integration flow instead of navigating to the **You** tab.

**Root cause:** `App.tsx:426` wires the Day screen's `onConnect` to `() => connectSource('github')` — hardcoded to GitHub. That handler is passed `YourDayScreen` → `NothingConnected` (`src/components/states.tsx:118`), whose button is **labeled `"Open You"`** but calls `onConnect`. So the label (open the You tab) and the action (start GitHub OAuth) are mismatched, and the provider is locked to GitHub regardless of what the user might want to connect.

**Fix:** point the Day empty-state action at the **You** tab, e.g. `onConnect={() => navigation.navigate('You')}`, so the user lands on the You screen and chooses which tool to connect (the You screen already does per-provider connect via `connectSource`). Then "Open You" matches its behavior.

**Severity:** functional/UX. Not blocking — the button does start a GitHub connection, so you can still proceed; it's just mislabeled and provider-locked.

---

## BUG-8 — The app never creates Composio triggers on connect — **CRITICAL, missing implementation**

**Observed:** after connecting GitHub through the app, **zero triggers exist** on the Composio account. So no events are ever generated, and the feed can never populate from real activity.

**Root cause:** the connect flow (`backend/services/connections.py`) only calls `connected_accounts.link` (link_url) to create the OAuth account. There is **no trigger-creation code anywhere in the backend** — confirmed by grep: `triggers.create` / `set_webhook_subscription` appear **nowhere**; the only trigger references are the *handlers* in `ingest.py` and a comment in `slack.py`. The event-receiving half (webhook route + ingest mappers) is built; the event-*subscribing* half (creating per-user trigger instances) was never implemented.

**Impact:** this is the actual root of BUG-1. With no triggers, Composio has nothing to poll, so no webhook is ever delivered. The manually-created `pg-test` triggers were the only ones that ever existed.

**Fix:** on a source reaching `ACTIVE`, create its trigger instance(s) for that user via `composio.triggers.create(slug=..., user_id=..., connected_account_id=..., trigger_config=...)` — e.g. GitHub → `GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER` (+ notification); Slack → `SLACK_DIRECT_MESSAGE_RECEIVED` / `SLACK_CHANNEL_MESSAGE_RECEIVED`; etc. (These slugs already have ingest mappers, so once created, delivery → ingest is proven to work.) Backend change → Red-Green-Refactor.

---

## BUG-9 — `public.connections` never persisted after a real connect — **backend**

**Observed:** GitHub is `ACTIVE` in Composio under the user's UUID, but `public.connections` is empty.

**Root cause:** `mark_active` (the DB write) runs **only inside `status()`** when the poll catches `CONNECTED` (`connections.py:138-146`). The web OAuth completed *after* the status poll had stopped, so `mark_active` was never called. `list_sources` (the `GET /connections` refresh) reads live Composio status but **does not persist** the row. So the table stays empty even though the UI shows connected — and ingest's `identity_for` reads that table, so it can't resolve the connection.

**Fix:** persist the connection whenever an `ACTIVE` status is observed (including in `list_sources` / on refresh), or keep polling/reconciling until the row is written. Decouple "row written" from "the poll happened to be running."

---

## BUG-10 — Connection shows only after a manual refresh — **frontend/flow**

**Observed:** after authorizing GitHub, the app didn't show "connected" until a manual refresh.

**Root cause:** the `/connections/github/status` poll ran ~17s then gave up, but the web OAuth round-trip (with Composio's "Taking you back to Composio…" interstitial) finished later. So auto-detection missed the `ACTIVE` transition. On web there's no deep-link return, so the app never re-polled on focus.

**Fix:** re-poll `status` when the app regains focus after the OAuth tab, and/or extend the poll window / backoff. (On native the deep link would trigger this; on web, use a visibility/focus listener.)

---

## BUG-11 — Stale duplicate connection attempts not cleaned up — **minor**

**Observed:** 4 GitHub connected accounts under the user (1 `ACTIVE`, 3 `INITIATED`/`INITIALIZING`) from multiple connect clicks. Each `link` creates a new attempt; abandoned ones are never removed.

**Fix:** on a successful `ACTIVE` connect, delete the other non-active attempts for that (user, toolkit); or dedupe before creating a new link.

---

## FEATURE — Display name (set at signup, shown on Day/You, editable on You) — **enhancement**

**Request:** add a **name** field to the first-run signup flow. If set, show it on the **Day** tab greeting ("Good evening, {name}") and on the **You** tab. If not set, leave the Day greeting without a name, but always show an **editable name field on the You** tab so it can be set/changed later.

**Implementation notes:** add `name` to the `users` table (nullable), an update endpoint (e.g. `PATCH /me`), a signup step or a post-signup prompt, and the You-tab editable field. Greeting falls back to no-name when null.
