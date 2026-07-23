# Architecture: do we need a backend, and what runs where

**Date:** 2026-07-23
**Status:** answers the open questions. Read this before the plan.

---

## 1. The app and the backend are two separate programs

This is the core confusion, so plainly:

- **The mobile app** (React Native + Expo) is what gets installed on a phone. It is the *client*. It draws screens and calls an API.
- **The backend** (Python + FastAPI) is a *separate program running on a computer in the cloud*. It is never inside the `.apk` or `.ipa`.

They talk over HTTPS. **No Python ever ships inside the app file.** When you hand someone the app, they get the React Native client only.

```
[ Phone: React Native app ]  --HTTPS-->  [ Cloud: FastAPI backend ]  <-->  [ Supabase ]
                                                  ^
                                                  |  webhooks
                                         [ Composio ]  <-->  GitHub / Slack / Calendar / Drive
```

---

## 2. Can we skip the backend entirely?

**No.** Two reasons, and the second is absolute.

**Reason 1: secrets.** Calling Composio requires the Composio API key. Anything shipped inside a mobile app can be extracted from the binary by anyone who installs it. If the key is in the app, one person can pull it out and reach **every user's** connected accounts. API keys must live on a server. This alone forces a backend.

**Reason 2: notifications while the app is closed.** This is the one that cannot be engineered around. **An app that is not running cannot check anything.** iOS and Android suspend apps aggressively. For the phone to buzz when a PR needs your review, some always-on computer has to notice the event and tell Apple's (APNs) or Google's (FCM) push service to wake the device. That always-on computer *is* the backend. There is no version of "the app does it itself" that delivers a notification while the app is closed.

So: a backend is required. But it can be **small**, and it does not need a scheduler.

---

## 3. Prefect is not needed. Here is why.

You were right to push back, and the capability research proves it.

**Composio does the polling for us.** When Composio documents a trigger as "polling" (Gmail, Calendar, Linear private teams), that means **Composio polls Google or Linear on their own infrastructure**, then pushes the result to our webhook. From our side it is simply an inbound HTTP request. We never run a schedule, never poll a provider, never need a scheduler.

So the backend is: **a webhook receiver plus an API**. Nothing periodic runs on our side.

| Old plan (v2) | Now |
|---|---|
| Prefect flow polling GitHub every N minutes | Composio triggers push events to `POST /webhooks/composio` |
| A scheduler process to run and host | No scheduler at all |

And when the user opens the app, the app calls `GET /feed`, which can also trigger a fresh pull right then. That matches your mental model: **things happen when someone opens the app**, plus webhooks arriving in the background so notifications still work when it is closed.

> Note on the "always use Prefect" rule: that rule governs *scheduled application jobs*. We now have none, so it does not apply here.

---

## 4. What the backend actually does

Five jobs, all small:

1. **Holds the secrets** (Composio key, OpenRouter key, Supabase service key).
2. **Receives Composio webhooks** for every integration, on one endpoint.
3. **Classifies, ranks and stores** items into Supabase.
4. **Sends push notifications** through Expo's push service to APNs/FCM.
5. **Serves the app**: `GET /feed`, `GET /sources/{provider}`, `POST /items/{id}/actions`.

That is a single small service. No queue, no scheduler, no worker fleet.

---

## 5. Where to deploy it

The one hard requirement is **a stable public HTTPS URL that is always reachable**, because Composio delivers webhooks to it.

| Option | Verdict |
|---|---|
| **Small always-on container** (Railway, Render, Fly) | **Recommended to start.** About $5/month, zero ops, one stable URL, no cold starts, no timeout ceiling. |
| **AWS EC2** (t4g.small) | Also fine, and you have done it before. More control, slightly more setup. Good target once it is real. |
| **Vercel** | Works for webhooks, but serverless timeouts (10s on hobby) will bite when we batch LLM summarization. Not recommended for this shape. |

### Local first, deploy later (validated)

For the demo we do **not** deploy at all. The backend runs on your Mac and **ngrok** gives it a public HTTPS URL so Composio can reach it. This was tested end to end on 2026-07-23:

- Local listener on `:8787`, ngrok tunnel up, public URL reachable from the internet and the request logged locally.
- Webhook subscription registered with Composio against that ngrok URL.
- Trigger created; Composio's own poll loop confirmed running (see section 3).

So the order is: **everything on localhost with ngrok → demo on your phone via Expo → then EC2** when it needs to be always-on. Nothing about the local setup has to change when we deploy; only the webhook URL does.

Recommendation for eventual hosting: a small always-on container, or EC2 since you are comfortable there. Either way it is one service and one URL.

---

## 6. Categories: urgency tiers, not semantic types

Earlier drafts had two overlapping taxonomies and a "Blocked on others" bucket. **"Blocked on others" is dropped: we cannot reliably know it.** Inferring that someone else is the holdup means guessing at intent, and a category built on a guess will be wrong often enough to destroy trust. What we *can* honestly say is "your PR has been awaiting review for 4 hours", and that is a detail on an item, not a category.

The organising principle is **urgency**, because that is how the question is actually asked: *what do I have to deal with right now.*

### Home has two zones

**Zone 1: Your day.** Time-anchored, always on top. Next meeting, meetings remaining, and what is due today. From Calendar plus Linear. This is the "what is happening and what is pending for the day" view.

**Zone 2: Needs you.** Three tiers, nothing more.

| Tier | Meaning | Examples |
|---|---|---|
| **Urgent** | Someone is actively waiting on you right now | GitHub: review requested, assigned to you, @mentioned, changes requested on your PR, CI failed on your PR · Slack: a message the model judges needs an answer now · Docs: someone @mentioned you in a comment |
| **Today** | Real, should be handled today, nobody is blocked this minute | Slack message that asks something but states a later deadline · PR awaiting your review that is not blocking a release · issue due today |
| **Can wait** | Needs you eventually, no time pressure | Assigned with no deadline, non-blocking mention |

**Noise** is the fourth bucket and it **never appears on Home**. It lives in its own tab: CI passed, merged, closed, releases, channel chatter, promotions, automated mail.

### Type is a tag, not a section

Each row carries a small tag (**Reply · Review · Assigned · Comment**) and a source icon (Slack, GitHub, Docs). You can see what kind of action it is without type becoming a second layer of grouping. One hierarchy only: urgency.

### Lifecycle: unread in, handled out

- Unread and unhandled: visible.
- Replied, reacted to, or read at the source: **disappears immediately.**
- Read state syncs both directions (`SLACK_SET_READ_CURSOR_IN_A_CONVERSATION`, GitHub mark-read), so the app and the source never disagree.

This is the single biggest simplification. The app only ever shows unhandled work, so the list shrinks as you work and reaches zero.

### On "does GitHub really tell us this?"

Yes, verified live. GitHub's notification API returns a `reason` field per item, with values including `review_requested`, `assign`, `mention`, `team_mention`, `approval_requested`, `ci_activity`, `invitation`, `state_change`. So "CI failed on your PR" and "repo invitation" are real, typed signals, not guesses.

**But "await you" was a bad label** and you were right to call it out. We will say the precise thing: *"2 PRs need your review"*, *"3 issues assigned to you"*, *"1 repo invitation"*. Never a vague count.

---

## 7. Notifications: derived from the tier, not a second system

There is no separate notification taxonomy. **The tier decides the notification.**

- **Urgent** sends a push. Your phone buzzes.
- **Today** and **Can wait** do not push. They are simply there when you open the app.
- **Noise** never notifies at all.

That is the whole model. One setting exists, with three options:

| Setting | Behaviour |
|---|---|
| **Urgent only** (default) | Push only when someone is actively waiting |
| **Urgent and Today** | For people who want more |
| **Nothing** | Silent, check when you like |

No per-category matrix, no rule builder. The data model stores rules generically so per-repo or per-channel control can be added later without a migration, but the user never sees that.

---

## 8. Where the LLM is used (OpenRouter)

**Provider: OpenRouter**, starting with `google/gemini-2.5-flash`. Verified working.

Your question was: are we clustering from the app-provided category, or from the LLM? **Both, layered, and the split matters.**

**Deterministic (no LLM) wherever the platform tells us the type:**
- GitHub gives `reason` directly, so category is a lookup. Free, instant, always consistent.
- Calendar, Drive, Linear, Notion all carry a typed event.

**LLM required where there is no type at all:**
- **Slack is the clearest case.** A Slack message is just text. "can you unblock the deploy?" carries no type field. Only a language model can tell a genuine request apart from chatter. Same for Gmail and doc comments.

**LLM also does, from Phase 1:**
1. **A one-line summary per item.** "This PR swaps the icon set, 3 files, low risk." This is what stops you opening GitHub.
2. **Ranking within a category.** Which of five review requests actually matters most.

**Not doing** (your call, agreed): reply drafting, tab-complete, rule authoring, auto-send.

**Cost control**, because "an LLM call per listing" would be expensive:
- **Batch:** one call per refresh covering all new items, not one call per item.
- **Cache:** summarize an item once, store it, reuse forever. Items do not change.
- **Skip:** category 5 and 6 items never get summarized.

---

## 9. Navigation: what happens with more integrations

Bottom tabs stop working past about five, so integrations do **not** each get a tab.

| Tab | Contents |
|---|---|
| **Home** | Day plan plus the ranked, categorized feed across everything |
| **Sources** | A list of connected integrations (GitHub, Slack, Calendar, Drive, Linear, Gmail). Tap one to drill into its own dashboard. Scales to twenty. |
| **Later** | Categories 5 and 6, the low-signal pile, kept out of Home entirely |
| **You** | Connections, notification levels, account |

This is your "fourth tab for things that do not matter much", and it solves the scaling problem: adding an integration adds a row in Sources, not a tab.

---

## 9b. How the poll loop is enabled, and how multi-user works

### What "the poll loop" actually is

It is not something we run or host. It is a **trigger instance** stored inside Composio. We create one with a single API call, and Composio persists it and runs it on their infrastructure forever after.

```python
composio.triggers.create(
    slug="GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER",
    user_id="<our user id>",
    trigger_config={"owner": "dswh", "repo": "glued_landing", "interval": 2},
)
# -> ti_bPn-OyqzRkrm
```

`interval` is the poll frequency in minutes. That one call **is** enabling the poll loop. Verified live: the instance came back carrying `last_synced_at` and a list of `seen_ids`, which is Composio's own sync state.

**One trigger instance exists per (user, trigger type, config).** Ten users watching two event types means twenty trigger instances, all living in Composio.

### The identity chain

Composio's unit of identity is `user_id`, and **it is a string we choose**. That is the whole trick: we pass our own Supabase user UUID as the Composio `user_id`. Then no mapping table is needed, because the id in the webhook payload already *is* our user id.

```
Supabase user UUID  ==  Composio user_id  ==  user_id in every webhook payload
```

(The current test connection reads `pg-test-86b8d0d9…` only because that account was linked through the dashboard playground, which generates its own id. In the real onboarding flow we pass our UUID.)

### Onboarding: connecting a user

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant App as Mobile app
    participant BE as Our backend
    participant CO as Composio
    participant GH as GitHub

    U->>App: Sign up
    App->>BE: create account
    BE->>BE: Supabase user created (uuid)
    U->>App: Tap "Connect GitHub"
    App->>BE: POST /connections/github
    BE->>CO: link(user_id=uuid, auth_config_id)
    CO-->>BE: redirect_url
    BE-->>App: redirect_url
    App->>U: Open authorize page
    U->>GH: Approve access
    GH-->>CO: OAuth callback
    CO->>CO: Store connected account for uuid
    BE->>CO: triggers.create(slug, user_id=uuid, interval)
    CO-->>BE: trigger instance id
    Note over CO: Poll loop now runs inside Composio for this user
```

### Runtime: an event arrives, for the right user

```mermaid
sequenceDiagram
    autonumber
    participant GH as GitHub / Slack
    participant CO as Composio
    participant BE as Our backend
    participant DB as Supabase
    participant EX as Expo push
    participant App as User's phone

    loop every interval, inside Composio
        CO->>GH: poll for new events
        GH-->>CO: new notification
    end
    CO->>BE: POST /webhooks/composio (signed)<br/>payload carries user_id
    BE->>BE: verify signature
    BE->>BE: classify by rules, then LLM for Slack text
    BE->>DB: upsert feed_item (user_id, dedupe on source_ref)
    alt tier == Urgent
        BE->>EX: push to that user's device token
        EX->>App: notification
    else Today / Can wait / Noise
        BE-->>BE: no push, appears in app
    end
```

### How the app gets only its own data

```mermaid
sequenceDiagram
    autonumber
    participant App as Mobile app
    participant BE as Our backend
    participant DB as Supabase

    App->>BE: GET /feed  (Supabase JWT)
    BE->>BE: decode JWT -> user uuid
    BE->>DB: select feed_items where user_id = uuid
    Note over DB: Row Level Security also enforces<br/>user_id = auth.uid() at the database
    DB-->>BE: only that user's rows
    BE-->>App: ranked feed
```

Two independent guards: the backend filters by the id in the verified JWT, and Postgres RLS refuses cross-user reads even if the backend had a bug. One user can never see another's items.

### Components

```mermaid
flowchart LR
    subgraph Phone
        A[React Native app]
    end
    subgraph Cloud
        B[FastAPI backend<br/>webhook receiver + API]
        C[(Supabase<br/>Postgres + Auth + RLS)]
    end
    subgraph External
        D[Composio<br/>holds connections<br/>runs poll loops]
        E[OpenRouter<br/>gemini-2.5-flash]
        F[Expo push]
    end
    G[GitHub / Slack / Calendar / Drive]

    A -->|HTTPS, JWT| B
    B --> C
    D -->|webhook, signed| B
    B -->|tool calls| D
    D <-->|poll + act| G
    B -->|classify + summarise| E
    B -->|urgent only| F
    F --> A
```

Note that **we never talk to GitHub or Slack directly.** Composio holds every connection and runs every poll. Our backend only receives webhooks, classifies, stores, and serves.

### Scaling note

Trigger instances multiply as users times event types. At 100 users watching 4 event types that is 400 instances inside Composio, and each poll is a tool call against the quota. This is the number to model before opening the doors, and it is an argument for preferring genuinely push-based triggers (Slack) over polled ones (Gmail, Calendar) wherever both exist.

## 10. Home screen composition

Home answers two questions in that order: **how is my day shaped**, then **what needs me now**.

1. **Your day.** Next meeting, meetings remaining, free time left, and what is due today. Calendar plus Linear.
2. **Urgent.** Someone is waiting. Each row: source icon, type tag, one-line summary, who is waiting and for how long.
3. **Today.** Handle before end of day.
4. **Can wait.** Collapsed by default.
5. **Cleared state** when nothing is left.

Noise never appears here. It has its own tab.

### How urgency is actually decided

**GitHub is mostly deterministic.** The notification `reason` field already tells us the type (`review_requested`, `assign`, `mention`, `ci_activity`), so tier assignment is a rule. The model is used only to summarise and to order within a tier.

**Slack is where the model does the real work,** because a Slack message carries no type at all, only text. The judgement is exactly the one you described:

- *"can you unblock the staging deploy?"* → **Urgent.** A direct ask, nothing scheduled, someone is stopped.
- *"can you look at this when you get a chance, need it by tomorrow EOD"* → **Today**, not Urgent. It asks something, but it states its own deadline.
- *"shipped the fix, thanks all"* → **Noise.** No ask.

That distinction cannot be hard-coded, which is precisely why the model is in Phase 1 rather than deferred. Same judgement applies to Google Doc comments: an @mention that asks a question is Urgent, one that says "looks good" is Noise.
