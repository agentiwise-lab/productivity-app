# MVP Plan (v2): Unified AI Work Feed

**Date:** 2026-07-23
**Status:** For review. Once approved this is detailed enough to run AFK implementation against.
**Companions:** [product-brief.md](product-brief.md) · [product-research.md](product-research.md) · [design-system.md](design-system.md) · [mockups/screens.html](mockups/screens.html)

## 0. What changed since v1

- **Composio replaces per-provider OAuth apps.** No GitHub App, no Slack app, no Google Cloud project to register. One integration layer for all four tools.
- **Verified working already:** 38 tests green, and real GitHub notifications pulled through the pipeline with zero OAuth apps created.
- **Consequence:** the "create a GitHub App" step from v1 is deleted. Integration cost drops enough that Slack and Linear move earlier.
- **Added:** per-integration summary tabs (your ask), the notification/anxiety model, and the AI role split.

---

## 1. The product in one screen

- **Home** is everything combined: one ranked feed of what needs you across GitHub, Slack, Calendar, Drive, Linear and (later) Gmail, clustered by what is being asked of you rather than by which app it came from.
- **Home also knows your time.** Calendar supplies how much free time is actually left today, which turns the feed from a list into a plan: "seven things need you, and you have 90 free minutes before your 14:00".
- **Per-integration tabs** (GitHub, Slack, ...) each show a summary dashboard first (counts, repo-wise or channel-wise breakdown), then that tool's items.
- **You act in the app**: approve a PR, reply to a thread, comment, snooze. No app-hopping.
- **It stays quiet by default.** Only "someone is blocked on you" earns a push. Everything else batches into two briefs a day.

See the six screens: [mockups/screens.html](mockups/screens.html).

---

## 2. Decisions locked

| Layer | Choice | Why |
|---|---|---|
| Mobile | **React Native + Expo** (TypeScript) | One codebase for iOS **and** Android. Not two implementations. Expo wraps APNs/FCM push and gives over-the-air updates. |
| Backend | **Python + FastAPI** | AI pipeline plus data-heavy work. Matches the "Python for AI/automation backends" rule. |
| Scheduler | **Prefect** | Polling GitHub on a schedule is an external-data job. Managed cron is disallowed by rule; logic stays in the codebase. |
| Database + auth | **Supabase (Postgres)** | Postgres, auth and row-level security out of the box. Fastest path, and RLS gives per-user isolation for free. |
| Integrations | **Composio** (managed auth) | No OAuth apps to register. One webhook for all providers. |
| LLM | **Anthropic SDK (Claude)** | Used narrowly (section 7), not on the hot path. |

**Repo layout (Pattern A, each folder is a deployment boundary):**

```
productivity-app/
  backend/        FastAPI: API, services, contracts, integrations
  mobile/         React Native + Expo app
  prefect/        scheduled GitHub pollers
  supabase/       migrations
  docs/           this plan, research, design system, mockups
  tests/          backend tests at the contract boundary (repo root)
```

---

## 3. What I need from you (access checklist)

Nothing here is blocking review. These unblock implementation.

- [x] **Composio API key**: done, in `.env` as `COMPOSIO_API_KEY`, validated.
- [ ] **Composio: connect GitHub under this API key's project.** The key currently reports **0 connected accounts**; the CLI's GitHub link sits in a different project. Fix is either `composio link github` against this project or connecting from the Composio dashboard.
- [ ] **Supabase project.** Create one, then add to `.env`:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY` (mobile client)
  - `SUPABASE_SERVICE_ROLE_KEY` (backend only, never in the mobile app)
- [ ] **Anthropic API key** (Phase 4, not needed before): `ANTHROPIC_API_KEY`.
- [ ] **Expo account** (Phase 6, for device builds and push credentials).

Add each with the same safe pattern (never paste into chat):

```bash
cd /Users/vickypandey/Desktop/agentiwise/productivity-app && read -rs "?Paste value: " v && echo "SUPABASE_URL=$v" >> .env && unset v
```

`.env` is already gitignored.

---

## 4. Architecture and data flow

- **Ingest (two paths, one shape):**
  - **Poll:** Prefect calls `GITHUB_LIST_NOTIFICATIONS` through Composio on a schedule. GitHub's notification inbox is poll-only, there is no webhook for it.
  - **Push:** Composio triggers deliver provider events (Slack messages, Linear updates) to **one** signed webhook, `POST /webhooks/composio`.
- **Normalize:** every inbound signal becomes a `RawEvent`, so nothing downstream knows which provider or channel it came from.
- **Enrich:** notifications are thin (a `reason` plus a URL, not content), so we fetch the PR/issue/message to learn what it is and how urgent.
- **Classify:** `RawEvent` to an action type (rules first, LLM only for the residue).
- **Score:** composite priority.
- **Store:** upsert into `feed_items`, deduped by `(user_id, source_ref)`.
- **Serve:** `GET /feed` ranked; per-tab summary endpoints.
- **Notify:** rules decide push now, hold for brief, or stay silent.

**Cost note:** tool calls are Composio's meter and polling scales per user. Roughly 2,880 calls/user/month at a 15 minute interval, 8,640 at 5 minutes, against 20,000/month on the free tier. So: prefer triggers (push) wherever a provider supports them, and reserve polling for GitHub's inbox where there is no alternative.

---

## 5. Database (Supabase / Postgres)

Every table is keyed by `user_id` and protected by row-level security, so a user can only ever read their own rows. Multi-tenancy is built in from the first migration, not retrofitted.

| Table | Columns (essential) |
|---|---|
| `users` | `id` uuid PK, `email`, `github_login`, `timezone`, `expo_push_token`, `created_at` |
| `connections` | `id`, `user_id` FK, `provider` (github/slack/linear/gmail), `composio_connected_account_id`, `status`, `connected_at` |
| `feed_items` | `id` uuid, `user_id` FK, `source`, `source_ref`, `action_type`, `title`, `url`, `repo`, `actors` jsonb, `deadline` timestamptz, `is_blocking` bool, `priority_score` numeric, `status`, `raw` jsonb, `created_at`, `updated_at` · **UNIQUE (user_id, source_ref)** |
| `user_preferences` | `user_id` PK, `priority_repos` text[], `vip_actors` text[], `muted_repos` text[], `quiet_hours` jsonb, `brief_times` time[] |
| `notification_rules` | `id`, `user_id`, `name`, `level` (push/brief/off), `match` jsonb, `created_at` |
| `actions` | `id`, `user_id`, `feed_item_id` FK, `type`, `payload` jsonb, `result` jsonb, `performed_at` |
| `digests` | `id`, `user_id`, `window_start`, `window_end`, `item_ids` uuid[], `summary` text, `sent_at` |

- **RLS policy on every table:** `user_id = auth.uid()`.
- **The dedupe key is `(user_id, source_ref)`.** A poll and a webhook describing the same PR collapse into one row.
- Per-integration dashboard counts are computed from `feed_items` plus `actions` for the selected window. No separate stats table until it is measurably slow.

---

## 6. Categories

### 6.1 Action type (what you are being asked to do)

Framed as *what is being asked of you*, so it holds for a developer and a non-developer alike. Clusters are assigned by **deterministic rules**, not the LLM, so the same input always lands in the same place. Full per-platform mapping in [capabilities.md](capabilities.md) section 11.

| Cluster | Meaning | Sources across platforms |
|---|---|---|
| **Needs your decision** | A call only you can make | GitHub: CI failed on your PR, changes requested, repo invitation, security alert · Calendar: **invite awaiting RSVP**, moved or conflicting meeting · Drive: access request · Linear/Jira: issue assigned needing triage |
| **Needs your review** | Someone's work is waiting on your eyes | GitHub: review requested, ready for review · Drive: **doc shared for review**, pending suggestion · Calendar: agenda needing prep |
| **Needs your reply** | Someone is waiting on your words | Slack: **DM, mention, thread awaiting** · Drive: **comment or @mention on a doc** · Gmail: reply-needed thread · GitHub: comment on your PR · Notion/Linear: comment mentioning you |
| **Blocked on others** | Yours, but the ball is not in your court | Your PR awaiting review, you asked with no answer, awaiting others' RSVP |
| **Worth knowing** | Context only, digest only, never pings | Merged, closed, CI passed, release, file updated, **event cancelled (time back)**, status changed |

### 6.2 Urgency grouping (how Home is sectioned)

- **Needs you now**: someone is blocked on you, or a deadline is close. This is the only group allowed to push.
- **Waiting on others**: yours, but the ball is not in your court.
- **Later today**: real but not urgent.
- **Cleared**: done, with an explicit end state.

### 6.3 Notification level (what may interrupt)

- **Push**: immediate notification.
- **Brief**: held for the next digest (default 08:30 and 16:30).
- **Off**: visible in the app, never notified.

**Default mapping:**

| Category | Default level |
|---|---|
| Someone blocked on you (Review, Approve, blocking Reply) | Push |
| DM from a VIP | Push |
| Non-blocking Reply, Decide | Brief |
| CI results, status changes, merged/closed/released (FYI) | Brief |
| Muted repos/channels, anything you turned off | Off |
| **Anything new we have not seen before** | **Brief** (never Push) |

### 6.4 Custom rules

- Shape: `WHEN <source> <event/reason> [from <actor>] [in <repo/channel>] [matching <keyword>] THEN <push|brief|off>`.
- Examples: "always ping me when Priya DMs", "never notify me from `archived-repo`", "push anything mentioning `production`".
- Authored either from the rules screen, or in plain English and converted to a structured rule by the LLM (section 7).

---

## 7. Role of AI (deliberately narrow)

**Principle: rules first, LLM only where rules genuinely cannot decide.** GitHub's `reason` field already classifies most events for free. Sending every event to an LLM would add cost and latency for no accuracy gain.

**No LLM at all in Phase 1.** The tracer is fully deterministic.

From Phase 4, Claude does exactly four jobs:

1. **Ambiguity resolution.** Only for events rules cannot settle: Decide vs FYI, and "is this Slack message actually asking me something?" Reply-needed detection is genuinely linguistic and rules fail at it.
2. **Summarization.** The twice-daily brief and the per-integration daily summary in natural language ("3 PRs merged, 1 CI failure on glued_landing").
3. **Reply drafting.** A suggested response to a Slack thread or PR comment. **Always user-edited before sending, never auto-sent.**
4. **Rule authoring.** Turn "ping me when Priya DMs" into a structured `notification_rules` row.

**Ranking design (Phase 4 upgrade):**
- Score on **two separate axes**, confidence (does this genuinely need you) and severity/impact, combined into a composite. A single urgency number lets loud-but-trivial items dominate.
- **Actionability gate:** if you cannot act on it, log it, do not interrupt.
- **Personalize from behaviour:** learn from what you open, reply to, snooze and dismiss. Research shows a personalized profile beats a static classifier substantially on urgency accuracy.

---

## 8. Anxiety strategy (how this app stays calm)

The failure mode for this product is becoming another anxiety source. Explicit countermeasures:

- **Quiet by default.** New categories default to Brief, never Push, so the app gets **quieter** as it learns, not louder.
- **Only blocking work pushes.** If nobody is waiting on you, nothing buzzes.
- **The day ends.** A finite list with a real "You're clear for today" state. No infinite scroll.
- **Explain the silence.** The cleared screen says what was held back ("12 low-signal updates rolled into your evening brief"), so quiet never feels like something was missed.
- **Explain the ranking.** Every item can show "why this is top of your feed". Ranking that feels arbitrary destroys trust fast.
- **Batching over streaming.** Two briefs a day, not a live drip.
- **Quiet hours and weekends**, on by default.
- **No permanent red badge.** Badge counts only true blockers, never total unread.
- **Snooze is specific** ("until 14:00"), never a vague "later".

---

## 9. Phases

**Phase 0: backend spine (DONE)**
- Contracts, classification, scoring, feed service, FastAPI, in-memory repo, 38 tests green.
- Composio GitHub integration, real notifications flowing.

**Phase 1: persistence and live GitHub (backend only)**
- Supabase migrations for all tables plus RLS.
- `SupabaseFeedRepository` implementing the existing `FeedRepository` contract.
- Wire the Composio SDK path (needs GitHub connected under the API key's project).
- Prefect flow polling notifications on a schedule, respecting `X-Poll-Interval`.
- Enrichment (fetch PR details) for ranking.
- **Done when:** your real notifications persist to Supabase and `GET /feed` returns them ranked.

**Phase 2: the app you can see (Mac)**
- Expo app: Home feed and GitHub tab per the mockups, against the local backend.
- Design tokens from `design-system.md`.
- **Done when:** the feed renders on the iOS simulator on your Mac.

**Phase 3: acting and pushing**
- Approve, comment, snooze writing back to GitHub through Composio.
- Expo push (APNs/FCM) for Push-level items only.
- Rules screen plus `notification_rules` enforcement, briefs at 08:30 and 16:30.
- **Done when:** you approve a PR from your phone and it lands on GitHub.

**Phase 4: the AI layer**
- Claude for the four jobs in section 7.
- Two-axis scoring, actionability gate, behavioural personalization.

**Phase 5: Slack**
- Composio Slack triggers (real-time push, avoids the read rate limit).
- Slack tab with its summary dashboard.
- Reply in thread, react, and mark read from the app.

**Phase 6: Calendar, then Drive**
- **Calendar** (45 tools, 7 triggers): today's events, invites awaiting RSVP, cancellations. This is the phase that turns Home from a list into a plan, because it adds "and here is when you could actually do it".
- **Drive** (77 tools, 7 triggers): **document comments and @mentions**, and files shared with you. Note that Docs comments arrive via Drive's `COMMENT_ADDED`, not via the Docs toolkit. Reply to a doc comment in-app with `GOOGLEDRIVE_CREATE_REPLY`.

**Phase 7: Linear, then Gmail**
- Linear (46 tools, 12 triggers), low compliance cost, and the only source of **native due dates**.
- **Gmail last**, because restricted scopes bring a recurring annual CASA security assessment once you move off Composio's managed auth to your own branding.
- Notion and Jira on demand (Notion carries `COMMENT_CREATED`; Jira can **transition issue status** from the app).

**Why this order changed from v1:** the full capability sweep ([capabilities.md](capabilities.md)) showed Calendar and Drive deliver more feed value per unit of integration cost than Gmail, and neither carries Gmail's recurring audit. Gmail moved later.

---

## 10. How to run it

### 10.1 On your Mac first

```bash
cd /Users/vickypandey/Desktop/agentiwise/productivity-app
uv run pytest -q                                  # backend tests
uv run uvicorn backend.main:app --reload --port 8000
```

```bash
cd mobile && npm install && npx expo start
```

- Press `i` in the Expo terminal for the iOS simulator, `w` for browser.
- The app points at `http://localhost:8000`.

### 10.2 On your own iPhone (no Apple Developer account needed)

- Install **Expo Go** from the App Store.
- Run `npx expo start`, scan the QR code with the Camera app.
- Mac and iPhone must be on the same wifi, and the app's API base URL must be your Mac's LAN IP (for example `http://192.168.1.x:8000`), not `localhost`.

### 10.3 On an Android phone (someone else's)

- Install **Expo Go** from the Play Store, scan the QR code. Same wifi requirement.
- To hand someone an installable app instead, build an APK:

```bash
npm install -g eas-cli && eas build -p android --profile preview
```

- That produces a downloadable `.apk` you can send over any link. No Play Store listing required.

### 10.4 Giving it to other people properly

- **Android:** `eas build -p android --profile preview` gives an APK anyone can sideload. Play Store internal testing when you want it cleaner.
- **iOS:** requires an **Apple Developer account ($99/year)**. Then `eas build -p ios` plus **TestFlight**, which lets up to 10,000 external testers install it. There is no way to distribute an iOS app to other people's phones without this. Expo Go covers your own testing for free in the meantime.
- **Backend:** needs to be reachable, so deploy it (a small VM or container) before anyone outside your wifi can use the app.

---

## 11. Testing

- Backend is **test-first** (Red-Green-Refactor). Every new or modified function gets a test, in the root `tests/`.
- Tests run **through contracts** using `Fake*` implementations, never against live GitHub, Slack or Supabase.
- Mobile is implemented directly, no TDD, verified against the running backend.
- Current state: **38 passing**.

---

## 12. Risks and open items

1. **Composio branding.** Managed auth shows "Composio wants to access your account" on the consent screen. Fine for you and early testers, not fine for public launch. Switching to your own OAuth credentials is a Composio config change, not a rewrite, but it must happen before public launch.
2. **Composio shared quota.** Managed auth shares quota across all Composio users, and enforces a 15 minute minimum polling interval. Both argue for your own credentials once there is real usage.
3. **Gmail CASA.** Composio defers this cost, it does not delete it. Own credentials plus restricted scopes equals a recurring annual security assessment. Keep Gmail last.
4. **Slack read limits.** Non-Marketplace apps are throttled to 1 request/minute on message history. Design around Events API push. Research **refuted** the assumption that Marketplace approval lifts this, so do not plan around it.
5. **Polling cost scales per user.** See section 4. Model it before onboarding beyond a handful of people.
6. **Deadlines are not native to GitHub.** They live in Projects v2 (GraphQL) or milestones. Phase 1 ranks without them; add in Phase 4.
7. **Connected-account plumbing.** The Composio API key currently reports 0 connected accounts. Resolve before Phase 1.

---

## 13. What I want reviewed

- **The screens.** Do the six mockups match what you pictured? Especially Home and the per-integration tab shape.
- **The category taxonomy** (section 6). Are Review/Approve/Reply/Decide/FYI the right five?
- **Notification defaults** (6.3). Is "only blocking work pushes" too conservative?
- **The AI split** (section 7). Comfortable with rules-first and LLM only on the residue?
- **Phase order** (section 9). Slack before Linear, Gmail last.
