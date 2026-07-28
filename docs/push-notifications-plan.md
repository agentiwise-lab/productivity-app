# Push notifications: research, RCA, plan

**Status:** approved for research, awaiting go-ahead to implement
**Branch:** `feature/push-notifications` (worktree at `../productivity-app-notifications`)
**Mocks:** [docs/mockups/notifications.html](mockups/notifications.html)

Goal: when a new event is ingested, send an OS push notification to the user's phone if the
item's tier matches their notification setting. Make the "Notify me" setting real and respected
end to end.

---

## 0. Read this before starting an unattended run

The work splits at a hard line: everything up to "the server decides to send" can be built and
proved without anyone present. Everything past it needs credentials only Vicky can create.

### Phase A, unattended

Migration SQL authored, backend service and repository, endpoints, ingest wiring, all tests green
under `uv run pytest`, mobile client wiring, `app.json` config, the priming card, the notification
small-icon asset. Ends with a full backend test suite passing and a mobile app that requests the
permission and uploads a token.

### Phase B, needs Vicky present

| Step | Why it cannot be automated |
|---|---|
| **FCM V1 service account key** | Firebase console sign-in, generate a private key, upload under EAS credentials. Google account access. **Without this no Android push is delivered at all**, regardless of how correct the code is. |
| **`eas-cli` install** | Not installed on this machine (`eas` not found, `npx eas` fails). Installing a global CLI needs explicit permission, and `eas login` needs Vicky's account. |
| **Preview APK build and install** | Follows from the two above. Expo Go cannot do Android push on SDK 57. |
| **Real-device tap test** | Physically requires a phone. |

Applying migration 0011 and deploying to EC2 were **authorised for the unattended run** (4.10), so
they move into Phase A.

The failure mode to avoid: an unattended run that ends "complete" while nothing has ever reached a
phone. Phase A's honest end state is "every test passes and the server posts to Expo", not "push
works".

---

## 0.1 Review pass: what the first draft got wrong

Four corrections, found by reading the code the plan was leaning on rather than trusting the plan.

**1. `notify()` takes one token, and looping over devices would silently drop notifications.**
`DefaultNotificationService.notify(token, items, prefs, level)` marks items into `_notified` after a
successful send. Called once per device in a loop, the first device marks the item seen and every
subsequent device filters it out as already-notified. A user with a phone and a tablet would get the
notification on exactly one of them, chosen by dict order. The signature has to become
`notify(tokens: list[str], ...)` with a single seen-mark after the fan-out.

**2. `PushTransport.send()` returns `None`, so `DeviceNotRegistered` is unreachable.** The plan said
to delete dead tokens on that error, but the Protocol discards Expo's response. The contract has to
become `send(messages) -> list[dict]` returning tickets, which is a breaking change to an existing
tested Protocol: `FakePush.send` in `tests/test_notifications.py` must return a list too.

**3. The Redis client is local to `_build_repository()` and never returned**, so the planned
`SeenStore` had nothing to bind to. Composition opens its own `redis.from_url(REDIS_URL)` for the
seen store rather than reaching into `repo._r`. A second connection is cheap and leaves
`_build_repository` untouched.

**4. The webhook path pushes one item at a time, which contradicts "one notification per batch."**
`_classify_soon` fires per item, so three things arriving within a minute produce three separate
buzzes. The batch branch of `build_message()` is never reached from the webhook path at all. The
docstring's promise was written for the refresh-sweep path, where a batch genuinely exists. Settled
in 4.10: a 25-second debounce window, so the promise is kept.

Two smaller gaps: `Profile` and `UserRecord` both need a `notify_level` field (neither was
mentioned), and `PATCH /me`'s existing `NameBody` treats `None` as "clear the name", which cannot be
reused for `notify_level` where `None` must mean "unchanged".

## 0.2 Second review pass

Six more, found by checking the plan against the schema, the router and the ingest control flow
rather than against itself.

**1. `device_tokens` had no RLS.** The table was specified with a hand-wave at "the service-role
pattern from migration 0005" and no DDL. Every other table in this database enables RLS and revokes
anon and authenticated privileges, and a push token is a send-anything-to-this-device capability, so
it is the last table to leave open. Real DDL is now in 4.1.

**2. The upsert did not reassign `user_id`, which is a privacy bug.** `token` is the primary key
precisely because a device can move between accounts, but the plan never wrote the `on conflict do
update`. Without it, a phone that signs out of account A and into account B keeps receiving A's
notifications. Now spelled out, with the reason.

**3. The migration was not idempotent.** Postgres has no `add constraint if not exists`, so an
inline `check` on `add column if not exists` fails on a re-run. It is applied unattended, so it is
now split into an `add column`, a `drop constraint if exists`, and an `add constraint`.

**4. `DELETE /devices/{token}` puts `ExponentPushToken[...]` in a URL path.** Square brackets are
reserved characters RFC 3986 does not allow unencoded in a path segment, so the value has to survive
encoding by `fetch`, decoding by Caddy and re-decoding by Starlette with all three agreeing. Changed
to `POST /devices/unregister` with the token in the body, which also **removes the CORS
`allow_methods` edit entirely**: the existing `[GET, POST, PATCH, OPTIONS]` already covers every
route this feature adds.

**5. The claimed failure isolation in the ingest seam did not exist.** Detailed in 4.4: the
deterministic branch has no `try` at all, and the background branch swallows exceptions into a
never-retrieved future. The no-raise guarantee had to move into `DefaultPushService`.

**6. The debounce would have sent 25-second-stale items.** `_should_notify` reads `handled_at` and
`snoozed_until`, and a snapshot buffered before the user opened the app knows neither. Buzzing about
something the user just handled is the exact failure the product exists to prevent.
`RedisFeedRepository.get(user_id, item_id)` is public, so the flush now re-reads.

One design improvement fell out of the same pass: **no database or Redis reads happen on the webhook
path at all** any more. Buffering is pure memory and every read moves to the flush, which keeps the
latency promise `ingest.py` already makes, turns per-item reads into per-window reads, and means the
notify level is read at send time rather than at buffer time.

---

## 1. Inward findings

### The backend push service already exists and is dead code

[backend/services/notifications.py](../backend/services/notifications.py) (163 lines) already
contains a complete, well-designed push layer:

- `NotifyLevel` enum: `urgent` / `urgent_today` / `all` / `off`. **Wire values already match the
  mobile type exactly** (`mobile/src/screens/YouScreen.tsx:37`), so no translation layer is needed.
- `_ALLOWED` tier map: `URGENT` to `{URGENT}`, `URGENT_TODAY` to `{URGENT, TODAY}`, `ALL` to
  `{URGENT, TODAY, CAN_WAIT}`, `OFF` to `{}`. `Tier.NOISE` is deliberately excluded from every
  level, including `ALL`.
- `PushTransport` Protocol (the outward seam) and `ExpoPushTransport`, which posts to
  `https://exp.host/--/api/v2/push/send`.
- `DefaultNotificationService.notify(token, items, prefs, level)` with the handled / snoozed /
  muted-channel / muted-repo / already-notified filters.
- `build_message()` producing the batch copy.
- Covered by [tests/test_notifications.py](../tests/test_notifications.py) with a `FakePush` at the
  contract boundary.

**It is imported by nothing.** A grep across `backend/` and `tests/` returns zero references
outside its own module and its own test. It is absent from `composition.py`, `main.py` and
`ingest.py`.

The gap is therefore smaller than it first looks: the tier-versus-preference **filter logic is
written and tested**. What is missing is everything on either side of it, the token, the persisted
level, and the call site.

### What is there versus what is needed

| Layer | There | Needed |
|---|---|---|
| Tier to level filter | `DefaultNotificationService` + `_ALLOWED` | nothing, reuse |
| Expo HTTP transport | `ExpoPushTransport` | ticket handling, `DeviceNotRegistered` unregister |
| Ingest seam | `_classify_soon()` calls `self._publish(user_id)` at `ingest.py:281` and `:287`; `item` and `user_id` both in scope | a second injected callback alongside `publish` |
| Dedupe | in-process `set` on the service instance | cross-process store (Redis is already wired) |
| `users.notify_level` | absent | migration 0011 |
| Device tokens | absent | migration 0011 table + repository |
| Settings endpoint | `GET /me` and `PATCH /me` (`main.py:403`, `:413`), `NameBody` at `main.py:172`, to `DefaultProfileService` to `SupabaseCredentialsRepository.set_name` | extend this exact path, do not build a parallel one |
| Token register/unregister | absent | `POST /devices`, `POST /devices/unregister`. Both covered by the existing CORS `allow_methods` |
| Mobile persisted level | `useState('urgent')` at `App.tsx:161`, resets every launch | read from `GET /me`, write via `PATCH /me` |
| Mobile client methods | `me()` / `setName()` at `client.ts:254-265` | `setNotifyLevel()`, `registerDevice()`, `unregisterDevice()` |
| expo-notifications | `~57.0.7` and `expo-device ~57.0.1` in `package.json` | zero usage: no import, no permission request, no handler, no config plugin in `app.json` |
| `projectId` | `extra.eas.projectId = 474647b4-...` present | consumed via `expo-constants` |
| Onboarding hook | `justSignedUp` to name modal at `App.tsx:322` | priming screen mirrors this pattern |

---

## 2. Outward findings

### Recommendation: Expo Notifications plus the Expo Push API

**Expo Push API (chosen).** One POST to `exp.host/--/api/v2/push/send` with
`{to: ExponentPushToken[...], title, body, data}` reaches both platforms. Expo brokers to FCM
(Android) and APNs (iOS). Free, no per-notification charge. Limits: **100 messages per request,
600 notifications per second per project**. Neither ceiling is a real constraint at our scale.

**Direct FCM plus APNs (rejected).** Two senders, two credential sets, two payload schemas, two
error taxonomies, and a JWT-signing loop for APNs. It buys nothing here. Worth revisiting only past
600/sec or for APNs features Expo does not proxy. `getDevicePushTokenAsync()` returns the native
token if we ever migrate, so this is not a one-way door.

**OneSignal (rejected).** Adds a vendor, an SDK, a dashboard and a data-processing relationship, to
solve a problem `ExpoPushTransport` already solves in twelve lines. Its value is campaign and
segmentation tooling, which is the opposite of this product's thesis that a buzz means something.

### Is the implementation the same on iOS and Android?

**Client and server code: identical.** Same `requestPermissionsAsync()`, same
`getExpoPushTokenAsync({projectId})`, same server payload.

**Credentials and permission mechanics: different.**

- **Android:** an **FCM V1 service account key** uploaded to EAS. Firebase console, project
  settings, service accounts, generate private key, then EAS credentials, "FCM V1 service account
  key". Free.
- **iOS:** an **APNs key**, which requires the **$99/yr Apple Developer Program**. EAS generates and
  manages the key once the account is linked. No account, no iOS push, no workaround.

Android additionally needs a **notification channel** created client-side via
`setNotificationChannelAsync`. Skipping it files our notifications under the user-facing "Default"
channel, which the Expo docs explicitly warn against. We create one channel, `urgent`, at
`IMPORTANCE_HIGH`, and send with `priority: 'high'`; normal priority gets batched by Doze and can
land an hour late, which for an urgent item is the same as not landing.

### Permissions

- **iOS:** the system alert, fired by `requestPermissionsAsync()`. **One shot.** A denial is close
  to permanent short of a trip to Settings.
- **Android 13+ (API 33):** `POST_NOTIFICATIONS` is a runtime permission, requested through the same
  `requestPermissionsAsync()` call, so our code does not branch. Android 12 and below grant it at
  install.

### Background versus foreground

Background and killed-app delivery is the OS's job and works once credentials are right. Foreground
display is **not automatic**: without a `setNotificationHandler` returning `shouldShowBanner` and
`shouldPlaySound`, a notification arriving while the app is open is silently swallowed. This is the
most common "push is broken" report, and it is a client bug. Expo's troubleshooting names the
inverse symptom (foreground works, background does not) as the tell for misconfigured credentials.

### Token lifecycle

`ExponentPushToken[...]` is stable for an install but not permanent: it rotates on reinstall, on
some restores, and on FCM/APNs re-registration. The correct pattern:

1. Re-fetch and re-upload the token on **every app launch** as an idempotent upsert, not once at
   signup.
2. Subscribe to `addPushTokenListener` for mid-session rotation.
3. Server-side, when a ticket or receipt returns `DeviceNotRegistered`, delete that token row. Expo
   is explicit: stop sending to it.

This is why device tokens need their own table rather than a `users.push_token` column: one user,
several devices.

### The Expo Go trap

**Push notifications no longer work in Expo Go on Android as of SDK 53** (deprecated in 52, removed
in 53). iOS in Expo Go still works because EAS can auto-configure it. On SDK 57 the Android
verification loop is therefore an EAS development or preview build, not `expo start`. This repo has
already been bitten by one Expo Go SDK-mismatch gotcha, so budget for it.

### Best-practice permission UX

The OS prompt is a one-shot resource and a cold prompt converts far worse than a primed one. The
pattern:

1. **Priming screen first**, our own UI, fully recoverable, no OS involvement.
2. **Only the affirmative button fires the OS prompt.** "Not now" leaves the OS permission unasked,
   so we can ask again later from the You tab.
3. **Placement: after the first source connects, not at signup.** Asking before there is a feed is
   asking somebody to consent to notifications about nothing.

**Sources**

- <https://docs.expo.dev/push-notifications/push-notifications-setup/>
- <https://docs.expo.dev/push-notifications/sending-notifications/>
- <https://docs.expo.dev/push-notifications/faq/>
- <https://docs.expo.dev/versions/latest/sdk/notifications/>
- <https://expo.dev/changelog/sdk-53>
- <https://appycodes.dev/blog/push-notifications-expo-fcm-apns-2026/>

---

## 3. RCA

**Why the setting is a no-op.** `notifyLevel` is a `useState` in `Shell()` at `App.tsx:161`. Its
only consumer is `YouScreen`'s own rendering. It is never sent anywhere, never read back, and resets
to `'urgent'` on every cold start. There is no `users.notify_level` column, no endpoint accepting
it, and no backend reader. It is a control wired to itself.

**The full chain from "event ingested" to "phone buzzes".**

| # | Step | Status |
|---|---|---|
| 1 | Composio trigger to `POST /webhooks/composio` to `WebhookIngestService.handle` | works |
| 2 | Item stored, `_classify_soon` resolves the final tier | works |
| 3 | `self._publish(user_id)` fires on the Redis channel | works |
| 4 | Something asks "should this user be pushed about this item?" | **BREAK.** No call site. `DefaultNotificationService` is never constructed. |
| 5 | Read the user's `notify_level` | **BREAK.** Column does not exist. |
| 6 | Look up the user's device tokens | **BREAK.** Table does not exist. |
| 7 | Tier versus level filter | **exists and is tested** |
| 8 | POST to Expo | `ExpoPushTransport` exists, never instantiated |
| 9 | Expo to FCM (Android) | **BREAK.** No FCM V1 service account key in EAS. |
| 9' | Expo to APNs (iOS) | **BREAK.** No Apple Developer account, therefore no APNs key. |
| 10 | Device holds a push token | **BREAK.** `getExpoPushTokenAsync` is never called. |
| 11 | OS permission granted | **BREAK.** No `requestPermissionsAsync`, no priming screen, no config plugin, no Android channel. |
| 12 | Tap opens the item | **BREAK.** No response listener, no deep-link route. |

Eight breaks. Six are missing plumbing around working logic; two (FCM key, APNs key) are
account and credential work outside the codebase.

**Secondary latent problem.** `DefaultNotificationService._notified` is a process-local `set`. Under
a restarted or multi-worker uvicorn it forgets, and "once per item, ever" silently degrades to "once
per item per process". Its own docstring flags this. Wiring it as-is into a live path would ship
that bug.

---

## 4. Plan

### 4.0 File inventory

Written out because an unattended run cannot ask "was there another implementation of this
Protocol?" halfway through. Every Protocol below has more than one implementation, and missing one
is a green test suite that fails at runtime.

**New**

| File | Holds |
|---|---|
| `supabase/migrations/0011_push_notifications.sql` | 4.1 |
| `backend/repositories/device_token_repository.py` | Protocol **and** `InMemoryDeviceTokenRepository`, matching how `credentials_repository.py` pairs them in one file |
| `backend/repositories/supabase_device_token_repository.py` | the Postgres implementation |
| `backend/services/push.py` | `PushService` Protocol, `DefaultPushService`, `PendingBuffer`, `SeenStore`, `RedisSeenStore` |
| `tests/test_push.py` | 4.8 |
| `mobile/src/push/register.ts` | permission, token, upload |
| `mobile/src/components/NotificationPrompt.tsx` | 4.6 |
| `mobile/assets/notification-icon.png` | white-on-transparent silhouette |

**Modified**

| File | Change |
|---|---|
| `backend/services/notifications.py` | `notify(tokens: list[str], ...)`, `PushTransport.send -> list[dict]`, injected `SeenStore` |
| `backend/models/profile.py` | `Profile.notify_level` |
| `backend/models/auth.py` | `UserRecord.notify_level` |
| `backend/repositories/credentials_repository.py` | `set_notify_level` on the Protocol **and on `InMemoryCredentialsRepository`**, which is what the tests run against |
| `backend/repositories/supabase_credentials_repository.py` | `set_notify_level`, plus `notify_level` added to **both** `select(...)` column lists |
| `backend/services/profile.py` | `set_notify_level`, and `CredentialsRepositoryLike` grows the method |
| `backend/services/ingest.py` | `on_item_ready` parameter, called in both branches of `_classify_soon` |
| `backend/main.py` | `ProfileBody`, `/devices`, `/devices/unregister`, wire `on_item_ready` |
| `backend/composition.py` | build the token repo, seen store, push service; own `redis.from_url` |
| `tests/test_notifications.py` | new signatures, `FakePush.send` returns a list |
| `tests/test_ingest.py`, `tests/test_profile.py`, `tests/test_api.py` | 4.8 |
| `tests/fakes.py` / `tests/fake_supabase.py` | whatever the new column and repository need |
| `mobile/app.json` | `expo-notifications` plugin |
| `mobile/App.tsx` | handler, listeners, persisted level, priming trigger |
| `mobile/src/api/client.ts`, `mobile/src/api/types.ts` | three methods, `Profile.notify_level` |
| `mobile/src/screens/YouScreen.tsx` | OS-denied banner state |

**No new backend environment variable is required.** Expo's push endpoint is unauthenticated for
sending, and `REDIS_URL` already exists on the box. Nothing needs adding to the `.env` at the repo
root before the deploy, which removes the most common cause of a restart coming back unhealthy.

### 4.1 Migration 0011

```sql
alter table public.users
  add column if not exists notify_level text not null default 'urgent';

alter table public.users
  drop constraint if exists users_notify_level_check;
alter table public.users
  add constraint users_notify_level_check
  check (notify_level in ('urgent','urgent_today','all','off'));

create table if not exists public.device_tokens (
  token        text primary key,            -- ExponentPushToken[...]
  user_id      uuid not null references public.users(id) on delete cascade,
  platform     text not null check (platform in ('ios','android')),
  created_at   timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);
create index if not exists device_tokens_user_id_idx on public.device_tokens(user_id);

-- Service role bypasses RLS; enabling it with no policy denies anon and
-- authenticated, which is what every other table does (migration 0005). A push
-- token is a send-anything-to-this-device capability, so it belongs with the
-- credential tables rather than with the feed.
alter table public.device_tokens enable row level security;
revoke all on public.device_tokens from anon, authenticated;
```

`token` as the primary key rather than a surrogate id: a token is globally unique and can migrate
between users (shared device, account switch), which makes the upsert trivial and makes stale rows
impossible to duplicate. That migration case is exactly why the upsert must reassign the owner:

```sql
insert into public.device_tokens (token, user_id, platform)
values (:token, :user_id, :platform)
on conflict (token) do update
  set user_id = excluded.user_id,
      platform = excluded.platform,
      last_seen_at = now();
```

Without the `do update` on `user_id`, a phone that signs out of account A and into account B keeps
delivering A's notifications to B's session. This is the one line in the migration where getting it
wrong is a privacy bug rather than a papercut.

**The `add column ... check (...)` split is not stylistic.** Postgres has no
`add constraint if not exists`, so an inline `check` on a re-run of `add column if not exists` fails
the whole migration. Dropping the named constraint first makes the file idempotent, which matters
because it is applied unattended.

### 4.2 Contracts, written and tested before any implementation

**`backend/repositories/device_token_repository.py`** Protocol:

```
upsert(user_id, token, platform) -> None
delete(token) -> None
tokens_for(user_id) -> list[str]
```

**Extend `CredentialsRepositoryLike` and `ProfileService`** rather than adding a parallel service:

```
repo:    set_notify_level(user_id, level) -> None
service: set_notify_level(user_id, level) -> Profile
```

Model changes that follow, both of which the first draft missed:

- `backend/models/profile.py`: `Profile` gains `notify_level: NotifyLevel = NotifyLevel.URGENT`, so
  `GET /me` already returns it and the mobile stub replacement is a one-field read.
- `backend/models/auth.py`: `UserRecord` gains `notify_level: str = "urgent"`, and both
  `select("id, email, password_hash, name, created_at")` calls in
  `supabase_credentials_repository.py` must add the column or the field silently keeps its default
  for every user.

**Two corrected contracts**, per the review above:

```
PushTransport.send(messages: list[dict]) -> list[dict]     # was -> None; returns tickets
DefaultNotificationService.notify(
    tokens: list[str], items, prefs, level) -> None        # was a single token
```

Both are breaking changes to code that already has tests, so they are the first red step: update
`tests/test_notifications.py` to the new signatures, watch it fail, then change the service.

**`backend/services/push.py`**, the new module, named `DefaultPushService` per the
provider-agnostic convention:

```
class PushService(Protocol):
    def push_for_item(self, user_id: str, item: FeedItem) -> None: ...
```

One method. It owns: buffer the item, and at flush read the level, read the tokens, delegate the
tier / mute / snooze decision to the existing `DefaultNotificationService`, send, and handle
`DeviceNotRegistered` by calling `repo.delete(token)`. It is the deep module;
`DefaultNotificationService` becomes its already-tested policy core and `PushTransport` stays the
outward seam.

**`push_for_item` must never raise, and that is load-bearing rather than tidy.** See 4.4: the
deterministic branch of `_classify_soon` is not inside any `try`, so an exception there propagates
out of `handle()`. It would be caught by the blanket handler in `main.py`, but the webhook would then
answer `ingest_error` for an item that was in fact ingested successfully. The no-raise guarantee lives
in this class, not in the caller.

**No I/O on the webhook path.** `push_for_item` does nothing but append to the in-memory buffer and,
on the call that opens a window, schedule the flush. Every database and Redis read happens on the
timer thread 25 seconds later. Three reasons, in order of importance:

1. The webhook path is already latency-sensitive by design. `ingest.py` moves classification off it
   specifically because, in its own words, Composio retry-storms on a slow HTTP response. Adding two
   round trips per item to read a level and a token list would undo that.
2. One read per window instead of one per item.
3. The level read at flush time is the most recent one, so a user who switches to `off` inside the
   window is not buzzed by an item buffered a moment earlier.

**Items are re-read at flush, not sent from the buffered snapshot.** `RedisFeedRepository.get(user_id,
item_id)` is public and cheap. A snapshot buffered 25 seconds ago does not know that the user has
since opened the app and handled or snoozed the item, and `_should_notify` checks exactly those two
fields. Buzzing about something the user just dealt with is the precise failure this product exists
to avoid, so the flush re-reads each buffered id, drops any that have vanished, and passes the fresh
items to `notify`.

**Dedupe fix.** `DefaultNotificationService` gains a `SeenStore` Protocol
(`mark_if_new(item_id) -> bool`) injected at construction, defaulting to the current in-process set.
Production binds a Redis-backed implementation, `SETNX` on `notified:{item_id}` with a 24h TTL
matching the feed's. This is the minimum change that makes "once, ever" true across workers, and it
also covers a missed-then-backfilled webhook: a duplicate arriving from the refresh sweep is
swallowed rather than double-buzzing.

**Where the Redis client comes from.** `_build_repository()` in `composition.py` creates its client
locally and does not return it, so there is nothing to reach for. `build_app()` opens its own
`redis.from_url(os.environ["REDIS_URL"])` for the seen store when `REDIS_URL` is set, and falls back
to the in-process set when it is not. A second connection to the same server is cheap, and it leaves
`_build_repository` untouched rather than widening its return type for one caller.

**Where preferences come from.** `DefaultPushService` takes its own
`prefs_for: Callable[[str], UserPreferences]`, defaulting to
`lambda user_id: UserPreferences(user_id=user_id)`, which is exactly what `WebhookIngestService`
already defaults to. Worth knowing while reading the mute filters: nothing in the app populates
`muted_channels` or `muted_repos` today, so those branches are inert in production and are exercised
only by tests.

### 4.3 Endpoints

All three carry `user_id: str = Depends(current_user)`, like every other authenticated route.

- `PATCH /me` accepts `notify_level` alongside `name`. `NameBody` becomes `ProfileBody` with both
  fields optional. `None` means "unchanged" for `notify_level`, which is deliberately different from
  `name`, where `None` means "clear"; the asymmetry is handled in the service and gets a comment.
- `POST /devices`, body `{token, platform}`, returns 204. Idempotent upsert, safe every launch.
- `POST /devices/unregister`, body `{token}`, returns 204. Called on sign-out and when the level
  goes to `off`.

**Why unregister is a POST and not `DELETE /devices/{token}`, which is what the first draft said.**
An Expo token is literally `ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]`. Square brackets are reserved
characters that RFC 3986 does not permit unencoded in a path segment, so the value has to survive
percent-encoding by `fetch`, decoding by Caddy, and re-decoding by Starlette's router without any of
the three disagreeing. That is a needless bet to place on a token string, and it fails in a way that
is miserable to diagnose: a 404 on some clients and not others.

Putting the token in a JSON body sidesteps the encoding question entirely, and it has a second
payoff: **the CORS `allow_methods` change is no longer needed at all.** The current
`[GET, POST, PATCH, OPTIONS]` already covers every route this feature adds. One fewer edit to a
shared middleware config, and one fewer way for the web build to break.

### 4.4 The ingest seam

`WebhookIngestService.__init__` gains `on_item_ready: Callable[[str, FeedItem], None] | None = None`
defaulting to a no-op, mirroring the existing `publish` parameter exactly.

In `_classify_soon`, both branches call it immediately after `self._publish(user_id)`: the
deterministic branch at `ingest.py:281` and inside the background lambda at `:287`. Calling it after
the classify lands is what guarantees the tier is final; pushing earlier would push on a placeholder.

Wired in `main.py` next to `publish=getattr(repo, "publish_change", None)`.
`WebhookIngestService` never imports `DefaultPushService`, it takes a callable, so ingest tests need
no push fake.

**Failure isolation, corrected.** The first draft claimed the callback sits inside a protecting
`try`. Re-reading `_classify_soon`, that is only half true and the wrong half:

- The **deterministic branch** calls `self._publish(user_id)` and returns, with no `try` around it.
  An exception here propagates out of `handle()`.
- The existing `try` wraps only the *scheduling* of the background work, not its execution.
- Inside the **background lambda**, an exception is swallowed by the executor and never retrieved,
  so it disappears without a log line.

Neither path is a safety net worth relying on: one turns a successful ingest into a reported
`ingest_error`, the other loses the error entirely. The guarantee therefore lives in
`DefaultPushService.push_for_item`, which catches everything and logs, exactly as
`DefaultNotificationService.notify` already does for a failed send. The flush callback on the timer
thread needs the same treatment for the same reason: an uncaught exception on a `threading.Timer`
thread prints to stderr and kills nothing, which means a silent, permanent loss of that window's
notification.

### 4.5 Client wiring

1. `app.json`: add `"expo-notifications"` to `plugins` with `icon` and `color`. Keep
   `extra.eas.projectId`. The plugin `icon` is the Android **status-bar small icon**, which Android
   renders as a flat silhouette: any colour or interior detail is discarded and only the alpha
   channel survives. The two-card mark works as a silhouette, but it has to be exported as a
   dedicated white-on-transparent asset rather than pointed at the existing launcher icon, which
   would come out as a solid blob. `color` is the tint Android applies behind it.
2. `mobile/src/push/register.ts`, one module, one exported `registerForPush(api)`. Guards on
   `Device.isDevice`; calls `getPermissionsAsync` then `requestPermissionsAsync` only when
   undetermined; creates the Android `urgent` channel; gets the token; POSTs to `/devices`. Called
   on every launch when the persisted level is not `off`. It also returns the token so the caller
   can cache it, because unregister needs a token in hand and re-deriving one at sign-out time is
   both slower and able to fail.

   The projectId lookup needs the documented fallback, not just the happy path:

   ```ts
   const projectId =
     Constants?.expoConfig?.extra?.eas?.projectId ?? Constants?.easConfig?.projectId;
   ```

   `expoConfig` is null in some production build contexts, and `getExpoPushTokenAsync` without a
   projectId throws rather than degrading. A crash on launch inside the one function that is called
   on every launch is not a failure mode to discover on a real phone.
3. `setNotificationHandler` at module scope in `App.tsx` so foreground notifications appear.
4. `addNotificationResponseReceivedListener` reads `data.item_id` and opens the item sheet through
   the existing `openRow` path. Cold-start taps come from `getLastNotificationResponseAsync()` after
   the feed has loaded, because the live listener never fired.
5. `addPushTokenListener` re-uploads on rotation.
6. Replace `App.tsx:161`: `notifyLevel` initialises from `loadProfile()` and `onSetNotifyLevel`
   becomes optimistic-set then `api.setNotifyLevel()`, reverting on failure. Going from `off` to any
   level triggers `registerForPush`; going to `off` posts the cached token to `/devices/unregister`.
   If no token is cached (the app has not registered this launch), the level write still happens and
   the unregister is skipped: the server-side `off` already stops every send, so the token row is
   redundant rather than harmful, and it is cleaned up on the next `DeviceNotRegistered` or the next
   launch that re-registers.
7. `client.ts`: `setNotifyLevel(level)`, `registerDevice(token, platform)`,
   `unregisterDevice(token)`.
8. New You-tab state: **on in the app, denied by the OS.** The preference stays on, and an inline
   banner explains why nothing is arriving and deep-links to Settings. Firing another OS prompt here
   does nothing, because the prompt has already been spent.

### 4.6 Priming screen

`mobile/src/components/NotificationPrompt.tsx`, a centred modal card.

**It reuses `NamePrompt`'s geometry exactly**, because that is the closest sibling in the app: the
other modal shown once, right after signup. Scrim, `space.lg` page padding, a `c.raised` card at
`radius.lg` with `space.lg` padding and a `space.md` gap, left-aligned text, actions right-aligned
on one row. No new shape is introduced.

**Sizes are the house sizes, not invented ones.**

| Element | Value | Source |
|---|---|---|
| Modal card | `radius.lg` (16), `space.lg` (24) padding, `space.md` (16) gap | `NamePrompt.tsx` |
| Primary action | pill, `space.xs` (8) vertical and `space.md` (16) horizontal padding around `role="label"`, which lands at 32 tall | `NamePrompt.tsx` Save |
| Secondary action | plain `role="label"` text, `tone="mid"`, `space.xs` padding | `NamePrompt.tsx` Cancel |
| Full-width button (screens, not modals) | `size.bigButton` (48), `radius.md` (12), `role="body"` at weight 500 | `ui.tsx` `BigButton` |
| Text field | height 46, `radius.md`, 1px `c.border`, `c.surface` fill | `AuthKit.tsx` `Field` |
| Segmented | `size.segmented` (32), `radius.pill`, 2pt padding, `role="label"` options | `ui.tsx` `Segmented` |
| Toggle | 44x26, 22 knob, `c.high` fill when on | `ui.tsx` `Toggle` |

A 52-tall full-bleed button inside a 345-wide card reads as a landing page rather than as this app.
The primary action in a modal is the 32-tall pill, and full-width 48pt buttons are for screens.

**The mark is `AuthGraphic`**, the two offset rounded cards from
`mobile/src/screens/auth/AuthKit.tsx`, at 52pt in the card. The same glyph is the launcher icon the
OS composites into every notification row, so the thing asking for the permission is visibly the
thing that signed the user in. It stays neutral: this app reserves colour for tiers, and an icon in
the urgent hue would claim a tier the app itself does not have.

**Placement: the first time a source finishes connecting.** The `justSignedUp` to name-modal effect
at `App.tsx:322` is the pattern to mirror, but the trigger is `connectedCount` going 0 to 1,
persisted to a primed-once flag so it never re-nags.

Copy:

> **We'll only buzz for what's urgent**
>
> Not every email. Not every Slack message. Just the things that need you before end of day.
>
> And never twice for the same thing.
>
> `Not now`   `[ TURN THEM ON ]`

Actions read right-aligned on one row, secondary first, exactly as `NamePrompt` places Cancel and
Save.

Three claims, each of which the code actually keeps: the tier filter, the end-of-day bound, and the
once-ever dedupe. "Turn them on" fires the OS prompt (iOS alert, or Android 13+
`POST_NOTIFICATIONS`) and then registers the token. "Not now" dismisses and leaves the OS permission
unasked, so the You tab can offer it again. If the OS permission is already denied at the system
level, the You toggle deep-links to Settings rather than firing a prompt that will not appear.

### 4.7 Platform credentials

- **Android, now.** Create the Firebase project, generate the FCM V1 service account JSON, upload
  via `eas credentials`, Android, FCM V1. Free, and it unblocks the whole verification loop.
- **iOS, deferred.** Needs the $99/yr Apple Developer Program. The code path is identical, so this
  is a credential task, not an engineering one. Every artifact above ships iOS-ready.

### 4.8 Tests, Red-Green-Refactor, in `tests/` at repo root

Failing test first, `Fake*` at the contract boundary, never touching internals.

- `test_notifications.py` (extend): `SeenStore` injection, the same item twice pushes once. Existing
  coverage stays green.
- `test_push.py` (new): `FakeDeviceTokenRepository`, `FakePush`, and a `FakeSchedule` that runs the
  flush immediately so **no test sleeps**. Level `off` sends nothing; `urgent` sends for URGENT and
  stays silent for TODAY; `urgent_today` sends for both; a user with two devices gets the
  notification on **both** (the regression that the single-token signature would have caused);
  `DeviceNotRegistered` in the ticket deletes exactly that token; a raising transport is swallowed
  and no item is marked seen.
- `test_push.py`, debounce specifically: three items inside one window produce **one** send carrying
  all three; only the first `add` opens a window, so three items schedule one flush and not three;
  a second flush for the same user drains empty and sends nothing; and items are marked seen at
  flush rather than at buffer time, proved by asserting that a buffered-then-never-flushed item is
  still eligible on the next window.
- `test_ingest.py` (extend): a `FakePushService` recording calls proves `on_item_ready` fires once
  per ready item, after classification, and that a raising push service still returns
  `handled=True`.
- `test_profile.py` (extend): `set_notify_level` round-trips, an invalid level is rejected, `name`
  and `notify_level` are independently updatable.
- `test_api.py` (extend): `POST /devices` is idempotent across repeated calls; posting the same
  token as a second user **moves** it rather than duplicating it (the privacy case from 4.1);
  `POST /devices/unregister` returns 204 and removes the row; `PATCH /me` with `notify_level`
  persists and with only `name` leaves `notify_level` untouched; every one of the three routes
  answers 401 without a token.

### 4.9 Verification

**Unattended (Phase A).** The end state is "every test passes and the server posts to Expo", which
is not the same as "push works", and the run must not claim otherwise.

1. `uv run pytest` green across the whole suite, not just the new files. The two contract changes
   in 4.2 touch existing tests, so a green full suite is the proof that nothing else regressed.
2. Migration 0011 authored under `supabase/migrations/`, then applied to the live project.
3. A local end-to-end check with a `FakePush` and a synchronous `schedule`: post two synthetic
   Composio envelopes to `/webhooks/composio` against an in-memory build and assert that **one**
   message reached the transport carrying **both** items, with the right title, body and
   `data.item_ids`. Then post the first envelope again and assert the transport is untouched.
4. `npx tsc --noEmit` in `mobile/` clean.
5. rsync to `productivity_app_test`, `sudo systemctl restart productivity-backend`, then curl `/me`
   and confirm `notify_level` is present in the response and the service is healthy. If the restart
   does not come back clean, roll back the rsync and stop rather than leaving the box down.

**Attended (Phase B), in this order, because each step needs the one before it.**

6. `npm i -g eas-cli`, then `eas login`.
7. Firebase project, FCM V1 service account key, upload under EAS credentials.
8. Set `app.json` `name` to something that reads properly on a lock screen.
9. `eas build -p android --profile preview`, install the APK on a real phone.
10. Sign in, connect a source, complete the priming card, confirm a row lands in `device_tokens`.
11. Trigger a real Gmail or Slack event that classifies URGENT. Confirm the notification lands with
    the app backgrounded, that tapping it opens that item, and that a second identical event does
    not double-buzz.
12. Trigger two urgent events a few seconds apart and confirm they arrive as **one** notification,
    which is the debounce window doing its job.
13. Set the level to `off` in You, repeat, confirm silence.

### 4.10 Settled decisions

**Coalescing: a 25-second debounce window.** Vicky's call (2026-07-27). The promise in the service's
own docstring is kept rather than quietly dropped: a burst of urgent items produces one buzz.

The design, and why it is safe here:

```
class PendingBuffer(Protocol):
    def add(self, user_id: str, item: FeedItem) -> bool: ...   # True = you opened the window
    def drain(self, user_id: str) -> list[FeedItem]: ...       # atomic, returns [] if already drained
```

`DefaultPushService.push_for_item` appends to the buffer. The call that opens a fresh window (the
one where `add` returns `True`) schedules a flush via an injected
`schedule: Callable[[float, Callable[[], None]], None]`, which is `threading.Timer` in production
and a synchronous "call it now" in tests, so no test ever sleeps. The flush drains, filters through
`DefaultNotificationService.notify(tokens, items, prefs, level)` with the full list, and sends one
message. `build_message()`'s batch branch finally gets exercised by the real path.

**The buffer is in-process, deliberately.** `docs/deployment-plan.md:154` fixes this deployment at a
**single uvicorn worker** (the classification cache requires it), so an in-process dict cannot
fragment across workers, and a Redis-backed buffer would buy nothing for real complexity. The
`SeenStore` stays Redis-backed, because its job is to survive restarts and the buffer's is not.

**Accepted cost:** a backend restart inside a live 25-second window drops that buzz. The items are
still in the feed and still on the next screen the user opens, and `SeenStore` will not let them be
re-announced later. This was accepted knowingly when the window was chosen.

**Two ordering traps the implementation must not fall into**, both of which would produce a subtly
wrong result that still passes a naive test:

1. **Mark seen at flush, never at buffer time.** Marking on `add` means a restart mid-window
   consumes the item's one and only alert without ever sending it. The item is marked only after a
   successful send, which is the rule the existing code already follows.
2. **Drain must be atomic.** `drain` empties and returns in one step, so a second timer firing for
   the same user gets `[]` and sends nothing rather than re-sending the batch.

**AFK authorisation.** Vicky's call (2026-07-27): migration 0011 may be applied to the live Supabase
project, and the backend may be rsynced to `productivity_app_test` and restarted, both unattended.

**eas-cli is not installed on this machine.** Checked: not on `PATH`, absent from
`mobile/node_modules/.bin`, absent from `npm ls -g` under the only installed node (v22.16.0), and
not in Homebrew. `mobile/eas.json` does exist with a working `preview` profile
(`distribution: internal`, `android.buildType: apk`, pointing at `https://52-64-67-235.sslip.io`),
which is probably the memory of having set this up. The config is here; the binary is not. The APK
step waits for Vicky regardless, because `eas login` and the Firebase FCM key both need his
accounts.

### 4.11 Still open, non-blocking

**Notification icon asset.** The Android status-bar icon is a flat alpha silhouette. The two-card
mark can be exported white-on-transparent from the SVG already in the mock, but no image tooling is
confirmed present, so the export may need doing by hand.

**App display name.** `app.json` `name` is `"mobile"`, so real notifications would read "MOBILE" on
the lock screen. Needs a value before the preview APK reaches a phone. Not a blocker for Phase A.

### 4.12 Explicitly deferred

- **iOS APNs and any iOS delivery verification**, until the Apple Developer account exists. Code
  ships complete; only the credential is missing.
- **Push receipt polling.** Ticket-level `DeviceNotRegistered` handling ships now; the 15-minute
  receipt sweep is a Prefect job and belongs with the scheduled-jobs work.
- **Notification actions** (Reply, Snooze from the shade). Needs a background task and a signed
  action route.
- **Badges.** An unread count is a different promise from "this needs you", and a badge that never
  clears is its own kind of noise.
- **Quiet hours and per-source rules.** The four levels are the whole surface for now.
