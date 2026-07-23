# Composio Capability Catalog (all platforms)

**Date:** 2026-07-23
**Purpose:** an exhaustive, evidence-based menu of what we can read, what the user can act on, and what fires in real time, across every platform that generates work notifications. Section 11 is the shortlist.

**Method:** read-only discovery only (`composio search`, `--get-schema`, `dev toolkits list`, `dev triggers list`). **No live calls were made against connected accounts.**

**SDK vs CLI:** everything below is reachable from the Python SDK. Same API, same tool slugs. The only open item is that connections currently sit in the CLI's project while the API key points at another, which is config, not capability.

---

## 1. Inventory

| Toolkit | Tools | Triggers | Notification value |
|---|---:|---:|---|
| **github** | 871 | 46 | Very high. Deepest surface available. |
| **outlook** | 286 | 5 | High, if the user is Microsoft-based. |
| **slack** | 158 | 9 | Very high. Read plus genuine reply. |
| **asana** | 153 | 6 | Medium. |
| **jira** | 97 | 3 | High for enterprise teams. |
| **zoom** | 90 | 11 | Low to medium. |
| **googledrive** | 77 | 7 | **High. Carries doc comments and shares.** |
| **gmail** | 61 | 2 | High value, highest compliance cost. |
| **linear** | 46 | 12 | High. Native due dates. |
| **googlecalendar** | 45 | 7 | **High. Time context, not just alerts.** |
| **notion** | 45 | 8 | Medium to high. |
| **googlesheets** | 45 | 16 | Low for notifications. |
| **googledocs** | 41 | 10 | Medium. Content, not comments (see 5). |

500 toolkits exist in total. Above are the ones relevant to a work feed.

---

## 2. GitHub

**Show:** notification inbox with `reason` (`GITHUB_LIST_NOTIFICATIONS`, verified live); PRs awaiting my review (`GITHUB_FIND_PULL_REQUESTS`); cross-repo assigned issues in one call (`GITHUB_SEARCH_ISSUES_AND_PULL_REQUESTS`); **repository invitations** (`GITHUB_LIST_REPOSITORY_INVITATIONS`); reviews on a PR (`GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST`); comment threads (`GITHUB_LIST_ISSUE_COMMENTS`); commits per repo (`GITHUB_LIST_COMMITS`); CI (`GITHUB_LIST_CHECK_RUNS_FOR_A_REF`, `GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY`); deployments; releases; PR detail and files (`GITHUB_GET_A_PULL_REQUEST`, `GITHUB_LIST_PULL_REQUESTS_FILES`).

**Act:** comment (`GITHUB_CREATE_AN_ISSUE_COMMENT`); **approve / request changes** (`GITHUB_CREATE_A_REVIEW_FOR_A_PULL_REQUEST`); inline review comment; accept invitation. **Not merge**, by decision.

**Triggers (46, best):** `REPOSITORY_NOTIFICATION_RECEIVED` (per-repo push path to notifications), `ISSUE_ASSIGNED_TO_ME`, `PULL_REQUEST_REVIEWERS_CHANGED`, `PULL_REQUEST_REVIEW_SUBMITTED`, `PR_REVIEW_COMMENT_CREATED`, `ISSUE_COMMENT_CREATED`, `CHECK_RUN_STATUS_CHANGED`, `WORKFLOW_RUN_STATE_CHANGED`, `COMMIT_EVENT`, `CODE_SCANNING_ALERT_CREATED`, `SECRET_SCANNING_ALERT_DETECTED`.

**Escape hatch:** `GITHUB_RUN_GRAPH_QL_QUERY` reaches Projects v2 date fields, the only real source of GitHub due dates.

---

## 3. Slack

**Show:** conversations (`SLACK_LIST_CONVERSATIONS`); history (`SLACK_FETCH_CONVERSATION_HISTORY`); full thread (`SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION`); **mentions** (`SLACK_SEARCH_MESSAGES`); channel prefs; sender profile and presence; permalink (`SLACK_RETRIEVE_MESSAGE_PERMALINK_URL`).

**Act:** **reply in thread** (`SLACK_SEND_MESSAGE`); react (`SLACK_ADD_REACTION_TO_AN_ITEM`); **mark read** (`SLACK_SET_READ_CURSOR_IN_A_CONVERSATION`); open DM.

**Triggers (5 live):** `DIRECT_MESSAGE_RECEIVED`, `CHANNEL_MESSAGE_RECEIVED`, `MESSAGE_REACTION_ADDED` / `REMOVED`, `CHANNEL_CREATED`.

**Limit:** **no dedicated mention trigger.** Filter channel messages for the handle, or poll search.

---

## 4. Google Calendar

Calendar is different in kind: it supplies **time context**, not just alerts. It answers "when could you actually do this", which is what makes a feed realistic rather than a wish list.

**Show:** today's events with attendees (`GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS`); event detail (`GOOGLECALENDAR_EVENTS_GET`); find events (`GOOGLECALENDAR_FIND_EVENT`); calendars (`GOOGLECALENDAR_LIST_CALENDARS`); current time (`GOOGLECALENDAR_GET_CURRENT_DATE_TIME`).

**Act:** **RSVP** by patching your attendee response (`GOOGLECALENDAR_PATCH_EVENT`); update or delete an event. There is no single dedicated "RSVP" tool, so the patch mechanics need one verification pass before we build on it.

**Triggers (7, all polling):** `EVENT_STARTING_SOON` (configurable minutes ahead), `EVENT_CREATED` (someone invited you), `EVENT_UPDATED` (time moved), `EVENT_CANCELED_DELETED` (you got time back), `ATTENDEE_RESPONSE_CHANGED`, `EVENT_SYNC` (full data with attendees).

---

## 5. Google Drive (carries Docs and Sheets comments)

**The most under-rated source.** Comments and @mentions on Docs, Sheets and Slides all arrive through Drive, not through the Docs toolkit.

**Show:** files shared with me (`GOOGLEDRIVE_FIND_FILE`); **comments** (`GOOGLEDRIVE_LIST_COMMENTS`, `GOOGLEDRIVE_GET_COMMENT`); replies (`GOOGLEDRIVE_LIST_REPLIES`); permissions and who has access (`GOOGLEDRIVE_LIST_PERMISSIONS`); file metadata.

**Act:** **reply to a document comment** (`GOOGLEDRIVE_CREATE_REPLY`); update a reply (`GOOGLEDRIVE_UPDATE_REPLY`). This is the direct parallel of Slack reply, for docs.

**Triggers (7):** `COMMENT_ADDED` (**Docs, Sheets and Slides comments, so @mentions land here**), `FILE_SHARED_PERMISSIONS_ADDED` (**someone shared a file with you**), `FILE_CREATED`, `FILE_UPDATED`, `FILE_DELETED_OR_TRASHED`, `GOOGLE_DRIVE_CHANGES`, `NEW_FILE_MATCHING_QUERY`.

---

## 6. Google Docs

**Show:** **plain text of a document** (`GOOGLEDOCS_GET_DOCUMENT_PLAINTEXT`), which is exactly what the AI summarizer needs; document by id; search documents.

**Act:** create and edit documents (not needed for a feed).

**Triggers (10):** document created / updated / deleted, structure changed, keyword detected, word-count threshold, search update, placeholder filled. These are **document-lifecycle, not notification**. For "someone commented on my doc", use Drive (section 5).

---

## 7. Gmail

**Show:** threads (`GMAIL_LIST_THREADS`), messages (`GMAIL_FETCH_MESSAGE_BY_THREAD_ID`), profile.
**Act:** **reply** (`GMAIL_REPLY_TO_THREAD`), **draft** (`GMAIL_CREATE_EMAIL_DRAFT`, the safer default), mark read / label (`GMAIL_BATCH_MODIFY_MESSAGES`).
**Triggers:** only 2, `NEW_GMAIL_MESSAGE` and `EMAIL_SENT`, **both polled**.
**Cost:** restricted scopes bring a recurring annual CASA assessment once we move off managed auth. Keep last.

---

## 8. Linear

**Show:** `LINEAR_LIST_LINEAR_ISSUES` (status **and due date**), `GET_LINEAR_ISSUE`, `SEARCH_ISSUES`, `LIST_LINEAR_STATES`, `GET_CURRENT_USER`.
**Act:** `LINEAR_CREATE_LINEAR_COMMENT`, `UPDATE_LINEAR_COMMENT`, `CREATE_COMMENT_REACTION`.
**Triggers (12):** issue created / updated, comment created, project created / updated / update posted, with public-team (webhook) and private-team (polled) variants.
**Unique value:** the only tool with **native due dates**, so deadline ranking becomes real here.

## 9. Notion

**Show:** `NOTION_SEARCH_NOTION_PAGE`, `RETRIEVE_PAGE`, `FETCH_BLOCK_CONTENTS`, `FETCH_DATABASE`.
**Triggers (8):** **`NOTION_COMMENT_CREATED`** (the notification-relevant one), page created, page content updated, page properties updated, database and view created.

## 10. Jira

**Show:** `JIRA_SEARCH_FOR_ISSUES_USING_JQL_GET` (anything expressible in JQL, so "assigned to me and not done"), `GET_ISSUE`, `LIST_ISSUE_COMMENTS`.
**Act:** `JIRA_ADD_COMMENT`, **`JIRA_TRANSITION_ISSUE`** (move status from our app), `EDIT_ISSUE`.
**Triggers:** only 3, so Jira leans on polling via JQL.

---

## 11. Unified notification map

This is the synthesis. Every source below rolls into one of five deterministic clusters.

| Cluster | GitHub | Slack | Calendar | Drive / Docs | Gmail | Linear / Jira / Notion |
|---|---|---|---|---|---|---|
| **Needs your decision** | CI failed on your PR, changes requested, repo invitation, security alert | question aimed at you | **invite awaiting RSVP**, moved or conflicting meeting | **access request**, file shared needing action | email needing a call | issue assigned needing triage |
| **Needs your review** | review requested, ready for review | "can you look at this" | agenda needing prep | **doc shared for review**, pending suggestion | attachment to review | issue in review |
| **Needs your reply** | comment on your PR or issue | **DM, mention, thread awaiting** | invite with a question | **comment or @mention on a doc** | reply-needed thread | comment mentioning you |
| **Blocked on others** | your PR awaiting review | you asked, no answer | awaiting others' RSVP | awaiting their comment | awaiting their reply | your issue awaiting someone |
| **Worth knowing** (digest only) | merged, closed, CI passed, release | channel chatter, reactions | **event cancelled** (time back) | file updated | newsletters | status changed |

### Actions confirmed available in-app

| Platform | Actions we can genuinely offer |
|---|---|
| GitHub | comment, **approve**, request changes, accept invitation (not merge) |
| Slack | **reply in thread**, react, **mark read**, open DM |
| Drive / Docs | **reply to a comment** |
| Calendar | **RSVP** (via patch), reschedule, delete |
| Gmail | reply, **draft**, mark read, label |
| Linear | comment |
| Jira | comment, **transition status** |
| Notion | (read-focused for now) |

---

## 12. Recommended shortlist

**Mode of the product: cluster and categorize, never a raw notification dump.**

**Home (unified):** the attention count, the five clusters, the blocking-others callout, the cleared state, the AI brief, and **today's remaining meeting time from Calendar**. Nothing else.

**Why Calendar earns a place early despite being "just" a calendar:** it converts the feed from a list into a plan. "Seven things need you, and you have 90 free minutes before your 14:00" is a fundamentally more useful sentence than either half alone. It is also cheap: 45 tools, 7 triggers, no compliance burden beyond standard Google scopes.

**Per-platform tabs:** GitHub and Slack first (deepest surfaces), then Calendar, Drive, Linear, Gmail.

**Integration order, revised from the capability evidence:**
1. **GitHub** (phase 1, deepest, no compliance cost)
2. **Slack** (real-time triggers, genuine reply)
3. **Calendar** (time context, cheap, transforms Home)
4. **Drive** (doc comments and shares, a genuinely under-served notification source)
5. **Linear** (due dates)
6. **Gmail** (last, CASA cost)
7. Notion / Jira on demand

Gmail moved **later** than in plan v2, because Drive and Calendar deliver more feed value per unit of integration cost, and neither carries Gmail's recurring audit.

### Where AI earns its place
1. **Summarize** so you do not open the source (`GOOGLEDOCS_GET_DOCUMENT_PLAINTEXT` and PR files make this real).
2. **Explain the ranking**, one line, so ordering is trustworthy.
3. **Write the brief**, twice a day.
4. **Detect reply-needed** in Slack, email and doc comments, which is linguistic and rules cannot do it.

Excluded: auto-reply, tab-complete, anything that sends without the user reading it.

---

## 13. Limits to design around

1. **No Slack mention trigger.** Filter channel messages, or poll search.
2. **GitHub global notification inbox is poll-only.** Per-repo push exists via `REPOSITORY_NOTIFICATION_RECEIVED`.
3. **Gmail has 2 triggers, both polled.**
4. **All 7 Calendar triggers are polling.** Expect up to the managed-auth floor of ~15 minutes.
5. **Doc comments come from Drive, not Docs.** Easy to get wrong.
6. **Linear private teams poll**, public teams push.
7. **Jira has only 3 triggers**, so it leans on JQL polling.
8. **Calendar RSVP has no dedicated tool.** It is a patch on the attendee response and needs one verification pass.
9. **Managed auth enforces a 15 minute minimum poll** and shares quota.
10. **Tool calls are the meter.** Prefer triggers over polling; polling cost scales per user per platform.
