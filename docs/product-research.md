# Product Research: A Unified AI Work Feed

Working title: TBD. Referred to below as "the product."

**Date:** 2026-07-22
**Status:** Foundation research. Findings below are split into three tiers: **Verified** (confirmed against primary sources through adversarial multi-vote checking), **Supporting** (from fetched sources but not put through the full verification pass, or from secondary sources), and **Open / Refuted** (things the research could not confirm, or actively knocked down). Do not build the roadmap on anything outside the Verified tier without re-confirming it.

**How this was produced:** a fan-out research pass across six angles (competitive map, AI triage mechanics, integration/compliance feasibility, per-tool notification taxonomy, market/pricing, and a contrarian "why incumbents miss it" angle). 26 sources fetched, 116 candidate claims extracted, top 25 put through 3-vote adversarial verification (a claim needed 2 of 3 refutes to be killed). 22 confirmed, 3 refuted. The Verified tier reflects those 22.

---

## 1. The concept in one paragraph

A mobile-first (iOS + Android) app that connects the tools where professionals actually work (starting with Slack, Linear, GitHub, Gmail) and produces a single daily **action feed**: "here is what needs you today," with each item classified by action type (Reply / Review / Approve / Decide / FYI) and ranked by priority (deadline, who is blocked on you, sender importance, thread age, plus user-defined rules). The user acts from inside the feed (reply to a Slack thread, approve or comment on a PR, respond on a Linear issue) without opening each app. It is deliberately **not** a conventional to-do list and not a social/visual feed. It is a triage surface for cross-tool attention.

---

## 2. Competitive landscape

### 2.1 The map

| Category | Examples | What they do | Gap vs this product |
|---|---|---|---|
| Daily planners / unified task inboxes | Akiflow, Sunsama, Motion, Morgen, Reclaim, Routine, Amie | Pull tasks/events into a planner, time-block the day | Desktop-first, planning-centric (not triage-of-live-events), premium priced |
| Unified team inboxes / chat aggregators | Missive, Spike, Twist | Shared inbox over email/chat | Team-collaboration framing, not personal cross-tool triage; limited AI ranking |
| AI email triage | Cora, Shortwave, Superhuman, Fyxer, Serif | AI sorts/surfaces/auto-archives email | Single tool (email only) |
| Enterprise work assistants / search | Glean, Dust, Moveworks, Leena | Unified retrieval + Q&A over company data | Strong on search/answers, weaker on agentic action; enterprise sales motion, not mobile consumer |
| Multi-account desktop shells | Rambox, Shift, Station, Franz | Wrap many web apps in one window | No AI, no triage, just tab consolidation; desktop only |

> **Coverage caveat:** only four competitors survived the full verification pass (Akiflow and Sunsama as planners; Cora and Shortwave as AI-triage). Specifics on Motion, Morgen, Reclaim, Missive, Spike, Superhuman, Glean, Dust, Moveworks, and the desktop shells are **from search snippets, not verified**. Treat the table as a validated core plus an unvalidated periphery. See Open Questions.

### 2.2 Closest comparable: Akiflow (still meaningfully different)

Akiflow is the closest thing to this concept in shape: a keyboard-driven "command center" where tasks from Slack, Gmail, and Notion land automatically (star an email, get @-tagged, and it appears). **[Supporting: blog.saner.ai]** The differences that leave the lane open:

- **Desktop-first with weak mobile.** *[Verified]* Both Sunsama and Akiflow are desktop-primary. Sunsama's own positioning describes its mobile app as "a companion, not a replacement," and Akiflow shipped a 2026 changelog titled "Mobile Redesign and Sync Improvements," confirming its mobile sync/loading problems were real rather than marketing. ([saner.ai comparison](https://blog.saner.ai/sunsama-vs-akiflow/))
- **Planner, not triage.** Akiflow/Sunsama are built to *plan and time-block a day*, not to answer "what across all my tools needs a reply/review/decision right now." The framing difference is the product.
- **Premium price.** *[Verified]* Sunsama is a single Pro plan at **$22/month billed monthly, $17/month billed yearly**. ([sunsama.com/pricing](https://www.sunsama.com/pricing))

### 2.3 Closest comparable on the AI side: Cora and Shortwave (single-tool)

These validate the **triage-to-attention** model the product depends on, but only for email:

- **Cora** *[Verified]* auto-archives everything that does not need attention, leaving only human emails that require a response (a clear-to-empty model, explicitly not a to-do list). It fights notification fatigue by surfacing time-sensitive email immediately while batching non-urgent mail into a summarized brief sent twice a day (morning and afternoon), not item-by-item. ([Every: Introducing Cora](https://every.to/p/introducing-cora-manage-your-inbox-with-ai))
- **Shortwave** *[Verified]* uses AI to split the inbox into auto-labeled tabs, offers an "Organize my inbox" action that analyzes up to the 100 most recent threads and suggests bulk actions, and supports agentic natural-language filters (rules generated from a description, plus web browsing) rather than static keyword rules. ([Zapier](https://zapier.com/blog/shortwave-vs-superhuman/), [Shortwave docs](https://shortwave.com/docs/guides/ai-assistant/))

The takeaway: the "AI decides what deserves your attention and batches the rest" pattern is proven and loved, but nobody in this verified set does it **across** Slack + GitHub + Linear + Gmail on **mobile**. That is the open lane.

---

## 3. White space and differentiation

**The genuine gap:** a mobile-first, AI-triaged, act-from-feed, cross-tool "what needs me today" surface. The proven triage products are single-tool (email). The cross-tool products are either desktop planners (Akiflow/Sunsama) or enterprise search layers (Glean/Dust) that are strong on finding information and weaker on the action that comes after. **[Supporting: dust.tt]** Glean is described as "a unified retrieval layer, strong on search and Q&A but weaker on agentic action"; if the bottleneck is what happens *after* you find the info (validate, decide, act), that is the unserved need. ([Dust on Glean agents](https://dust.tt/blog/glean-agents))

**Why incumbents have not nailed it:**
1. **Single-tool focus** for the AI-triage winners (email only) is a product choice, not a temporary state.
2. **Desktop/planning DNA** for the planners: retrofitting a mobile triage feed onto a time-blocking planner is a different product.
3. **The integration gauntlet** (Section 6) is a real deterrent: cross-tool means eating Slack's Marketplace + rate-limit regime and Gmail's recurring security audit. Most teams pick one tool to avoid this.

**What makes it defensibly different (in priority order):**
1. **Mobile-first triage** is the sharpest and most defensible axis. The closest comparables are explicitly weak here. *[Verified]*
2. **Cross-tool action, not just aggregation.** Reply/approve/decide from the feed. This is where enterprise search stops short. *[Supporting]*
3. **AI prioritization** is real but the *least* defensible axis on its own, because the incumbents' current AI capabilities are unresolved (see Refuted item 3). Lead with mobile + cross-tool + action; treat AI quality as the retention engine, not the headline moat.

---

## 4. Notification and action taxonomy

### 4.1 Per-integration event sources

**GitHub** *[Verified, primary docs]* is the richest ready-made classifier. Two complementary streams:

- **Notifications API** tags every item with a `reason` field (currently **15 defined values**), several mapping almost 1:1 onto the action taxonomy: `review_requested`, `assign`, `mention`, `team_mention`, `approval_requested`, `ci_activity`, and others. This inbox is **poll-based** (returns `304 Not Modified` via `Last-Modified`; cadence set by the `X-Poll-Interval` header) with **no webhook equivalent**, so a server-side poller is required. ([GitHub REST: notifications](https://docs.github.com/en/rest/activity/notifications))
- **Webhooks** for real-time richness: the `pull_request` event fires on `assigned`, `opened`, `closed`, `review_requested`, `review_request_removed`, `ready_for_review` (Review and FYI items from one stream). Review submissions come from the separate `pull_request_review` event (`submitted`/`edited`/`dismissed`), and CI status from `check_run` / `check_suite` / `workflow_run`. ([GitHub webhook events](https://docs.github.com/en/webhooks/webhook-events-and-payloads))

**Slack** *[Verified, primary docs]* via the Events API (push, not poll): DMs, `@mentions`, thread replies. Two hard bounds: event access is **scope-gated** (you only get event types your OAuth scopes cover), and you only receive events **the authorizing user can already see** in their workspace. ([Slack Events API](https://docs.slack.dev/apis/events-api/))

**Linear** *[Supporting: secondary blog; confirm against Linear's primary docs]* via GraphQL API + webhooks. Webhook resource types include Issue, Comment, Project, Cycle, IssueLabel, Reaction, IssueAttachment, ProjectUpdate, Document, Customer, each firing on create/update/remove. Maps to: assigned, mentioned (via Comment), status change (Issue update), due date. ([Linear webhooks guide](https://inventivehq.com/blog/linear-webhooks-guide))

**Gmail** *[Verified, primary docs]* via push (see Section 6 for the cost): reply-needed and important senders. Note the push payload only carries `{emailAddress, historyId}`, so surfacing the actual message requires a follow-up `history.list` call. ([Gmail push](https://developers.google.com/workspace/gmail/api/guides/push))

### 4.2 Proposed action-type taxonomy

A clean, tool-agnostic set that every event maps into:

| Action type | Meaning | Example sources |
|---|---|---|
| **Reply** | Someone is waiting on your words | Slack DM/mention/thread reply, Gmail reply-needed, Linear comment mention |
| **Review** | You are asked to review work | GitHub `review_requested`, PR `ready_for_review` |
| **Approve** | A gated decision waits on you | GitHub `approval_requested`, deploy/merge approvals |
| **Decide** | An open question needs your call (no single obvious owner) | Slack thread posing a question to you, Linear issue awaiting triage |
| **FYI** | Context you may want, no action required | CI passed, status changes, cc'd threads (batched, never interruptive) |

### 4.3 Priority signals for ranking

Rank each item by a composite of: **deadline / SLA proximity**, **is-someone-blocked-on-you** (highest weight: your inaction stalls others), **sender/requester importance** (manager, key client, repo owner), **thread age / staleness**, **explicit user rules** (priority channels, muted repos, VIP senders), and **action type weight** (Approve/Reply generally outrank FYI). Section 5 turns this into a concrete scoring design.

---

## 5. AI prioritization and feed-ranking model

### 5.1 What the best triage products actually do

- **Cora** *[Verified]*: binary attention decision (needs-you vs auto-archive) plus urgency-splitting (immediate for time-sensitive, twice-daily brief for the rest). ([Every](https://every.to/p/introducing-cora-manage-your-inbox-with-ai))
- **Shortwave** *[Verified]*: AI labeling into tabs + bulk-action suggestions over recent threads + natural-language (not keyword) rules. ([Zapier](https://zapier.com/blog/shortwave-vs-superhuman/))
- **Superhuman** *[Supporting: blog]*: AI prioritization that learns from user feedback and scans incoming messages to decide what to surface. ([review](https://virtualworkforce.ai/cora-vs-superhuman/))
- **Personalized multi-agent triage** *[Supporting: arXiv primary]*: a design using an "analyser" LLM that builds a per-user profile from past notification-interaction history, plus "rater" LLMs that classify incoming notifications against that profile, reported **81.5% urgency-classification accuracy** and cut the false-negative rate to 0.381, versus a non-personalized base model at 0.670 accuracy / ~0.586 FNR. The signal to take: personalization from observed behavior materially beats a static classifier. ([arXiv 2508.19622](https://arxiv.org/pdf/2508.19622))

### 5.2 Recommended design

*[Recommendation grounded in Verified + Supporting evidence]*

1. **Two-axis scoring, not one urgency number.** Score each item on **confidence** (is this genuinely something that needs the user) and **severity/impact** separately, then combine into a composite priority. This mirrors established alerting practice and prevents "loud but low-impact" items from dominating. ([alerting/triage practice](https://zylos.ai/zh/research/2026-04-23-agent-notification-intelligence-smart-alerting-triage/)) *[Supporting: secondary, corroborated by Google SRE guidance that "every page should be actionable."]*
2. **Actionability gate.** If the user cannot act on an item, log it, do not interrupt with it. This is the single biggest defense against fatigue.
3. **Urgency-splitting + batching (Cora pattern).** Truly urgent items surface immediately; everything else rolls into scheduled digests (for example a morning feed and an afternoon feed). Never a live item-by-item stream. *[Verified pattern]*
4. **Personalize from behavior.** Learn from what the user opens, replies to, snoozes, and dismisses to tune per-user weights and the confidence model over time. *[Supporting: arXiv]*
5. **Classification pipeline:** deterministic pre-filter (map raw events to action types using the GitHub `reason` field, Slack event type, etc., which is free and reliable) → LLM classifier only for the ambiguous residue (Decide vs FYI, Reply-needed detection in Gmail/Slack) → composite score → feed assembly. Keep the LLM off the hot path where a rule already answers the question, for cost and latency.

---

## 6. Integration and API feasibility (operator-critical)

This is where the real cost, sequencing, and moat live. Ranked from easiest to hardest to onboard.

### 6.1 GitHub: cleanest, lead here *[Verified]*
- `reason` field maps almost 1:1 to the taxonomy; webhooks cover the rest.
- Fine-grained personal access tokens; no marketplace gate; no recurring security audit.
- One caveat: the personal Notifications inbox is **poll-only** (respect `X-Poll-Interval`), so you run a per-user poller alongside webhooks.
- **Implication:** fastest path to a working end-to-end slice. Lead integration.

### 6.2 Linear: developer-friendly, second *[Supporting]*
- GraphQL API + webhooks, clean resource/action model, no heavy compliance regime.
- Natural pairing with GitHub for the developer/eng-manager persona.
- **Implication:** second integration; confirm rate limits and webhook setup against Linear's primary docs before committing.

### 6.3 Slack: powerful but gated, third *[Verified]*
- **Events API is push-based** and the right model for DMs/mentions/threads. ([Slack](https://docs.slack.dev/apis/events-api/))
- **Rate-limit trap:** non-Marketplace apps are throttled to **1 request/minute and max 15 objects/request** on `conversations.history` and `conversations.replies` (effective for new apps May 2025, extended to all existing non-Marketplace apps Sept 2, 2025). Bulk reading of message history via a non-Marketplace app is effectively unworkable. ([Slack changelog](https://api.slack.com/changelog/2025-05-terms-rate-limit-update-and-faq))
- **Marketplace approval is a multi-month process:** Preliminary review up to 10 business days, then Functional review up to **10 weeks** for new apps (6 weeks for updates). ([Marketplace review guide](https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/))
- **Chicken-and-egg pre-req:** before you can even submit, the app must be installed on **≥5 active workspaces** (used in the last 28 days; reduced from 10 to 5 in Aug 2025). You need direct-install traction first.
- **Design implication:** lean on **Events API push** (real-time, event-driven) and avoid history/replies bulk reads, so the 1-req/min throttle does not bite. Do **not** assume Marketplace approval lifts the throttle (see Refuted item 1).

### 6.4 Gmail: highest barrier, last *[Verified]*
- **Restricted scopes trigger a mandatory CASA security assessment** by Google-empanelled assessors, which must be **re-completed at least every 12 months**. This is a recurring annual compliance cost and the clearest moat in the stack, but it is a cost you take on, not a free one. ([Google restricted-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification))
- **Push is indirect:** requires Google Cloud Pub/Sub (a topic + subscription you own) as an intermediary.
- **`watch()` subscriptions expire** and must be renewed at least every 7 days per user (daily recommended), so you run a scheduled per-user renewal job.
- **Payload is thin:** push delivers only `{emailAddress, historyId}`; you then call `history.list` to learn what changed. ([Gmail push guide](https://developers.google.com/workspace/gmail/api/guides/push))
- **Implication:** sequence Gmail **last**, once traction justifies the audit cost and operational overhead.

### 6.5 Mobile push (APNs/FCM)
Standard but required plumbing: your backend fans verified, ranked feed items out to devices via APNs (iOS) and FCM (Android). This is table stakes and not a differentiator.

### 6.6 Sequencing summary
**GitHub → Linear → Slack → Gmail.** The order is dictated by compliance/rate-limit cost, not by user value. The two highest-value tools for many users (Slack, Gmail) are the two most expensive to onboard, which is exactly why this is defensible if you get through it.

---

## 7. Monetization and market

- **Comparable pricing** *[Verified]*: Sunsama at $22/mo (monthly) / $17/mo (yearly) shows a premium daily-productivity tool sustains ~$17–22/user/month. ([sunsama.com/pricing](https://www.sunsama.com/pricing)) A cross-tool triage feed can credibly target a similar prosumer price band.
- **Market sizing: unresolved.** A specific shared-inbox market figure surfaced in research was **refuted** (see Refuted item 2). Do not cite a TAM number yet. Context-switching pain is real and well-documented qualitatively, but the load-bearing statistics came from blog sources that were not verified; source them to primary studies before using them in a deck.

---

## 8. Recommendation

### 8.1 Sharpest wedge / positioning
Lead with the **developer / engineering-manager / technical-founder** persona. Their entire daily action surface is **GitHub + Linear + Slack**, which is exactly the low-compliance-cost end of the integration stack (no Gmail audit required on day one). They feel cross-tool fragmentation acutely, they are reachable through community distribution, and they trust mobile-first tools. Positioning: **"One mobile feed of everything that needs you across GitHub, Linear, and Slack. Triaged by AI, actionable in one tap."** Expand to Gmail, Jira, and Notion once the wedge is working.

### 8.2 MVP scope
- Integrations: **GitHub + Linear** (add Slack once you have enough installs to approach the ≥5-workspace Marketplace threshold).
- Feed: action-typed (Reply / Review / Approve / Decide / FYI), composite-scored, with morning/afternoon batching and immediate surfacing for urgent items.
- Actions in-app: approve/comment a PR, respond on a Linear issue.
- Customization: priority repos/projects, VIP senders, mute rules.

### 8.3 Thinnest end-to-end tracer slice (build this first)
One path through every layer, GitHub only:

> Poll the GitHub Notifications API + subscribe to the `pull_request` webhook → classify each event into an action type using the `reason`/action field → assign a composite priority score → render a single ranked mobile feed → let the user **approve or comment on a PR from the feed** via the GitHub API, and push the item to the device via APNs/FCM.

If that one slice works end to end (event in, ranked feed out, action back to GitHub, push to phone), every other integration is a variation on the same spine. This is the tracer bullet; do not build breadth until it is proven.

### 8.4 Top risks
1. **Slack gate.** The 1-req/min throttle + multi-month Marketplace review + ≥5-workspace pre-req can stall the highest-value chat integration. Mitigate by designing around Events API push and treating Slack as a post-traction integration.
2. **Gmail audit cost.** Recurring annual CASA assessment; magnitude unquantified (Open Question). Sequence last.
3. **Triage quality.** Bad prioritization reproduces the notification fatigue you are selling against. The two-axis score + actionability gate + batching are the defense, and they must be right early.
4. **Write access raises the bar.** Acting from the feed (reply, approve) needs write scopes, which increases OAuth review scrutiny and the user-trust bar. Budget for it.
5. **Differentiation via "AI" alone is thin.** Incumbent planners' current AI capabilities are unresolved (Refuted item 3), so anchor the moat on mobile-first cross-tool action, with AI quality as the retention driver rather than the headline.

---

## 9. Open questions (research could not resolve these)

1. **Does passing Slack Marketplace review exempt an approved app from the 1-req/min non-Marketplace throttle on `conversations.history`/`replies`?** The "yes" assumption was refuted. This needs primary confirmation from Slack because it materially changes whether Slack can be a real-time source at scale.
2. **What is the actual dollar cost and calendar timeline of a CASA Tier 2/Tier 3 assessment for Gmail restricted scopes** (initial + annual recert)? The requirement is confirmed; the magnitude is not.
3. **Credible market sizing / willingness-to-pay for a cross-tool "action feed" specifically.** The one surviving market figure was refuted.
4. **How do Motion / Akiflow / Sunsama actually implement AI prioritization today?** The claim that they do no true AI prioritization was refuted, so the sharpness of the "we have better AI" differentiation is unconfirmed.

---

## 10. Refuted claims (do not build on these)

1. **"Marketplace approval exempts an app from the Slack rate-limit reduction."** Refuted 0-3. Do not treat Marketplace approval as a rate-limit moat without primary confirmation. ([source](https://api.slack.com/changelog/2025-05-terms-rate-limit-update-and-faq))
2. **"Shared inbox software market is $1.89B (2025) growing to $5.5B by 2035 at 11.2% CAGR."** Refuted 0-3. Treat market sizing as unresolved.
3. **"Neither Sunsama nor Akiflow does true AI prioritization/auto-scheduling."** Refuted 0-3. Their AI capabilities are unresolved, not absent.

---

## 11. Sources

Primary (vendor/official docs and first-party):
- GitHub REST notifications: https://docs.github.com/en/rest/activity/notifications
- GitHub webhook events: https://docs.github.com/en/webhooks/webhook-events-and-payloads
- Slack Events API: https://docs.slack.dev/apis/events-api/
- Slack rate-limit changelog + FAQ (2025-05): https://api.slack.com/changelog/2025-05-terms-rate-limit-update-and-faq
- Slack Marketplace review guide: https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/
- Google restricted-scope verification (CASA): https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- Gmail API push guide: https://developers.google.com/workspace/gmail/api/guides/push
- Sunsama pricing: https://www.sunsama.com/pricing
- Every: Introducing Cora: https://every.to/p/introducing-cora-manage-your-inbox-with-ai
- Shortwave AI assistant docs: https://shortwave.com/docs/guides/ai-assistant/
- arXiv 2508.19622 (personalized notification triage): https://arxiv.org/pdf/2508.19622

Secondary / supporting (blogs, comparisons, editorial):
- Sunsama vs Akiflow: https://blog.saner.ai/sunsama-vs-akiflow/
- Zapier: Shortwave vs Superhuman: https://zapier.com/blog/shortwave-vs-superhuman/
- Cora vs Superhuman: https://virtualworkforce.ai/cora-vs-superhuman/
- Alerting/triage practice: https://zylos.ai/zh/research/2026-04-23-agent-notification-intelligence-smart-alerting-triage/
- Linear webhooks guide: https://inventivehq.com/blog/linear-webhooks-guide
- Dust on Glean agents: https://dust.tt/blog/glean-agents

_Verification note: 22 of 25 tested claims confirmed via 3-vote adversarial checking; 3 refuted (Section 10). Anything marked Supporting was not put through that full pass. Vendor policies (Slack rate limits, Marketplace thresholds, Gmail CASA cadence) are current as of 2026-07-22 and subject to change._
