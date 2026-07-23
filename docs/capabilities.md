# Composio Capability Catalog

**Date:** 2026-07-23
**Purpose:** an exhaustive menu of what we *could* build, so the product scope is chosen from evidence rather than guesswork. Section 8 is the shortlist to review.

**How this was researched:** read-only discovery only (`composio search`, `--get-schema`, `dev toolkits list`, `dev triggers list`, plus Composio docs). **No live calls were made against connected accounts**, so no real Gmail or Slack data was touched.

**On SDK vs CLI:** everything below is reachable from the Python SDK. The CLI and SDK hit the same Composio API and the same tool slugs. The only current gap is that connections live in the CLI's project while the API key points at another one, which is a config fix, not a capability difference.

---

## 1. Inventory

| Toolkit | Tools | Triggers | Role in this product |
|---|---:|---:|---|
| **github** | 871 | 46 | Phase 1. Deepest surface by far. |
| **slack** | 158 | 9 | Phase 3. Read plus genuine reply. |
| **slackbot** | 98 | 9 | Bot-token variant of Slack. |
| **linear** | 46 | 12 | Phase 4. |
| **notion** | 45 | 8 | Later. |
| **jira** | 97 | 3 | Later, alternative to Linear. |
| **gmail** | 61 | 2 | Last (compliance cost). |
| **googlecalendar** | 45 | 7 | Optional, gives "what is on today". |
| **asana** | 153 | 6 | Optional. |
| **trello** | 322 | 5 | Optional. |

500 toolkits are available in total. The above are the relevant ones.

---

## 2. GitHub

### 2.1 What we can SHOW

**Attention items (feed):**
- Notification inbox with the `reason` field: `GITHUB_LIST_NOTIFICATIONS`. Verified live. `reason` values include `review_requested`, `assign`, `mention`, `team_mention`, `approval_requested`, `ci_activity`, `author`, `state_change`, `subscribed`, `security_alert`, `invitation`.
- PRs where my review is requested: `GITHUB_FIND_PULL_REQUESTS`, `GITHUB_SEARCH_ISSUES_AND_PULL_REQUESTS`
- Issues assigned to me across **all** repos in one call: `GITHUB_SEARCH_ISSUES_AND_PULL_REQUESTS`
- Repository invitations: `GITHUB_LIST_REPOSITORY_INVITATIONS`
- Reviews left on a PR (approved / changes requested): `GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST`
- Issue and PR comment threads: `GITHUB_LIST_ISSUE_COMMENTS`

**Activity dashboard (so you rarely open GitHub):**
- Commits, per repo, per time window: `GITHUB_LIST_COMMITS`
- Commit detail: `GITHUB_GET_A_COMMIT`
- Repos I belong to: `GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER`
- Raw repo activity stream: `GITHUB_LIST_REPOSITORY_EVENTS`
- CI status: `GITHUB_LIST_CHECK_RUNS_FOR_A_REF`, `GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY`
- Deployments: `GITHUB_LIST_DEPLOYMENTS`
- Branches, releases, tags, artifacts

**PR context (for the summarized view):**
- PR detail incl. mergeable state, reviewers: `GITHUB_GET_A_PULL_REQUEST`
- Files changed and diff stats: `GITHUB_LIST_PULL_REQUESTS_FILES`

**Escape hatch:** `GITHUB_RUN_GRAPH_QL_QUERY` runs arbitrary GraphQL. This is how we reach **Projects v2 date fields** (the only real source of GitHub due dates) and anything else REST omits.

### 2.2 What the user can DO

| Action | Tool | Include? |
|---|---|---|
| Comment on a PR or issue | `GITHUB_CREATE_AN_ISSUE_COMMENT` | Yes |
| Approve / request changes / comment review | `GITHUB_CREATE_A_REVIEW_FOR_A_PULL_REQUEST`, `GITHUB_SUBMIT_A_REVIEW_FOR_A_PULL_REQUEST` | Yes |
| Inline review comment on a line | `GITHUB_CREATE_A_REVIEW_COMMENT_FOR_A_PULL_REQUEST` | Probably not on mobile |
| Accept a repo invitation | `GITHUB_ADD_A_REPOSITORY_COLLABORATOR` and related | Maybe |
| Merge a PR | exists in the 871 | **No.** Your call, and correct: merging from a phone is not a decision you want to make on a 6 inch screen. |

### 2.3 Real-time triggers (46, the useful ones)

- `GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER` — a notification thread appears for a repo. **This is a push path to notifications**, per repo, avoiding the poll-only global inbox for repos we watch.
- `GITHUB_PULL_REQUEST_REVIEWERS_CHANGED_TRIGGER` — review requested of me
- `GITHUB_PULL_REQUEST_REVIEW_SUBMITTED_TRIGGER` — someone approved or requested changes on mine
- `GITHUB_PR_REVIEW_COMMENT_CREATED_TRIGGER` — inline review comment
- `GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER` — dedicated, exactly what we want
- `GITHUB_ISSUE_COMMENT_CREATED_TRIGGER`, `GITHUB_ISSUE_CREATED_TRIGGER`, `GITHUB_ISSUE_STATE_CHANGED_TRIGGER`
- `GITHUB_CHECK_RUN_STATUS_CHANGED_TRIGGER`, `GITHUB_CHECK_SUITE_STATUS_CHANGED_TRIGGER`, `GITHUB_WORKFLOW_RUN_STATE_CHANGED_TRIGGER` — CI
- `GITHUB_COMMIT_EVENT` — commits, feeds the activity dashboard
- `GITHUB_PULL_REQUEST_CREATED`, `GITHUB_PULL_REQUEST_STATE_CHANGED_TRIGGER`
- `GITHUB_CODE_SCANNING_ALERT_CREATED_TRIGGER`, `GITHUB_SECRET_SCANNING_ALERT_DETECTED_TRIGGER` — security
- `GITHUB_COLLABORATOR_ADDED_TRIGGER`, `GITHUB_DEPLOYMENT_*`, `GITHUB_RELEASE_*`
- Vanity: `GITHUB_NEW_STARGAZER_ADDED_TRIGGER`, `GITHUB_FOLLOWER_EVENT`

---

## 3. Slack

### 3.1 What we can SHOW
- Channels, DMs and groups: `SLACK_LIST_CONVERSATIONS`
- Message history for a conversation: `SLACK_FETCH_CONVERSATION_HISTORY`
- A full thread: `SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION`
- **Messages mentioning me:** `SLACK_SEARCH_MESSAGES`
- Channel metadata and notification prefs: `SLACK_RETRIEVE_CONVERSATION_INFORMATION`, `SLACK_GET_CHANNEL_CONVERSATION_PREFERENCES`
- Sender profile and presence: `SLACK_RETRIEVE_USER_PROFILE_INFORMATION`, `SLACK_GET_USER_PRESENCE`
- Deep link back to Slack: `SLACK_RETRIEVE_MESSAGE_PERMALINK_URL`

### 3.2 What the user can DO
| Action | Tool |
|---|---|
| **Reply, in a thread or channel** | `SLACK_SEND_MESSAGE` (thread via `thread_ts`) |
| React with an emoji (lightweight acknowledge) | `SLACK_ADD_REACTION_TO_AN_ITEM`, `SLACK_REMOVE_REACTION_FROM_ITEM` |
| **Mark a conversation read** | `SLACK_SET_READ_CURSOR_IN_A_CONVERSATION` |
| Start a DM | `SLACK_OPEN_DM` |

`SLACK_SET_READ_CURSOR_IN_A_CONVERSATION` matters more than it looks: handling something in our app can mark it read in Slack, so the two never disagree. That is what makes "seen vs unseen" trustworthy.

### 3.3 Triggers (5 live, 4 deprecated)
- `SLACK_DIRECT_MESSAGE_RECEIVED` — DMs
- `SLACK_CHANNEL_MESSAGE_RECEIVED` — public, private and group messages
- `SLACK_MESSAGE_REACTION_ADDED` / `SLACK_MESSAGE_REACTION_REMOVED`
- `SLACK_CHANNEL_CREATED`

**Limit worth designing around:** there is **no dedicated mention trigger**. Mentions must be detected by filtering `SLACK_CHANNEL_MESSAGE_RECEIVED` for the user's handle, or by polling `SLACK_SEARCH_MESSAGES`. Plan for the filter.

---

## 4. Linear
- Show: `LINEAR_LIST_LINEAR_ISSUES` (status and due date included), `LINEAR_GET_LINEAR_ISSUE`, `LINEAR_SEARCH_ISSUES`, `LINEAR_LIST_LINEAR_STATES`, `LINEAR_GET_CURRENT_USER`
- Act: `LINEAR_CREATE_LINEAR_COMMENT`, `LINEAR_UPDATE_LINEAR_COMMENT`, `LINEAR_CREATE_COMMENT_REACTION`
- Triggers (12): issue created/updated, comment created, project created/updated, project update posted. Public-team variants are webhook-driven; **private-team variants are polled**.
- Linear is the one tool with **native due dates**, so it is where deadline-based ranking gets real.

## 5. Gmail
- Show: `GMAIL_LIST_THREADS`, `GMAIL_FETCH_MESSAGE_BY_THREAD_ID`, `GMAIL_FETCH_EMAILS`, `GMAIL_GET_PROFILE`
- Act: `GMAIL_REPLY_TO_THREAD`, `GMAIL_CREATE_EMAIL_DRAFT` (draft-first is the safer default), `GMAIL_BATCH_MODIFY_MESSAGES` (read/labels)
- Triggers: only 2, `GMAIL_NEW_GMAIL_MESSAGE` and `GMAIL_EMAIL_SENT_TRIGGER`, both **polled**, so up to ~15 min latency on managed auth.

## 6. Notion / Jira / Calendar (later)
- Notion: 45 tools, 8 triggers. Pages, databases, comments.
- Jira: 97 tools, 3 triggers. The Linear alternative for enterprise users.
- Google Calendar: 45 tools, 7 triggers. Would answer "what is on today", which pairs naturally with a daily brief.

---

## 7. The options menu

Everything below is buildable. This is the menu to shortlist from.

### 7.1 Home (unified, cross-platform)
1. **Attention counter** ("7 need you today") as the single headline number
2. **Clustered groups** by what is being asked, not by app
3. Cross-app **priority list** (top 3 to 5 only)
4. **Blocking-others** callout ("2 people are waiting on you")
5. **Streak / cleared state** ("you are clear")
6. Per-app **unread pills** (GitHub 4, Slack 12, Linear 2)
7. **Daily brief card**, AI-written, morning and afternoon
8. **What changed since you last looked** (delta since last open)
9. **Quiet summary** of what was deliberately held back
10. Calendar strip, if Calendar is connected
11. **Deadline horizon** (due today / this week), Linear-driven
12. Quick filters (Mine / Blocking / Overdue)

### 7.2 GitHub screen
13. Commits: last 24h and 7d, **per repository**
14. PRs: open, mine, review-requested, draft vs ready
15. **PRs awaiting my review**, with waiting time
16. My PRs **awaiting others**, with who is blocking
17. CI status, failing runs first
18. Issues assigned to me, cross-repo
19. Issues mentioning me
20. **Repository invitations**
21. Security alerts (code scanning, secret scanning)
22. Releases and deployments
23. Review comment threads awaiting my reply
24. Per-repo activity sparkline
25. Stars and followers (vanity, low value, probably skip)

### 7.3 Slack screen
26. Unread totals, and **seen vs unseen** split
27. DMs awaiting reply
28. **Mentions** across channels
29. Thread replies awaiting me
30. Busiest channels (where it piled up)
31. Message preview **in-app** with full thread
32. Sender profile and presence
33. Keyword alerts (for example "production", "outage")
34. Channels I can safely ignore (muted suggestions)

### 7.4 Item detail
35. Full title, author, age, waiting time
36. **AI summary** ("what this PR is about")
37. Diff stats and files changed
38. Original comment or message that triggered it
39. Full thread context
40. Why it is ranked here (AI explanation)
41. Actions: approve, comment, request changes, react, reply, mark read, snooze
42. **Open in browser / Slack** deep link

### 7.5 Actions to expose (confirmed possible)
- GitHub: comment, submit review (approve / request changes), accept invitation. **Not merge.**
- Slack: reply in thread, react, mark read, open DM
- Linear: comment
- Gmail: reply or draft, mark read

---

## 8. Recommended shortlist

The mode of the product is **cluster and categorize, never a raw notification dump**. So:

**Home shows:** the attention counter (1), clustered groups (2), the blocking-others callout (4), the cleared state (5), and the AI daily brief (7). Nothing else. Everything else lives one tap deeper.

**Clusters are deterministic** (rules, not the LLM) so the same input always lands in the same place:
- **Needs your decision** (approve, invitation, changes requested, CI failure on your PR)
- **Needs your review** (PR review requested, ready for review)
- **Needs your reply** (DM, mention, comment on yours, thread awaiting you)
- **Blocked on others** (yours, waiting on them)
- **Worth knowing** (merged, closed, CI passed, releases) — digest only, never pings

Note on your "review is too niche" point: **Review** stays as its own cluster because it is the single most common blocking ask for this audience, but it sits under the broader frame of *what is being asked of you*, alongside Decision and Reply. For a non-developer, Review and Decision are the two that carry over, and they stay meaningful.

**GitHub screen:** 13, 15, 16, 17, 18, 20 (commits per repo, PRs awaiting me, my PRs awaiting others, CI, issues assigned, invitations).

**Slack screen:** 26, 27, 28, 30, 31 (unread and seen/unseen, DMs, mentions, busiest channels, in-app thread with reply).

**Detail:** 35, 36, 38, 40, 41, 42.

### Where AI actually earns its place
Not autocomplete, not reply-all. Four jobs, in value order:
1. **Summarize** so you do not have to open the source. "This PR swaps the icon set and touches 3 files" is the difference between opening GitHub and not.
2. **Explain the ranking.** One line on why something is top. This is what makes the ordering trustworthy instead of arbitrary.
3. **Write the brief.** Two paragraphs a day covering what happened and what needs you.
4. **Detect reply-needed** in Slack, which is genuinely linguistic and rules cannot do it.

Deliberately excluded for now: auto-reply, tab-to-complete, and anything that sends on the user's behalf without them reading it.

---

## 9. Limits to design around

1. **No Slack mention trigger.** Filter channel messages for the handle, or poll search.
2. **GitHub global notification inbox is poll-only.** Per-repo push exists via `GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER`, so watched repos can be real-time while the catch-all stays polled.
3. **Gmail has only 2 triggers, both polled.** Up to ~15 min latency on managed auth.
4. **Linear private teams are polled**, public teams are pushed.
5. **Managed auth enforces a 15 minute minimum poll interval**, and shares quota across Composio users.
6. **Tool calls are the meter.** Prefer triggers over polling wherever a provider supports them.
7. **GitHub due dates are not native.** They come from Projects v2 via `GITHUB_RUN_GRAPH_QL_QUERY`, or from milestones.
