# MVP Plan: GitHub Tracer Slice

**Date:** 2026-07-23
**Companion to:** [product-brief.md](product-brief.md), [product-research.md](product-research.md)

## 1. Goal and non-goals

**Goal:** prove the entire product spine on **one integration (GitHub)** before adding any breadth. A GitHub event becomes a classified, priority-ranked item in a mobile feed, and the user can act on it back into GitHub, with a push notification on high-priority items. This is the Tracer Bullet: the thinnest path that touches every layer.

**In scope for the tracer:**
- GitHub App install (personal first), notifications poll + `pull_request` webhook.
- Deterministic classification into the action taxonomy (no LLM yet).
- Simple composite priority score.
- One mobile feed screen, ranked.
- One write action back to GitHub (comment on a PR).
- One push notification path.

**Explicitly not in the tracer** (later phases): LLM classification, Projects v2 deadlines, Linear/Slack/Gmail, multi-user onboarding at scale, batching/digests, snooze/rules UI.

## 2. Stack (decided)

| Layer | Choice | Why |
|---|---|---|
| Mobile | **React Native + Expo** (TypeScript) | One codebase for iOS + Android, TS-first (shares types/patterns with backend), Expo abstracts APNs/FCM push + OTA. |
| Backend | **Python + FastAPI** | AI pipeline + data-heavy; matches the "Python for AI/automation backends" rule. |
| Scheduler | **Prefect** | External-data app polling GitHub on a schedule. Managed cron is disallowed by rule; logic stays in the codebase. |
| Database + auth | **Supabase (Postgres)** | Postgres + auth + realtime out of the box, fastest MVP. Migrate if scale cost bites. |
| LLM | **Anthropic SDK (Claude)** | Added after the tracer, for the ambiguous-classification residue only. |
| GitHub auth primitive | **GitHub App** | Gives webhooks + notifications inbox + per-install tokens. "Personal-first" just means one install initially; multi-user needs no re-architecture. |

This is **Pattern A (multi-runtime)**: each top-level folder is its own deployment boundary, communicating over HTTP (or the DB), no imports across folders.

```
productivity-app/
  backend/                 # FastAPI: API + business logic
    api/routes/            # thin HTTP handlers, delegate to services
    services/              # classification, priority, feed (contract + impl)
    integrations/github/   # GitHubService contract + implementation
    database/repositories/ # data access, one file per entity
    models/                # request/response + FeedItem types
  mobile/                  # React Native + Expo (TypeScript)
    src/screens/           # FeedScreen, ItemDetail
    src/components/feed/    # feed card, action bar
    src/lib/               # api client + shared types
  prefect/                 # scheduled GitHub notification pollers
  supabase/                # migrations
  docs/
  tests/                   # backend tests at the contract boundary (repo root)
```

## 3. Architecture: the poll + webhook + enrich model

GitHub gives two event channels, and neither is complete alone:

- **Notifications API** (`GET /notifications`): the per-user "what needs me" inbox. **Poll-only** (no webhook); returns `304 Not Modified` between changes and dictates cadence via the `X-Poll-Interval` header. Each thread carries a coarse `reason` and a `subject.url`, not the content.
- **Webhooks** (GitHub App installation): real-time, full payloads (`pull_request`, `pull_request_review`, `issues`, `check_run`, `deployment_review`, ...).

Because notifications are thin, the pipeline is always:

> **notify** (cheap, tells you *that* something happened) → **enrich** (fetch the PR/issue/review object to learn *what* it is and *how urgent*) → **classify** → **score** → **store** → **serve**.

Prefect runs the per-user notification poller (respecting `X-Poll-Interval`); FastAPI receives webhooks at `POST /webhooks/github`. Both feed the same normalization pipeline.

## 4. GitHub data surface (what we pull, by action type)

| Action type | Signal | Source |
|---|---|---|
| **Review** | PR review requested of you; draft → ready; re-review requested | `reason: review_requested` · webhook `pull_request` (`review_requested`, `ready_for_review`) |
| **Approve** | Pending deployment/environment approval; you are a required approver | `reason: approval_requested` · webhook `deployment_review` / `deployment_protection_rule` |
| **Reply** | @mention / @team-mention; comment on your PR/issue; unresolved review-comment thread; discussion mention | `reason: mention` / `team_mention` / `comment` · webhooks `issue_comment`, `pull_request_review_comment`, `pull_request_review_thread`, `discussion` |
| **Decide / Act** | Issue or PR assigned to you; changes requested on your PR; CI failed on your PR; merge blocked; repo invitation; security alert | `reason: assign` / `ci_activity` / `security_alert` · webhooks `issues.assigned`, `pull_request_review` (changes_requested), `check_run`/`check_suite`/`workflow_run` (failure) |
| **FYI** (batched) | PR approved (mergeable); PR merged/closed; issue closed; CI passed; release; subscribed-thread updates | `reason: state_change` / `subscribed` · webhooks `pull_request` (closed), `release` |

**Enrichment for ranking:** PR age, additions/deletions, files changed, requested reviewers, mergeable state, who-is-blocked-on-whom; issue labels, milestone, assignees, linked PRs; actor importance; repo priority.

**Deadlines:** GitHub has **no native due-date on issues**. Deadlines come from **Projects v2 date fields** (GraphQL only) or **milestones**. Ranking by deadline requires reading Projects v2, so it is a phase-2 add, not tracer.

## 5. Data model (Supabase / Postgres)

| Table | Key columns |
|---|---|
| `users` | id, github_user_id, expo_push_token |
| `github_installations` | user_id, installation_id, token refs |
| `feed_items` | id, user_id, source (`github`), source_ref (thread/PR node id), action_type, title, url, actors (jsonb), deadline, priority_score, status (`unread`/`acted`/`dismissed`/`snoozed`), raw (jsonb), created_at, updated_at |
| `user_preferences` | user_id, priority_repos, vip_actors, muted_repos, batch_schedule |
| `actions` | feed_item_id, type, payload (jsonb), performed_at |

`feed_items.source_ref` is the dedupe key: a notification and a webhook for the same PR upsert to one row (this mirrors the retry-cap-by-unit-of-work discipline: the unit is the item, not the row).

**Isolation (multi-tenant from the first commit):** every table is keyed by `user_id` and protected by Supabase Row Level Security, so a user can read only rows where `user_id` equals their own authenticated id. Each person who installs the app connects their own GitHub account (their own App token) and sees only their own feed. There is no code path that returns one user's data to another. This is not deferred.

## 6. Contracts first (interface-first delegation)

The seams I define before any implementation. Callers import the contract only; tests run against it with `Fake*` implementations.

```python
# models/feed.py  (mirrored as a TS type in mobile/src/lib/types.ts)
class FeedItem(BaseModel):
    id: str
    source: Literal["github"]
    source_ref: str
    action_type: Literal["review", "approve", "reply", "decide", "fyi"]
    title: str
    url: str
    actors: list[Actor]
    deadline: datetime | None
    priority_score: float
    status: Literal["unread", "acted", "dismissed", "snoozed"]

# integrations/github/contract.py
class GitHubService(Protocol):
    def list_notifications(self, since: datetime | None) -> list[RawEvent]: ...
    def get_pull_request(self, ref: PRRef) -> PullRequest: ...
    def comment_on_pull_request(self, ref: PRRef, body: str) -> Comment: ...

# services/classification/contract.py
class ClassificationService(Protocol):
    def classify(self, event: RawEvent) -> ActionType: ...   # tracer: rules on `reason`

# services/priority/contract.py
class PriorityService(Protocol):
    def score(self, item: FeedItem, prefs: UserPreferences) -> float: ...
```

**HTTP contract (also the mobile ↔ backend seam):**
- `GET /feed` -> `FeedItem[]` (ranked desc by priority_score)
- `POST /feed/{id}/actions` `{ type: "comment", body }` -> action result
- `POST /webhooks/github` (webhook receiver)
- `GET /auth/github/callback` (App OAuth)

## 7. The tracer slice (build this first, end to end)

1. **Install** the GitHub App on your account. Store `installation_id` + user token.
2. **Ingest:** Prefect polls `GET /notifications` (respecting `X-Poll-Interval`); FastAPI receives `pull_request` webhooks. Both emit a `RawEvent`.
3. **Enrich:** for each event, fetch the PR (title, url, requested reviewers, mergeable) via `GitHubService.get_pull_request`.
4. **Classify:** `ClassificationService.classify` maps `reason`/action to an `ActionType` (pure rules, no LLM).
5. **Score:** `PriorityService.score` = simple composite (deadline proximity + is-blocking + action-type weight).
6. **Store:** upsert into `feed_items` by `source_ref`.
7. **Serve:** `GET /feed` returns the ranked list.
8. **Render:** Expo `FeedScreen` shows ranked cards; tap opens `ItemDetail`.
9. **Act:** "Comment on PR" -> `POST /feed/{id}/actions` -> `GitHubService.comment_on_pull_request`. Item status flips to `acted`.
10. **Push:** on storing a high-priority item, send a push via Expo (APNs/FCM) to the device.

If this one path works (event in → ranked feed out → action back to GitHub → push to phone), every later integration is a variation on the same spine.

## 8. Phases after the tracer

1. **GitHub depth:** full taxonomy (reviews, checks, deployments, security), Projects v2 deadlines (GraphQL), notification→enrich caching with conditional requests.
2. **AI classification:** Claude classifier for the ambiguous residue only (Decide vs FYI, reply-needed detection). Deterministic rules stay on the hot path; the LLM handles what rules cannot. Two-axis score (confidence x severity) + actionability gate + morning/afternoon batching (see research Section 5).
3. **Linear** (GraphQL + webhooks, low compliance cost).
4. **Slack** (Events API push; sequence after enough installs to approach the Marketplace ≥5-workspace threshold; do not rely on Marketplace approval lifting the read rate limit).
5. **Gmail** (last: restricted-scope CASA annual audit + Pub/Sub + 7-day `watch()` renewal).

## 9. Testing (Red-Green-Refactor, contract boundary)

- Backend is test-first. Every new/modified function gets a test scoped to that function, in the root `tests/`.
- Tests run through the **public contract** with `Fake*` implementations, never against internals or the real GitHub API.
- Tracer test set: `classify()` per `reason` value → asserts `action_type`; `score()` → asserts ordering; `comment_on_pull_request` via `FakeGitHubService`; `GET /feed` returns items sorted by score.
- Mobile: implemented directly (no TDD), verified against the running feed endpoint.

## 10. Risks and open decisions

1. **Projects v2 deadlines are GraphQL-only** and not on the issue object. Phase 2, not tracer.
2. **Notification→enrich fan-out** can hit REST rate limits at scale. Mitigate with conditional requests (ETag/`If-Modified-Since`) and caching the enriched object.
3. **Act-from-feed needs write scopes,** which raises the OAuth review bar and the user-trust bar. Budget for it.
4. **Dedupe:** a notification and a webhook can describe the same PR. `source_ref` upsert keeps it one feed item.
5. **Deferred onboarding UX, not deferred isolation.** Data isolation is multi-tenant from day one (Section 5: every row is `user_id`-scoped and enforced by Supabase RLS), so a second installer sees only their own data, never yours. "Single-user tracer" means only one real account (yours) is connected while we prove the pipeline. The polished multi-user sign-up and install flow is the additive next step, not a rewrite, because the GitHub App primitive is already per-user. Confirm this sequencing is acceptable.
