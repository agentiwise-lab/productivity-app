# Product Brief: Unified AI Work Feed

**Date:** 2026-07-22
**Status:** Draft vision. Companion to [product-research.md](product-research.md), which grounds these choices in verified evidence.

## The problem

Professionals live across too many surfaces: Slack, Linear/Jira/Notion, GitHub, Gmail, and more. Each has its own inbox, its own notifications, and its own app to open. The result is constant context-switching and no single answer to the only question that matters each morning: **"what actually needs me today?"** Existing tools either aggregate one surface well (email-only AI triage) or plan a day from a desktop (task planners), but none give a mobile, AI-triaged, cross-tool view of what needs your action, where you can act without leaving the app.

## The user

Start with the person whose whole workday already lives in **GitHub + Linear + Slack**: developers, engineering managers, and technical founders. They feel the fragmentation most, they trust mobile-first tools, and (importantly) their core tools are the ones that are cheapest and fastest to integrate. This is not a role-locked product: anyone should be able to connect their tools, choose which channels/projects/senders matter, and get a feed tuned to them. The technical wedge is a starting point, not the ceiling.

## The core loop

1. **Connect** the tools where you work (GitHub and Linear first; Slack and Gmail next).
2. **Ingest** events from each (mentions, review requests, assignments, due dates, replies-needed).
3. **Classify** each item by action type: **Reply / Review / Approve / Decide / FYI**.
4. **Prioritize** into a ranked feed using deadline, who is blocked on you, sender importance, thread age, and your own rules.
5. **Act** from the feed itself: reply to the Slack thread, approve or comment on the PR, respond on the Linear issue. No app-hopping.
6. **Learn** from what you open, reply to, snooze, and dismiss, and retune.

## What it is / what it is not

| It is | It is not |
|---|---|
| A triage surface: "what needs me today" | A conventional to-do list |
| A ranked, action-typed feed | An Instagram-style visual/social feed |
| Cross-tool, mobile-first | A desktop planner or single-tool inbox |
| Act-from-feed (reply/approve/decide) | A read-only notification aggregator |

## Scope

**MVP:** GitHub + Linear. Action-typed, priority-ranked feed. In-app actions (approve/comment a PR, respond on a Linear issue). Customization: priority repos/projects, VIP senders, mute rules. Morning + afternoon batching with immediate surfacing for urgent items.

**Next:** Slack (gated by Marketplace approval + rate limits, so it follows once there is install traction), then Gmail (gated by a recurring security audit, so it comes last).

**Later:** Jira, Notion, and eventually personal surfaces (for example WhatsApp) once the professional core is proven.

## Why now / why us

The proven AI-triage pattern (auto-surface what needs you, batch the rest) is loved but locked to email. The cross-tool products stop at aggregation or desktop planning. The gap is a mobile-first, AI-triaged, act-from-feed layer across professional tools. The moat is partly the triage quality and partly the integration gauntlet itself (Slack Marketplace, Gmail security audit) that deters most builders from going cross-tool. See the research for the full competitive and feasibility picture.

## The first thing to build

The thinnest end-to-end slice, GitHub only: event in → classified and ranked → shown in a mobile feed → one action back to GitHub → pushed to the device. Prove that spine works before adding any breadth. Detail in [product-research.md](product-research.md) Section 8.3.
