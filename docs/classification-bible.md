# Classification Bible — the single source of truth

This is the canonical rulebook for how every item from every source is categorised, where the decision is deterministic vs made by the LLM, where the LLM's reasoning is stored, how Later is populated, and the volume caps per source. If behaviour and this doc disagree, one of them is a bug. Keep this in sync with `backend/services/tier_bands.py`, `backend/services/rules.py`, and the per-source mappers.

Last verified against the tree: 2026-07-26.

---

## 1. The four categories (mutually exclusive)

Internally the tier enum is `urgent > today > can_wait > noise` (`backend/models/tiers.py`). User-facing:

| Category (UI) | Tier (code) | Meaning |
|---|---|---|
| **Urgent** | `urgent` | A specific person is actively waiting, or a hard deadline is past / within a few hours. |
| **By EOD** | `today` | Needs handling today; nobody is blocked right now. Anything with a stated deadline of today/tomorrow. |
| **Can wait** | `can_wait` | Genuinely needs you eventually, no time pressure. |
| **Later** | `noise` (routing) | No action asked of you. Shown in the Later tab, live. |

**Home** (Day + To-dos tabs) shows the three elevated buckets (Urgent / By EOD / Can wait). **Later** is the residual: what a source currently holds that was *not* elevated to Home. An item is in exactly one place. Later items surfacing inside the To-dos list is intended (finished actionable items still read as usable there); the distinction that matters is *elevated vs residual*.

---

## 2. The two decision mechanisms

Every signal is classified one of two ways:

**Deterministic** — a stated, structured fact fixes the category with no model: a GitHub reason, a CI conclusion, a security flag, a Linear due date, a calendar event type, a Gmail category tab, an urgent label. Cheap, instant, never queued for the model.

**LLM within a band** — for prose where urgency is not stated (a personal email, a Slack DM, a GitHub mention, a Docs comment), the model rates urgency and the rating is **clamped to `[floor, ceiling]`** set by the source/signal (`ranking.effective_tier` + `models/tiers.clamp`). The floor guarantees a minimum (a review request can never sink below By EOD); the ceiling caps it (a comment can rise to Urgent but starts at Can wait). The band is the guardrail; the model moves within it.

**Where the LLM reasoning is stored.** Two fields per item, written by the classifier (`services/classifier.py`): `summary` (≤90 chars, what it asks of you) and `reason` (≤60 chars, the evidence for the tier). Plus `llm_tier` (the model's rating) and `llm_attempted_at` (the attempt marker). Today these live on the `feed_items` row in Postgres; under the Phase 0 Redis plan they ride in the Redis feed row with the content (24h TTL). Deterministic items carry no model reason except the one deterministic line worth showing (Linear's "Overdue since 24 Jul" / "Due today", `tier_bands.linear_reason`).

**The clamp override for labels.** On a banded GitHub/Linear item, a structured urgency label short-circuits the model: an urgent label (`p0`, `blocker`, `critical`, `urgent`, `sev1`, `production`, `incident`) pins to the band ceiling deterministically; a low label (`low priority`, `p3`, `someday`, `backlog`, `wontfix`) pins to the floor. Either way `needs_llm` becomes false.

---

## 3. Per-source rules

### 3.1 GitHub

Recognition (`rules._canonical_reason` + `composio_github.notification_to_raw_event`): the notification `reason`, plus overrides — a security alert, a CI conclusion, or an approval/review flag win over the raw reason so the card carries one tag.

**Deterministic (no model):**
| Signal | Category | Why |
|---|---|---|
| `security_alert` | **Urgent** | A stated security alert on your repo. |
| `ci_failure_mine` (your PR's check failed) | **Urgent** | Your build is red. |
| `ci_failure_other` (a failed check on a repo you watch) | **Urgent** | A broken build is worth surfacing (Vicky's call 2026-07-26). |
| `ci_ok` (check succeeded) | **Later** | Informational. |
| `review_request_removed` | **Later** | Nothing to do. |
| `subscribed`, `author`, `state_change` | **Later** | Watched-repo noise, activity on your own thread, open/close/merge. |
| `invitation` (repo invite) | **By EOD** | A decision that should not sit for days. |

**LLM within a band** (floor..ceiling):
| Signal | Band (floor → ceiling) | Tag |
|---|---|---|
| `approval_requested` | By EOD → Urgent | approve |
| `review_requested` | By EOD → Urgent | review |
| `changes_requested_mine` | By EOD → Urgent | decide |
| `assign` | By EOD → Urgent | assigned |
| `mention` / `team_mention` | Can wait → Urgent | reply |
| `comment` | Can wait → Urgent | comment |

**GitHub Later** = notifications the ingest dropped as noise (`ci_ok`, `ci_failure_other`, `subscribed`, `author`, `state_change`, `review_request_removed`). The actionable ones are on Home and excluded.

### 3.2 Gmail

Recognition (`gmail.message_to_raw_event`): only `UNREAD` mail in the last 30 days is a candidate (read mail returns nothing). Two model buckets + one deterministic-Later bucket (Vicky's call 2026-07-26: a "subscription expiring" / payment email must not be deterministically buried, so `List-Unsubscribe` and Updates/Forums no longer force Later — they go to the model instead).

**Deterministic (no model) — the only mail that skips the model:**
| Signal | Category | Why |
|---|---|---|
| `gmail_bulk` — filed under **Promotions / Social / Spam / Trash** | **Later** | Unambiguous noise. Never addressed to you. |

**LLM within a band — two buckets, each the top 100 newest in the last 30 days:**
| Signal | Source query | Band (floor → ceiling) | Tag |
|---|---|---|---|
| `gmail_message` (personal INBOX) | `is:unread newer_than:30d -category:promotions -social -forums -updates` | **Later → Urgent** | reply |
| `gmail_transactional` (Updates / Forums / `List-Unsubscribe`) | the same window, the transactional slice | **Later → Urgent** | reply |

Both buckets floor at Later, so anything the model judges no-action still sinks to Later, but a payment/subscription/renewal email is now *seen* by the model instead of buried. Gmail is the only source whose floor is Later.

**Caps:** each model bucket is capped at **100** newest (`PAGE_SIZE`); the card surface shows a "latest 100 in the last 30 days" heading so the user knows the window.
**Gmail Later (live, no model)** — `is:unread newer_than:30d`, up to **400** (`MAX_UNREAD`), streamed 200 at a time, minus whatever is on Home.

### 3.3 Slack

Recognition (`slack.direct_message_to_raw_event` / `channel_message_to_raw_event`): Slack has no mention trigger, so "was this person actually addressed" is decided in our code. Your own messages, joins/leaves/topic edits, and `@channel`/`@here`/`@everyone` broadcasts are dropped. A channel message counts only if you were @-mentioned or it is a reply in a thread you posted in (needs `identity.slack_user_id`, resolved at connect).

**Deterministic (no model):**
| Signal | Category | Why |
|---|---|---|
| `slack_bot_noise` (a bot message, not a failure) | **Later** | Automated chatter. |

**LLM within a band:**
| Signal | Band (floor → ceiling) | Tag |
|---|---|---|
| `slack_dm` (a 1:1 direct message) | Can wait → Urgent | reply |
| `slack_mention` (you were @-mentioned in a channel) | Can wait → Urgent | reply |
| `slack_thread_reply` (reply in your thread) | Can wait → Urgent | reply |
| `slack_bot_failure` (a bot posting a failure report) | Can wait → Urgent | alert |

**Slack Later** (Vicky's call 2026-07-26: must not read empty) = the **top 100 recent Slack messages** you are involved in over the last 30 days, minus what's on Home, with a "latest 100" heading. **Your own messages are excluded** (self-DM reminders do not surface). Today the backfill is `is:dm` only (`slack_service.py:161-204`), which is why it read empty — the only inbound DM was elevated to Home and the rest were self-DMs. The fix broadens the backfill query (a single `search.messages`, to stay within Slack's hardest rate limit) so recent DMs and channel activity you are part of populate Later. Channel *mentions* still also arrive on the live webhook and go to Home.

### 3.4 Linear — fully deterministic, no model, ever

Recognition (`linear.issue_to_raw_event`): one signal, `linear`, for every open assigned issue. **Priority is ignored.** Completed/cancelled issues are dropped.

**Deterministic tier by due date** (`tier_bands._linear_tier`, in the user's timezone):
| Condition | Category |
|---|---|
| Completed / cancelled / done | dropped (not shown) |
| No due date | **Can wait** |
| Due date **is today** | **By EOD** |
| Due date **in the past**, any status except completed/done | **Urgent** |
| Due date in the future | **Can wait** (becomes By EOD on the day, Urgent once overdue) |

Priority and workflow state (backlog/in-progress/todo) do **not** change the tier — only the due date does. The one deterministic reason shown: "Overdue since 24 Jul" (overdue) / "Due today" (today).

**Linear Later** = `assigned_to_me` minus Home. Since every open assigned issue is elevated to Home (Can wait or Urgent, never dropped), Linear Later is empty for issues — that part is correct.

**Linear comments/mentions (to add, Vicky's call 2026-07-26).** Today Linear surfaces only assigned *issues*; a comment or @-mention on your issue is not fetched. These carry prose (someone is asking you something), so they are **LLM-in-a-band** (`Can wait → Urgent`, tag reply), like a Slack mention. They need either polling (a Linear comments query on your issues per refresh) or a real-time trigger (below).

### 3.5 Google Calendar — fully deterministic, no model, ever

Recognition (`calendar.event_to_raw_event` / `starting_soon_to_raw_event`): tier is set at read time from how close the meeting is (`tier_bands._calendar_tier`), not by the model. Passed meetings are dropped. Calendar is **never in Later** (a meeting is not a "did not need you" pile).

**Deterministic tier by proximity:**
| Signal | Category | Why |
|---|---|---|
| `calendar_invite` (you have not RSVP'd, `needsAction`) | Urgent within 1h of start, else **By EOD** | Wants your answer. Tag: rsvp. Kept regardless of day. |
| `calendar_meeting` (accepted, on your day) | Urgent within 1h of start, else **By EOD** | On your day. |
| `calendar_starting` (starting-soon trigger) | **Urgent** | Minutes out; cannot be done later. |
| `calendar_changed` | By EOD | A change to a meeting on your day. |
| `calendar_cancelled` | **Later** (dropped) | Nothing to do. |

(Known gap being fixed in the UX plan: the "on your day" window is currently 18h rolling, so a next-day meeting can leak in; the fix uses the user's calendar day.)

### 3.6 Google Docs (delivered via Gmail notifications)

Recognition (`google_docs.docs_notification_to_raw_event`): Composio has no Docs comment/mention event, so these arrive as Gmail notifications from `comments-noreply@docs.google.com` (mention/comment) or `drive-shares-noreply@google.com` (share). Anything from another sender is ignored, not mis-filed.

**Deterministic (no model):**
| Signal | Category | Why |
|---|---|---|
| `docs_edited` | **Later** | A doc was edited; no action asked. |

**LLM within a band:**
| Signal | Band (floor → ceiling) | Tag |
|---|---|---|
| `docs_mention` | Can wait → Urgent | comment |
| `docs_comment` | Can wait → Urgent | comment |
| `docs_share` | Can wait → Urgent | fyi |

---

## 4. How Later is populated (the selection logic)

Later is **live and stored nowhere** (`services/later.py`). Per connected source, per open:

1. Fetch the source's current set (Gmail unread, Slack DMs, Linear assigned, GitHub notifications, Docs mentions). **Calendar is excluded.**
2. Drop any `source_ref` already on Home (`on_home` exclusion) — Later is the complement of Home.
3. Cap at **200 rows per source**, newest first, streamed in batches.
4. No model runs. `LaterRow` has no tier; its summary is the first line of the body, truncated to 140 chars.

Consequence, stated plainly: a source's Later is only non-empty when it produces items that do *not* get elevated to Home. Gmail (narrow actionable query vs full unread) and GitHub (noise notifications) do; Linear and Slack (everything they surface is elevated) do not.

---

## 5. Volume caps per source (what the model sees, and the rest)

The model never classifies a source's whole firehose. Caps:

| Source | Ingested to Home (model set) | Cap | Later (live, no model) |
|---|---|---|---|
| Gmail | actionable unread, non-promotional | **100 / refresh** | up to 400 unread, 200 shown |
| GitHub | notifications | **50 / refresh** (`_PAGE_SIZE`) | noise notifications, 200 shown |
| Slack | DMs (backfill) + live channel mentions | search count **100** | DMs only, 200 shown |
| Linear | all assigned issues | paged, up to **500** (20×25), deterministic | empty by design |
| Calendar | day-window meetings + invites | ~50 events | n/a (excluded) |
| Docs | mention/share notifications | via Gmail search | 200 shown |

Classification pass (`services/classifier.py`): batches of **20**, a per-pass ceiling of **200 items** (`daily_budget`), and on the synchronous connect/refresh path a **20-second wall-clock budget** (`classify_budget`). Anything past the budget stays **held** (not shown) and is classified on the next pass. The count still owed is `RefreshResult.held` — this is the "we classified N, M still pending" number the syncing UX should surface.

---

## 6. Real-time delivery (webhook triggers) per source

Triggers are provisioned on connect (`services/triggers.py`). What arrives in real-time vs poll-only:

| Source | Trigger created on connect | Delivery |
|---|---|---|
| GitHub | `GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER` | Assigned issues push in real-time; review/mention/comment come on the next refresh poll. |
| Slack | `SLACK_DIRECT_MESSAGE_RECEIVED`, `SLACK_CHANNEL_MESSAGE_RECEIVED` | DMs + channel mentions push in real-time. |
| Gmail | `GMAIL_NEW_GMAIL_MESSAGE` | New mail pushes (also carries Google Docs mention/comment/share). |
| Calendar | `GOOGLECALENDAR_EVENT_STARTING_SOON_TRIGGER` | Starting-soon pushes. |
| **Linear** | **none today.** Native triggers exist but **all require `team_id`** (verified 2026-07-26). **LOCKED fix:** at connect, `LINEAR_LIST_LINEAR_TEAMS` (verified working — returns the user's teams, e.g. "Agentiwise") and provision one trigger per team: `LINEAR_ISSUE_CREATED_TRIGGER` + `LINEAR_COMMENT_EVENT_TRIGGER`. Optional backstop: sniff Linear notification emails via Gmail. | poll-only → real-time after the fix |
| **Google Docs → Google Drive** | **none today** (rides Gmail). **LOCKED fix (Vicky's call 2026-07-26): replace the Google Docs integration with a Google Drive connection.** `GOOGLEDRIVE_COMMENT_ADDED_TRIGGER` (verified: *"Triggers when a new comment is added to Google Docs, Sheets, or Slides"*, no required config, names the file) + `GOOGLEDRIVE_FILE_SHARED_PERMISSIONS_ADDED` give native comments/mentions/shares. Drive also lists the docs. Gmail sniffing stays as a redundant fallback. | Gmail-only → native real-time via Drive |

So today only **GitHub, Slack, Gmail, Calendar** create their own triggers; **Linear** (per-team provisioning, verified feasible) and **Google Drive** (replacing the Docs-via-Gmail source) are being upgraded to native real-time.

## 7. Known gaps against this model (to fix)

1. **Model-rated-noise stays on Home.** A `gmail_message` the model rates noise is stored on Home at noise tier rather than falling to Later, because it was ingested (`needs_llm`) and is therefore excluded from Later's live view. To keep the four categories clean, an item the model settles as noise should route to Later, not linger on Home. (Small band/read-time change.)
2. **Later SSE 401.** The Later stream uses a possibly-stale access token with no refresh/retry, so it intermittently 401s and shows empty for *every* source. This is the real "Later shows nothing" bug (distinct from Slack/Linear being empty by design). Fixed in the UX phase.
3. **Calendar next-day leak** (18h window) — fixed in the UX plan.
