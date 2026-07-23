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

Recommendation: start on a small container host, move to EC2 when you want the control. Either way it is one service and one URL.

---

## 6. Categories: one model, not two

The previous plan had two overlapping taxonomies (action types *and* urgency groups), which is exactly why it was confusing. Collapsed into one.

### The six categories (what is being asked of you)

| # | Category | What it means | Where it comes from |
|---|---|---|---|
| 1 | **Needs your decision** | A call only you can make | GitHub: CI failed on your PR, changes requested, repo invitation · Calendar: invite awaiting RSVP · Drive: access request · Linear: issue assigned, untriaged |
| 2 | **Needs your review** | Someone's work waits on your eyes | GitHub: review requested, ready for review · Drive: doc shared for review |
| 3 | **Needs your reply** | Someone waits on your words | Slack: DM, mention, thread · Drive: doc comment or @mention · Gmail: reply-needed · GitHub: comment on your PR |
| 4 | **Blocked on others** | Yours, ball is not in your court | Your PR awaiting review, you asked with no answer |
| 5 | **Worth knowing** | Context, digest only | Merged, closed, CI passed, release, event cancelled |
| 6 | **Others** | Everything else, low signal | Promotions, channel chatter, automated noise |

**Ordering is a score, not another taxonomy.** Inside Home, items are ranked by an urgency score (who is blocked, how long it has waited, deadline proximity, who asked). There is no second set of buckets. That removes the "needs you now vs later today" confusion entirely.

### On "does GitHub really tell us this?"

Yes, verified live. GitHub's notification API returns a `reason` field per item, with values including `review_requested`, `assign`, `mention`, `team_mention`, `approval_requested`, `ci_activity`, `invitation`, `state_change`. So "CI failed on your PR" and "repo invitation" are real, typed signals, not guesses.

**But "await you" was a bad label** and you were right to call it out. We will say the precise thing: *"2 PRs need your review"*, *"3 issues assigned to you"*, *"1 repo invitation"*. Never a vague count.

---

## 7. Notification levels, explained plainly

Three levels, per category. Not custom rules.

- **Push**: your phone buzzes immediately.
- **Brief**: the item is held and delivered as **one** summary notification twice a day (say 08:30 and 16:30). Twenty low-priority events become one notification instead of twenty buzzes. This is the whole anti-noise mechanism.
- **Off**: never notified. Still visible in the app when you look.

**No custom rule builder.** The settings screen is simply the six categories with a three-way choice each. Sensible defaults:

| Category | Default |
|---|---|
| Needs your decision | Push |
| Needs your review | Push |
| Needs your reply | Push |
| Blocked on others | Brief |
| Worth knowing | Brief |
| Others | Off |

The data model still stores rules generically, so per-channel or per-repo control can be added later without a migration. The user just never sees a rule builder.

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

## 10. Home screen composition

Home answers two questions in order: **how is my day shaped**, then **what needs me**.

1. **Day plan strip.** From Calendar: meetings done, next meeting, free time left today. Plus tasks due today from Linear. This is the "what is remaining on me today" view.
2. **Attention summary.** Counts per category, precise wording.
3. **The feed.** Ranked by urgency score, each row carrying its source icon, category tag, one-line LLM summary, and who is waiting.
4. **Cleared state** when the list is empty.

Categories 5 and 6 never appear on Home. They live in Later.
