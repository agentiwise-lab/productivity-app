# MVP Plan v3: implementation-ready

**Date:** 2026-07-23
**Status:** decisions closed. This is the document to implement from.
**Companions:** [architecture.md](architecture.md) (why the backend exists, trigger behaviour, verified tests) · [capabilities.md](capabilities.md) (what each platform can do) · [design-system.md](design-system.md) · mockups: [home](mockups/home.html), [app](mockups/app.html), [your day](mockups/yourday.html)

---

## 1. Decisions closed

| Area | Decision |
|---|---|
| Colour | **Sand & Slate** (`--c-ac:#2F4858`, urgency `#B25B33`) |
| Home layout | Time ruler → category counts (as filters) → swipeable card feed → grouped list. Ruler collapses to a sticky line on scroll. |
| Categories | **Urgent / Today / Can wait**, plus **Noise** which never reaches Home |
| Tabs | Home · Sources · Later · You (compact, icon-led) |
| Mobile | React Native + Expo |
| Backend | Python + FastAPI, webhook receiver plus API. **No scheduler.** |
| Database | Supabase (Postgres + Auth + RLS) |
| Integrations | Composio managed auth |
| LLM | **OpenRouter**, `google/gemini-2.5-flash` (verified working) |
| Notifications | Urgent pushes. Nothing else does. One setting, three options. |
| Demo | localhost + ngrok, Expo Go on a real phone. Deploy to EC2 later. |

---

## 2. Architecture in one paragraph

The Expo app talks to a FastAPI backend over HTTPS. The backend holds all secrets, receives Composio webhooks on one endpoint, classifies and ranks items, stores them in Supabase, and sends push notifications through Expo. **Composio runs all polling on its own infrastructure**, so we run no scheduler (proven: trigger instances carry `last_synced_at`, and a real Slack DM was delivered to a localhost listener). Full reasoning and test evidence in [architecture.md](architecture.md).

---

## 3. Category mapping

**Principle:** a rule assigns the tier whenever the source states both the type *and* an unambiguous urgency. The LLM is used only where urgency lives in human language. **The LLM may promote or demote**, it does not classify from scratch when a rule already knows.

Tier definitions:
- **Urgent**: a specific person is actively waiting on this user now, or a hard deadline has passed or is within hours.
- **Today**: needs handling before end of day, nobody is stopped right now.
- **Can wait**: genuinely needs the user eventually, no time pressure.
- **Noise**: no action required. Never reaches Home; lives in Later.

### 3.1 GitHub

| Signal (notification `reason` or trigger) | Tier | Method |
|---|---|---|
| `review_requested` | **Urgent** | Rule. Someone explicitly asked for your review. |
| `approval_requested` | **Urgent** | Rule. A gate is waiting on you. |
| `ci_activity`, conclusion = failure, on **your** PR | **Urgent** | Rule. Blocks your own work. |
| `ci_activity`, conclusion = success | Noise | Rule. |
| `security_alert` | **Urgent** | Rule. |
| `assign` (issue or PR assigned to you) | **LLM decides** | Rule sets Today as the floor; LLM reads **title + body + labels + milestone** and promotes to Urgent or demotes to Can wait. |
| `mention` / `team_mention` | **LLM decides** | Is it a question aimed at you, or were you named in passing? |
| `comment` on your PR or issue | **LLM decides** | Does it ask something, or is it "lgtm"? |
| `invitation` (repo invite) | Today | Rule. A decision, but nobody is blocked. |
| `state_change` (merged, closed) | Noise | Rule. |
| `subscribed` (thread you follow updated) | Noise | Rule. |

**On issues specifically** (the correction that drove this section): an assigned issue is **never** auto-filed as Can wait. Its urgency comes from what the raiser expressed. Signals the LLM reads, in priority order:
1. **Labels**: `P0`, `p0`, `blocker`, `critical`, `urgent`, `sev1`, `production` → strong promote to Urgent.
2. **Milestone or due date**: past due → Urgent. Due today → Today.
3. **Body language**: "production is down", "blocking the release", "customers affected" → Urgent. "nice to have", "someday", "low priority" → Can wait.
4. **Absence of all three** → Today, not Can wait. Defaulting an assigned issue to Can wait buries real work.

### 3.2 Slack

| Signal | Tier | Method |
|---|---|---|
| Direct message | **LLM decides** | Always. A Slack message has no type, only text. |
| Channel message that **@mentions you** | **LLM decides** | Always. |
| Reply in a thread you participated in | **LLM decides** | Always. |
| Channel message with no mention of you | Noise | Rule. Filtered before the LLM, so we do not pay to classify chatter. |
| Reaction added or removed | Noise | Rule. |
| Message from a bot or app | Noise | Rule, **unless** it reports a failure in the user's own work. |

**The judgement the LLM must make** (this is the core value of the product):
- *"can you unblock the staging deploy?"* → **Urgent**. Direct ask, no deadline, someone stopped.
- *"can you look at this when you get a chance, need it by tomorrow EOD"* → **Today**. It asks, but it states its own deadline.
- *"shipped the fix, thanks all"* → **Noise**. No ask.

### 3.3 Google Calendar

| Signal | Tier | Method |
|---|---|---|
| Event starting within 15 minutes | **Urgent** | Rule. |
| Invite received, awaiting your RSVP | Today | Rule. |
| Event time changed | Today | Rule. |
| Event cancelled | Noise (Worth knowing) | Rule. Surfaces in Later as "30m back". |
| Attendee RSVP changed | Noise | Rule. |

Calendar also feeds **Your day** (meetings left, free time), which is separate from the tiers.

### 3.4 Google Drive and Docs

| Signal | Tier | Method |
|---|---|---|
| Comment that **@mentions you** | **LLM decides** | Is it a question or an acknowledgement? |
| Comment on your file, no mention | **LLM decides** | Same, lower prior. |
| File shared with you | Today | Rule. LLM may demote to Can wait if the doc is clearly FYI. |
| File edited | Noise | Rule. |

### 3.5 Linear

| Signal | Tier | Method |
|---|---|---|
| Assigned, **priority = Urgent (1)** | **Urgent** | Rule. Linear has a native priority field, so no LLM needed. |
| Assigned, due date **past** | **Urgent** | Rule. |
| Assigned, due **today** | Today | Rule. |
| Assigned, priority High (2), no due date | Today | Rule. |
| Assigned, no priority, no due date | **LLM decides** | Reads title + description. |
| Comment mentioning you | **LLM decides** | |
| Status changed by someone else | Noise | Rule. |

### 3.6 Gmail (last phase)

All inbound mail goes to the **LLM**, because an email has no type. Promotions and list mail are filtered to Noise by Gmail's own category labels **before** the LLM, so we do not pay to classify newsletters.

### 3.7 Precedence when several rules match

One item can match more than one rule. A pull request can have your review requested *and* a failing check. Apply in this order and stop at the first match:

1. Security alert
2. CI failure on your own PR
3. `approval_requested`
4. `review_requested`
5. Direct mention or direct message
6. Assignment
7. Comment
8. Everything else

The **type tag** shown on the card comes from the winning rule, so an item is never labelled two things.

### 3.8 Tier is computed at read time, not frozen at ingest

**This is a correctness requirement, not an optimisation.** If the tier were stored once at ingest, an item due in three hours would still read "Today" after its deadline passed, and the model would rot silently.

Split it:

- **Stored at ingest**: the LLM's judgement (`llm_tier`), its `summary` and `reason`, the rule-derived tier (`rule_tier`), the deadline, and who is waiting. These do not change.
- **Computed on every read**: the final tier and the ranking, from the stored judgement plus *current* time.

Read-time promotion rules:
- Deadline now in the past → **Urgent**, whatever it was before.
- Deadline within 3 hours → at least **Today**.
- Calendar event starting within 15 minutes → **Urgent**.
- An Urgent item untouched for over 24 hours is **demoted to Today**, because if nobody chased it, it was not urgent. This stops the Urgent tier silting up.

### 3.9 Ranking inside a tier

`priority_score` was previously named but never defined. It is computed at read time:

```
score = tier_weight              # urgent 1000, today 100, can_wait 10
      + blocking_bonus           # +300 if a named person is explicitly waiting
      + deadline_pressure        # +200 overdue, +120 <3h, +60 <24h, else 0
      + vip_bonus                # +80 if sender is in user_preferences.vip_actors
      + age_pressure             # +min(60, minutes_waiting / 10)
      - snooze_penalty           # -1000 while snoozed_until is in the future
```

Ties break on `age_minutes` descending, so the thing that has waited longest wins. The card feed and the list use the same score, so their order never disagrees.

### 3.10 Identity facts we must resolve before classifying

Several rules depend on knowing who the user *is* on each platform. Resolve once at connection time and cache on `connections`:

- **GitHub login** (`GITHUB_GET_THE_AUTHENTICATED_USER`). Needed to answer "is this *my* PR" for the CI-failure rule.
- **Slack user id** (`SLACK_TEST_AUTH`). Needed to detect `<@U…>` mentions in message text, since Slack has no mention trigger.
- **Slack thread participation**: we only know a thread is "yours" if we have seen you post in it. Store `thread_ts` values the user has replied to, from `SLACK_SEND_MESSAGE` responses onward. **Accept the limitation:** threads you joined before installing the app are invisible until someone mentions you.

### 3.11 Lifecycle

- An item is visible while **unread and unhandled**.
- Replying, reacting, approving, or reading it at the source **removes it immediately**.
- Read state syncs both ways (`SLACK_SET_READ_CURSOR_IN_A_CONVERSATION`, GitHub mark-read).
- Items not acted on stay in **Later for 30 days**, then are deleted.

---

## 4. LLM design

### 4.1 What reaches the model

Only items whose row above says **LLM decides**. Everything else is free. Concretely, per refresh we expect a handful of items, not hundreds, because Noise is filtered by rules first.

### 4.2 Batching

- **One request per refresh**, carrying up to **20 items**. Never one request per item.
- If more than 20 new items, chunk into batches of 20 and issue them concurrently.
- Each item contributes roughly 150 to 250 tokens of context, so a 20-item batch is about 4,000 input tokens and 1,000 output tokens.
- **Cache by item id forever.** An item is classified once. Re-opening the app never re-classifies.
- Confirm current per-token pricing on OpenRouter at implementation time; the durable figure is the token count above, not the price.

### 4.3 The prompt

System prompt:

```
You triage work notifications for a busy professional. For each item, assign a
tier and write one short line explaining what it is.

TIERS
- urgent:   a specific person is actively waiting on this user right now, OR a
            hard deadline has passed or falls within a few hours.
- today:    needs handling before end of day, but nobody is stopped right now.
            Includes anything with a stated deadline of today or tomorrow.
- can_wait: genuinely needs the user eventually, no time pressure stated.
- noise:    no action required of this user. Status updates, automated messages,
            conversation they were not addressed in.

RULES
- Be conservative. If torn between urgent and today, choose today.
- A stated future deadline ("by tomorrow EOD") means today, never urgent.
- A direct question addressed to this user with no deadline means urgent.
- Labels such as P0, blocker, critical, sev1 or production mean urgent.
- An item assigned to this user is never can_wait unless it explicitly signals
  low priority. When there is no signal at all, choose today.
- Bot and automated messages are noise unless they report a failure in this
  user's own work.
- Recency alone never makes something urgent.

OUTPUT
A JSON array with one object per input id, no prose:
{"id": "...", "tier": "urgent|today|can_wait|noise",
 "summary": "<=90 chars: what it is and why it matters",
 "reason":  "<=60 chars: why this tier"}
```

User message: a JSON array of items, each carrying `id`, `source`, `type`, `sender`, `title`, `text` (truncated to ~400 chars), `labels`, `deadline`, `age_minutes`, and `is_direct` (was the user addressed directly).

The `summary` field is what the UI shows as the one-liner under each row. The `reason` is what the detail sheet shows under "Why this is urgent".

### 4.4 Guardrails and failure modes

**The feed must never block on the model.** Classification is asynchronous:

1. On ingest, assign the **rule tier immediately** and store the item. It is visible at once.
2. Queue the LLM batch.
3. When it returns, update `llm_tier`, `summary` and `reason`. The feed re-ranks on next read.

So a slow or dead model degrades the product to rules-only, which still works, rather than showing an empty screen.

| Failure | Behaviour |
|---|---|
| Malformed JSON | Retry once, then keep the rule tier |
| Request times out (>20s) | Abandon that batch, keep rule tiers, retry on next refresh |
| OpenRouter down or rate-limited | Log, keep rule tiers, exponential backoff |
| Model marks >40% of a batch urgent | Log an alarm. A model that marks everything urgent has defeated the product |
| Item text is not English | Pass through unchanged; the model handles it, no pre-translation |
| Daily budget exceeded | Stop classifying, rules only, surface nothing to the user |

**Cost ceiling.** Cap classifications per user per day (start at 200 items). Beyond it, rules-only. This bounds a runaway loop or an abusive account.

**Content truncation.** 400 characters can cut the actual ask. Take the **first 250 and last 150** characters rather than a plain head-truncate, because requests often sit at the end of a message.

**Privacy, and it must be disclosed.** Classifying Slack messages, doc comments and email means **sending that text to OpenRouter, a third party**. This is unavoidable given the design and is the core privacy fact of the product. Consequences to accept and state plainly in onboarding and any privacy policy:
- Message content leaves our infrastructure for classification.
- Do not log raw content in our own systems beyond the retention window.
- Offer a per-integration "do not send content to AI" switch that falls back to rules-only for that source.

The LLM never sends, replies or acts. It only classifies and summarises.

---

## 5. Data model (Supabase)

Every table is keyed by `user_id` with RLS `user_id = auth.uid()`.

| Table | Key columns |
|---|---|
| `users` | id (uuid), email, timezone, expo_push_token, working_hours_start, working_hours_end |
| `connections` | id, user_id, provider, composio_connected_account_id, composio_user_id, status |
| `feed_items` | id, user_id, source, source_ref, **rule_tier**, **llm_tier**, **tier_source** (`rule`/`llm`), type_tag, title, summary, reason, url, actors (jsonb), **sender_name**, **sender_handle**, deadline, **is_blocking**, **occurred_at**, status, **snoozed_until**, **handled_at**, **content_hash**, raw (jsonb), created_at · **UNIQUE (user_id, source_ref)** |
| `user_preferences` | user_id, notify_level (`urgent`/`urgent_today`/`off`), muted_repos, muted_channels, vip_actors, **ai_content_optout** (jsonb, per source) |
| `actions` | id, user_id, feed_item_id, type, payload, result, performed_at |
| `llm_cache` | **content_hash** (PK), tier, summary, reason, model, created_at |

Notes on the changes made during review:

- **`tier` is gone as a stored column.** `rule_tier` and `llm_tier` are stored; the effective tier and `priority_score` are computed at read time (section 3.8, 3.9). Storing a single frozen tier was the bug.
- **`llm_cache` is keyed on `content_hash`, not `source_ref`.** A Slack thread gains replies, so the same `source_ref` can have different content. Keying on the reference alone would serve a stale classification forever.
- **`snoozed_until`** is required because snooze is in the UI and had nowhere to live.
- **`handled_at`** is separate from `status` so we can measure how long things wait, which is what `age_pressure` needs.
- **`sender_name` / `sender_handle`** are stored because every card shows who is waiting; deriving it from `raw` on every read would be wasteful.
- **`occurred_at`** is the source's timestamp, distinct from `created_at` (when we ingested). Ranking must use the former.

**Your day is not stored.** Meetings and free time are read live from Calendar on each app open. Caching a schedule invites showing a stale one.

---

## 6. UI specification

Follow [design-system.md](design-system.md) tokens and the mockups.

**Home** ([mockups/home.html](mockups/home.html)): compact icon-led header → time ruler (`Your day`) → three category counts acting as filters → horizontal swipeable card feed (cards ~1/3 screen height, next card peeking) → `All items` grouped list. On scroll the ruler collapses to a sticky one-line strip.

**Your day** numbers, defined precisely and not interchangeable:
- **meetings left** = calendar events remaining today
- **free** = unscheduled minutes between now and working-hours end
- **due today** = the user's own tasks with a deadline of today (Linear, GitHub milestones)

**Sources**: list of connected integrations with per-source counts; tap to drill into that integration's dashboard.
**Later**: everything unactioned, all sources, 30-day window.
**You**: notification level (one three-way choice), connected accounts, sign out.

Header and footer are deliberately short and icon-led.

### 6.1 Card anatomy: nothing on this list is optional

Every feed card and every list row carries all of the following. This is the product's substance, not decoration, so none of it may be dropped for space.

| Element | Content | Source |
|---|---|---|
| **Source icon** | Real brand mark, tinted roundel (GitHub, Slack, Google Docs, Linear, Calendar, Gmail) | `feed_items.source` |
| **Type tag** | `REPLY` · `REVIEW` · `APPROVE` · `ASSIGNED` · `COMMENT` · `RSVP` · `FYI`, mono uppercase chip | `type_tag` from the winning rule (3.7) |
| **Urgency styling** | Ochre border and tint when Urgent, neutral otherwise | computed tier |
| **Time ago** | `18m`, `4h`, `due today`, right-aligned, mono | `occurred_at` |
| **Who** | Sender name in the title where it reads naturally ("**Priya** needs…") | `sender_name` |
| **Title** | The thing itself, clamped to 2 lines | `title` |
| **Subtext** | The AI one-liner, why it matters, 1 line | `summary` |
| **Context chip** | `#eng-releases`, `glued_landing`, `DM`, `Linear` | derived from `raw` |
| **Actions** | Two primary actions per card, source-appropriate | see 6.2 |

The detail sheet adds: the **quoted original message** with author and timestamp, the **"why this is urgent"** block (`reason`), counts (`3 in thread`, `2 waiting`), an inline reply field, and an **Open in [source]** deep link.

### 6.2 Actions per source

| Source | Primary | Secondary | Always available |
|---|---|---|---|
| GitHub PR review | Approve | Comment | Request changes, Snooze, Open |
| GitHub issue | Comment | Assign to me | Snooze, Open |
| Slack | Reply | React | Mark read, Snooze, Open |
| Google Docs | Reply to comment | Open | Snooze |
| Calendar | Accept | Decline | Open |
| Linear | Comment | Open | Snooze |

Merge is deliberately absent. Reaction is deferred past the MVP.

### 6.3 Icons: real brand marks, not placeholders

The mockups use two-letter placeholders (`GH`, `SL`). Ship real marks.

- **Source**: each vendor's official brand assets (GitHub Octicons/logos, Slack brand kit, Google brand permissions, Linear brand page). Download the SVGs and vendor them into `mobile/src/assets/brands/`. Do **not** hotlink, and do not use a third-party icon pack for brand marks.
- **Rendering**: `react-native-svg`, with each mark as a component so it can be tinted per theme. Keep the vendor's own colour for recognisability inside its tinted roundel; do not recolour brand marks arbitrarily.
- **Respect the guidelines.** Each vendor restricts distortion, recolouring and implying endorsement. Read each brand page once, record what it allows in `design-system.md`, and keep the marks at their permitted proportions.
- **UI icons** (tab bar, chevrons, actions, snooze, back): a single consistent open-licence set, **Lucide** (ISC), also via `react-native-svg`. One set only, no mixing.
- **Fallback**: if a source has no vendored mark yet, render the tinted roundel with the two-letter monogram, which is what the mockups already show. That keeps the UI correct while marks are being added.

### 6.4 States that must exist

The mockups show the happy path. These do not exist yet and each needs a screen.

| State | Behaviour |
|---|---|
| **First run, nothing connected** | Home replaced by a connect prompt listing available sources. No empty feed with zero counts, which reads as broken. |
| **Connected, nothing needs you** | The cleared state already designed: "You're clear for today", plus what was held back. |
| **Still loading first fetch** | Skeleton rows, never a spinner on a blank screen. |
| **Backend unreachable** | Show the last cached feed with a "last updated HH:MM" line. Never an empty screen just because the network is down. |
| **A connection expired** | Composio emits `CONNECTION_EXPIRED`. Mark that connection broken, show a banner on Home and a red dot on the source in Sources, and offer re-connect. **Do not silently show a stale or empty feed for that source.** |
| **A source errors but others work** | Degrade per source. One broken integration never blanks the feed. |
| **Offline** | Read from the local cache; queue actions and replay them when back online, or fail them loudly rather than silently dropping. |

### 6.5 Authentication

Supabase Auth, email magic link, is enough for the MVP. The app holds the Supabase session, sends the JWT as a bearer token, and the backend derives `user_id` from the verified token. **Never trust a `user_id` sent in the request body.** The Supabase user uuid is also what we pass to Composio as its `user_id`, so the identity chain stays single (architecture.md 9b).

---

## 7. Phases

**Phase 1: GitHub end to end, on localhost**
- Supabase migrations, RLS, `SupabaseFeedRepository` behind the existing contract.
- Composio SDK wired with the working API key; connections keyed by our Supabase uuid.
- `POST /webhooks/composio` receiving and verifying signed events.
- Fetch-on-open via global `GITHUB_LIST_NOTIFICATIONS`.
- Rule classifier for all deterministic GitHub rows in 3.1.
- LLM classifier via OpenRouter for the `LLM decides` rows, batched and cached.
- `GET /feed` returning tiered, ranked items.
- **Done when:** your real GitHub notifications appear tiered and summarised, from a real database.

**Phase 2: the app**
- Expo app, Home exactly as the mockup, against the local backend over ngrok.
- Sources, Later, You.
- **Done when:** it runs on your phone through Expo Go and shows your real feed.

**Phase 3: acting and pushing**
- Approve, comment, reply, mark read, snooze, all writing back through Composio.
- Expo push for Urgent only.
- Read-state sync both directions.

**Phase 4: Slack**, using the two account-wide push triggers already proven working.
**Phase 5: Calendar and Drive** (Your day becomes real; doc comments arrive).
**Phase 6: Linear, then Gmail last.**

---

## 8. Local development and the demo

No deployment needed for the demo.

```bash
# backend
cd /Users/vickypandey/Desktop/agentiwise/productivity-app
uv run uvicorn backend.main:app --reload --port 8000

# public URL for Composio webhooks
ngrok http 8000        # then register the https URL as the webhook subscription

# app
cd mobile && npx expo start
```

- Install **Expo Go** on your phone, scan the QR code. **No Xcode, no Android Studio needed.**
- The app's API base URL must be your Mac's LAN IP, not `localhost`.
- ngrok URLs change on restart, so re-register the webhook subscription each session.
- Later: EC2 for a stable URL. Not Vercel, whose serverless timeout would cut batched LLM calls.

---

## 9. Testing

- Backend is test-first (Red-Green-Refactor); every new or modified function gets a test in the root `tests/`.
- Tests run through contracts with `Fake*` implementations, never against live GitHub, Slack, Supabase or OpenRouter.
- The classifier needs a **fixture suite**: real payloads for each row of section 3, asserting the expected tier. This is the highest-value test set in the project, because a wrong tier is the product failing.
- Current state: 38 passing.

---

## 10. Open items

1. **App name.** The header currently reads "Today".
2. **Rotate the Supabase service role key.** It was pasted into a chat transcript.
3. Confirm OpenRouter per-token pricing at implementation time.
4. Calendar RSVP is a patch on the attendee response, with no dedicated tool. Verify before Phase 5.
5. GitHub urgent items surface on app open rather than as instant push, unless a repo is opted into real-time watching at 720 calls/month. Accepted for now.
