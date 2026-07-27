# Positioning

**Date:** 2026-07-27
**Status:** Decided. Supersedes the ICP and framing sections of [product-brief.md](product-brief.md).
**Companion docs:** [product-research.md](product-research.md) (competitive evidence), [capabilities.md](capabilities.md) (integration surface), [classification-bible.md](classification-bible.md) (how items are categorised).

This doc fixes who the product is for, what it promises, what it measures, and where AI is and is not allowed to go. Everything downstream (name, onboarding, pricing, roadmap order) resolves from here.

---

## 1. What the product is

A single daily surface that answers two questions across every tool a professional works in: **what needs me, and did anything slip.**

It is not a notification centre. The OS already owns that, and a better-sorted notification list is not a product. It is an **activity and progress layer**: the feed is the working surface, and the daily bookend (a morning plan and an evening report) is what the user actually comes back for.

The distinction matters because it decides what gets built. A notification centre is judged on completeness of delivery. An activity layer is judged on whether the user ends the day knowing where it went and confident nothing was dropped.

---

## 2. The promise

> **Nothing that needed you slipped.**

Closure, not speed and not volume. The user hands over responsibility for noticing, and the product guarantees the noticing.

Two supporting claims sit underneath the headline and are never the headline:

- **How long people waited on you.** Latency on the items that mattered.
- **What your day was actually made of.** How much of what you engaged with was work that needed you, versus work that did not.

### Why closure and not the other two

- It is the direct expression of the job. Users are not asking to be faster, they are asking not to be caught out.
- It is the cheapest of the three to measure honestly (see section 6). It is a state check, not a duration, so it survives the observation limits the current architecture imposes.
- It positions the product as insurance rather than a scoreboard. Insurance retains. Scoreboards get gamed and then abandoned.

The evening report reads, in this order: what arrived, what needed you, what is closed, and only then how long anyone waited.

---

## 3. The ICP

### The wedge: the bottleneck

The person **other people are blocked on**. Engineering manager, tech lead, technical founder, agency or consultancy owner.

Concretely:
- 6 to 60 person company, no EA and no chief of staff
- inbound arrives across five or more surfaces daily (Slack DMs, Gmail, calendar invites, doc comments, review requests, issue assignments)
- three to five hours a day in meetings, so their real working surface between meetings is a phone
- their failure mode is not "I forgot a task", it is "three people were stuck on me for six hours and I did not know"

### Why not the individual developer

The original brief led with a GitHub plus Linear developer wedge. That was chosen for integration convenience, not for pain, and it is the wrong first customer:

1. An IC developer lives in one or two tools. Cross-tool is the only differentiator, and it is worth nothing to someone who is not fragmented.
2. Lowest willingness to pay and highest churn of any segment for productivity tooling.
3. They are not the person being waited on. The whole ranking model is built around "someone is actively waiting on you", which describes a lead, not an IC.

Developers remain **users**. They are not the wedge.

### Reach versus wedge

The product serves any professional whose work arrives across many tools, technical or not. That is the reach. The wedge is one person, and the wedge decides onboarding defaults, the first integrations, the name, and the first hundred users.

Expansion path: the non-technical operator (consultant, PM, ops lead, agency owner) is a straightforward second, because the mechanics are identical. It is gated on the Microsoft stack, not on product work. See section 7.

### What this changes in positioning

Slack, Gmail and Calendar are the ICP's spine and lead the pitch. GitHub and Linear become "it also covers your engineering surface", which is the credibility differentiator against single-tool AI triage products, not the wedge.

---

## 4. Anti-goals

Each of these is a direction we have considered and rejected, with the reason, so they do not get relitigated every sprint.

| We do not build | Why |
|---|---|
| **An execution layer** (complete the Linear ticket, write the code) | Permanently second best at our own headline feature against companies spending billions on exactly this. The reason is competitive position, not compute cost. |
| **Autonomous send** (auto-reply, auto-archive, auto-RSVP) | The ICP is the person others depend on. One wrong outbound message to a client or a report is a professional incident, not a bug. A hundred correct auto-replies buy nothing; one wrong one ends the account. |
| **A chat tab** | A blank page. Blank pages have no daily habit, and we would be competing with Claude on Claude's ground for no reason. |
| **An MCP server for agent task visibility** | Considered and dropped. The person running an agent is watching it run, so visibility is not a need. And when a coding agent opens a PR or comments on an issue, the existing GitHub integration already surfaces it. The MCP would be a second, worse path to data we already have. |
| **Agentic pre-call research** (research the prospect before a discovery call) | That is a sales tool. Different buyer, different product, and it pulls toward the execution layer. |
| **A points currency with a redemption store** | Condescending to the buyer, a real per-user cost with no retention evidence, and it attaches motivation to the reward rather than the metric. See section 8. |

**The distinction that governs all of the above is not "agent or no agent". It is who presses send.** A drafting and synthesis system can be far more sophisticated than an autonomous one. The human being the commit step caps the downside at "the draft was bad" instead of "you sent a client something wrong."

---

## 5. AI policy

AI is what the product *is*, not a feature inside it. It is never a settings toggle and never a separate surface.

### Where AI earns its place

**1. Triage quality, and the personalisation underneath it.**
The band-clamp design (deterministic rules set a floor and ceiling, the model moves within them, per [classification-bible.md](classification-bible.md)) is correct and stays. What is missing is context. Today the CEO's one-line Slack DM and a vendor's one-line Slack DM are indistinguishable to the classifier. Two layers fix that:
- stated at onboarding: role, current responsibilities, top people
- learned from behaviour: who gets opened fast, who gets replied to, what always gets snoozed

The learned layer is the moat. Integrations can be copied in a quarter. Sixty days of one user's response patterns cannot.

**2. Cross-tool synthesis. This is the differentiated one.**
We are the only system holding all sources for one person at once. Claude does not know that the Slack DM from a colleague, the assigned Linear ticket, the PR sitting unreviewed for three days, and tomorrow's calendar invite are one piece of work with one person blocked at the centre. Every single-tool AI is structurally blind to this.

Synthesis, not autonomy, is the AI differentiator: recognising that N items across N tools are one thing, and saying so. It directly improves the plan, the report, and the pre-meeting card.

**3. Summaries good enough that the source does not need opening.**
The current 90-character line is a label, not a summary. For a long Slack thread or a PR diff, the win is the three lines needed to respond. Every time a user leaves to understand an item, they land in Slack and the session is over.

**4. Drafted replies, human sends.**
Reading is half the loop. The reason someone leaves is to respond. If the response is typed elsewhere, this is a read-only aggregator, which is the category that dies. Reply is available on Slack, Drive comments, Gmail, GitHub and Linear per [capabilities.md](capabilities.md).

**5. The daily bookend.** Morning plan and evening report. Two bounded calls per user per day.

### Per-source note

Reply-in-app is not equally valuable everywhere and we do not build one generic action layer.
- **Slack**: reply-in-app is high value. This is where the session can end in our app.
- **GitHub**: users will go to GitHub for real review work. Approve and comment are worth having; do not fight for the rest.
- **Gmail**: the mailbox is a database, not a conversation surface. The job here is **extraction** (the payment due, the contract, the decision buried in 400 unread), not reply.

### Cost shape

Classification and reports are bounded and predictable: hundreds of tokens per item, a couple of thousand per report, cached on content hash. Forecastable per user per month, which means priceable.

Agent loops are unbounded by construction, and the API bill is the smaller problem. The real cost is permissioning, undo, audit, error recovery and an eval harness. That is quarters of team time. **Opportunity cost is the argument, not the invoice.**

---

## 6. Measurement, and what the architecture actually permits

This section exists because an earlier version of this analysis assumed a scheduled 15-minute poll that **does not exist**. Anyone designing a metric here should read this before assuming a cadence.

### What the system actually does today

**There is no scheduled poller.** `prefect/` is empty. No cron, no APScheduler, nothing in `backend/` runs on a timer. Two paths bring data in:

- **Push.** `backend/services/triggers.py` provisions Composio trigger instances per source at connect, delivering to `POST /webhooks/composio`. Slack DM and channel messages are genuine real-time push; GitHub assigned-issue, Gmail new-message, Calendar starting-soon, Drive comment and share, and the Linear triggers are poll-type on Composio's side (GitHub is configured at `interval: 2`). `/feed/stream` is SSE and is a **notify** channel, not an ingest path.
- **Pull.** `SourceSync.refresh()` runs only when the client calls `POST /feed/refresh`, which is on app open or pull to refresh.

### The constraint this creates

**Every provisioned trigger is arrival-shaped. None is resolution-shaped.** There is no review-submitted, thread-replied, or issue-closed trigger anywhere. The push path gives T0 for free and gives nothing about T1.

Since the pull path only runs on app open, **the observation window for resolution is the user's app-open cadence, not a poll interval.** For a user who opens twice a day, which is precisely the habit the bookend is designed to create, every resolution falls into one of two windows. The better the habit loop works, the worse a latency metric gets.

Storage is the second constraint: `feed_actions` (migration `0010`) records only in-app action, keyed on `(user_id, source_ref)`. There is no `first_seen_at` or `resolved_at`, and everything else is Redis on a 24h TTL. Any latency exceeding a day is currently unmeasurable.

### Consequences for metric design

1. **Closure is the headline because it is a state check, not a duration.** It needs no timestamp precision and a twice-daily sweep is adequate. This is the main reason it beats latency as the headline.
2. **Latency is reported in hour buckets, never minutes**, and it is described as *how long the other person waited*, not how fast the user reacted. We observe resolution, not sighting.
3. **Not every item is scoreable.** An FYI, a shared doc, or a decision made verbally has no observable resolution. An item counts toward the metric **only if its source exposes an observable resolution event.** Everything else is excluded, never counted as a miss. Counting undetectable items as unresolved would tell a productive user they failed, which is a one-shot trust loss.
4. **"Attention leak" was retracted.** We cannot see where attention went; there is no time-on-task signal. The honest, observable version is composition of engagement: of what was resolved, what share was elevated versus Later.

### What measuring closure and latency requires

Three pieces, none of which exist yet:

1. **A durable lifecycle table**: `(user_id, source_ref, first_seen_at, tier_at_seen, resolved_at, resolved_via)`. Postgres, next to `feed_actions`, because the interesting spans exceed the Redis TTL.
2. **A batch resolution reader per source.** Must be one call per source per sweep, matched against open items locally. The naive per-item version is O(open items) per sweep and tool calls are the meter. The batch queries mostly exist already: GitHub `list_notifications(since=T)` plus read state, Gmail `is:read newer_than`, Linear `updatedAt > T`, one Slack `search.messages` for the user's own messages since T, Calendar `responseStatus` on the events list already pulled.
3. **A scheduler.** Per the stack rule, scheduled application jobs go to Prefect, and `prefect/` is empty. A sweep every 30 to 60 minutes, only for users with open tracked items, is sufficient for hour-bucketed metrics.

**Interim option:** arrival timestamps are already accurate to roughly two minutes from the triggers. The arrival half of the report can ship before the sweep exists, stated honestly as half the picture.

---

## 7. Integrations

**Every integration is a recurring per-user cost, not a one-time build cost.** Polling spend scales linearly per user per source, every day, whether or not the user opens the app. At a $15 to $25 price point this decides the margin. Integration breadth is a pricing decision. Gate the long tail behind a paid tier.

**Live today (6):** GitHub, Slack, Gmail, Google Calendar, Google Drive, Linear.

**Priority additions, in order:**

1. **Microsoft stack (Outlook, Teams).** The single largest gap and the unlock for the non-technical expansion. Outside startups, the professional is on Outlook and Teams, not Gmail and Slack. Composio exposes 286 Outlook tools.
2. **Notion** (has a comment trigger) and **Jira** (JQL polling) for the PM and non-technical operator.
3. **Asana or ClickUp**, one of them, for the agency and ops segment.
4. **Zoom or a transcript provider**, and only once the pre-meeting card exists.

**Hold everything else** until the six live sources are ranked well. More sources make clutter worse if triage is not excellent, and triage is what we are selling.

---

## 8. Gamification stance

Full design is a separate research track. What is decided here is the boundary, because it constrains what the score can be.

**The contradiction to avoid:** the product's thesis is "most of this does not deserve you." Points for clearing items say "clear more, earn more." Awarding points for replies and marks-as-read builds a machine that rewards engaging with clutter, and the most gamified user becomes the one answering sixty low-value messages. **Volume cleared is never the metric.**

**Decided:**
- No points currency, no redemption store, no external rewards. If a currency ever exists, the only thing worth redeeming is product value (AI credits, an extra integration), never external goods.
- Comparison is against the user's own recent baseline, not against other users.
- Streaks attach to a quality behaviour, never a volume one. "N days where nothing that needed you slipped" is worth defending; "N days of clearing the feed" is a chore.
- The evening report is itself the reward. It doubles as a receipt the user can reuse in their own weekly update, which is the organic loop.

**The scoring rule that makes it honest:** the score is computed from **source truth**, not from in-app actions. Users will keep acting in GitHub and Slack directly, and a score built on in-app action would tell a lead who reviewed nine PRs that they did nothing. That is an unrecoverable trust failure. In-app actions are a **precision and intent layer** on top: exact timestamps, plus the signals polling can never see (snooze, dismiss, not-for-me), which are what personalise the ranking.

Source truth makes the score honest. In-app makes the ranking personal. Both, in that order of dependency.

---

## 9. Build order

1. **Closure tracking**: the lifecycle table, the batch resolution readers, the Prefect sweep. Nothing else is credible without it.
2. **The evening report.** The receipt that makes the score trustworthy.
3. **The morning plan.** Completes the two-fixed-times habit loop, which is the retention mechanism.
4. **Reply from the app**, Slack first, so a session can end here instead of in Slack.
5. **User context at onboarding**, feeding the classifier.
6. **Cross-tool synthesis**, then the pre-meeting card on top of it.

Streaks and baselines come after there is a number worth defending.

---

## 10. The risk to hold in view

The product is only as good as the triage, and triage errors are unforgiving. If something is marked Urgent that was not, twice in a week, the user stops trusting the top of the feed. Once that trust is gone, the report and the score go with it, because they are derived from the same judgment. Everything here rests on one thing being excellent, which is why context and personalisation outrank every feature on the list, and why integrations seven through ten wait.

Second risk: clarity is a soft sell. "I see everything in one place" converts worse than "I saved four hours." The report and the score are the answer, which is why their honesty (section 6) is a commercial concern and not only an engineering one.

---

## 11. Open

- **The name.** Unblocked by this doc: the promise is closure and the ICP is the bottleneck, so the name should carry either the relief (nothing slips) or the role (the person others depend on).
- **Pricing tier boundaries**, specifically which integrations sit behind the paid tier given the per-user polling cost.
- **Gamification detail** beyond the boundary in section 8.
