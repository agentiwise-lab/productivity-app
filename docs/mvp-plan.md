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

### 3.7 Lifecycle

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

### 4.4 Guardrails

- Validate the response against the schema; on a malformed reply, retry once, then fall back to the rule-assigned tier rather than dropping the item.
- If the model returns `urgent` for more than 40% of a batch, log it. A model that marks everything urgent has defeated the product.
- The LLM never sends anything. It only classifies and summarises.

---

## 5. Data model (Supabase)

Every table is keyed by `user_id` with RLS `user_id = auth.uid()`.

| Table | Key columns |
|---|---|
| `users` | id (uuid), email, timezone, expo_push_token, working_hours_start, working_hours_end |
| `connections` | id, user_id, provider, composio_connected_account_id, composio_user_id, status |
| `feed_items` | id, user_id, source, source_ref, tier, type_tag, title, summary, reason, url, actors (jsonb), deadline, age_minutes, priority_score, status, raw (jsonb), created_at · **UNIQUE (user_id, source_ref)** |
| `user_preferences` | user_id, notify_level (`urgent`/`urgent_today`/`off`), muted_repos, muted_channels, vip_actors |
| `actions` | id, user_id, feed_item_id, type, payload, result, performed_at |
| `llm_cache` | source_ref, tier, summary, reason, model, created_at |

`llm_cache` is keyed on `source_ref` so a re-ingested item is never re-classified.

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
