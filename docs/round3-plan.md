# Round 3 plan — triage matrix, Google Docs, Later fixes

Date: 2026-07-26. Builds on [rca-round2.md](rca-round2.md). Three pieces: (1) redesign triage as a **data-driven band matrix** (no layered if/else), (2) add the **Google Docs** integration, (3) finish the **Later tab** fixes. You confirm/adjust the matrix cells; then it's implemented.

---

## 1. Triage — bands + clamp (replaces the branchy rules + the demotion bug)

**Four tiers, ordered low → high:**
`later(0) < can_wait(1) < today/by-EOD(2) < urgent(3)` (later == noise).

**The model (one rule, no branches):** every item's structural signal — `(source, reason)` — maps to a **band** `(floor, ceiling)` and a **default** tier. The LLM outputs one tier from content (deadline, who's waiting, urgency). The final tier is:

```
effective_tier = clamp(llm_tier or default, floor, ceiling)
```

- **Deterministic side (you own):** the floor/ceiling/default per row below, plus whether the LLM runs. This is the *only* place tier policy lives — a lookup table, not if/else.
- **LLM side:** picks a tier within the band from content. It can promote up to `ceiling` and demote down to `floor`, never past either. The prompt gets simpler (just "rate this item", no "never urgent" carve-outs) because the band, not the prompt, enforces policy.

This kills all three RCA-3 root causes at once: no branchy rules, the LLM can't demote below the floor (fixes assigned-issue → can_wait), and an urgent-with-deadline item is reachable because its ceiling is `urgent` and the prompt no longer forces deadlines to `today`.

### The matrix (proposed values — **confirm or adjust each cell**)

| Source | Signal / reason | Floor | Ceiling | LLM runs? | Default (no LLM) |
|---|---|---|---|---|---|
| GitHub | security alert / CI failure on my PR | urgent | urgent | no | urgent |
| GitHub | review_requested / approval_requested | today | urgent | yes | today |
| GitHub | changes_requested | today | urgent | yes | today |
| GitHub | assigned issue (`assign`) | today | urgent | yes | today |
| GitHub | notification / mention (subscribed) | can_wait | urgent | yes | can_wait |
| Slack | direct message | can_wait | urgent | yes | today |
| Slack | channel mention | can_wait | urgent | yes | can_wait |
| Gmail | message | later | urgent | yes | can_wait |
| Linear | assigned issue | today | urgent | yes | today |
| Calendar | meeting/event | can_wait | urgent | yes | today |
| **Google Docs** | **mention** | **can_wait** | **urgent** | **yes** | **can_wait** |
| **Google Docs** | **comment mentioning me** | **can_wait** | **urgent** | **yes** | **can_wait** |
| **Google Docs** | **share / access request** | **can_wait** | **urgent** | **yes** | **can_wait** |

Reading a row: "assigned issue → floor `today`" means it can never sink to can_wait/later no matter what the LLM says; ceiling `urgent` means the LLM *can* lift it to urgent if the content (a stated deadline) warrants; default `today` is used if the LLM hasn't run yet. Google Docs mentions have floor `can_wait` → they **never go to later**, and the LLM lifts them to today/urgent on a deadline, exactly as requested.

Levers you decide per row: **floor** (how low it can sink), **ceiling** (how high it can rise), **default** (pre-LLM), **LLM runs?** (skip the model for unambiguous structural cases like a CI failure).

### Implementation shape (data-driven, no if/else soup)
- One table constant `TIER_BANDS: dict[(Source, Reason) -> Band(floor, ceiling, default, runs_llm)]` (source of truth = this matrix).
- `rules.py` becomes a lookup into `TIER_BANDS` (no cascade of `if` checks); a missing key falls back to a safe default band (e.g. `(later, urgent, can_wait, llm=yes)`).
- `effective_tier` (ranking.py) becomes `clamp(llm_tier or band.default, band.floor, band.ceiling)` using the existing `Tier` ordering + the unused `at_least()`/a new `clamp()` in `tiers.py`.
- The LLM prompt (classifier.py) drops the policy carve-outs; it just rates urgency from deadline/waiting/urgency-language and returns one of the four tiers. The band clamps it.
- RGR: table-driven tests — for each row, assert (LLM says X) clamps to expected; assert assigned-issue never below today; assert Google-Docs-mention never `later`; assert a deadline email can reach urgent.

---

## 2. Google Docs integration (full, not hardcoded)

Add Google Docs as a first-class source, same shape as the others (it already has an auth-config env slot `COMPOSIO_AUTH_CONFIG_GOOGLEDOCS` and a catalogue entry).

- **Connect:** already wired via the source catalogue + `link_url`. Confirm the Composio auth config id is set in the box `.env`.
- **Triggers:** find the Composio Google Docs trigger slugs for mention / comment-mentioning-me / share-or-access-request (via `composio` search), add them to `TriggerProvisioner._TRIGGERS[Source.GOOGLE_DOCS]` with sane poll config.
- **Ingest mappers:** add `_MAPPERS` entries for those slugs → `RawEvent` (source="google_docs", a `reason` per event type, url to the doc/comment, title, body = the comment/mention text, deadline parsed from content if any). Each new slug MUST have a mapper (the provisioner test enforces this).
- **Triage:** covered by the matrix rows above — mentions/comments/share-requests get floor `can_wait` (never later), LLM lifts on deadline. Runs the same LLM triage over the doc content; no per-source hardcoding.
- RGR for the mappers + the band rows.

---

## 3. Later tab fixes (from RCA-2 issue 4)

- **Open modal, not link:** add a `laterRowToFeedRow` adapter (tier `noise`, status `unread`, id `source_ref`) and open a `DetailSheet` from the Later tab; the sheet's Open button becomes the only path to the external link. (Frontend, direct.)
- **Dynamic selector chips:** pass `sources: SourceInfo[]` into `LaterScreen`; derive chips from `status==='connected' && source!=='calendar'` instead of the hardcoded constant; initialize the selected chip to the first connected source.
- **`bring_back`:** scope to `status==='snoozed'` only (drop the fuzzy `noise` case); leave it off Later-tab rows.
- **Slack-in-Later:** LOW PRIORITY / optional (you said "no worries"). If done: give Slack a Later source that isn't DMs (channel mentions), since DMs already land on Home and are subtracted. Otherwise skip.

---

## 4. Verify
- Reset the GitHub integration for a clean test (delete Composio accounts + triggers + `connections`/`feed_items` rows for user `cf54cdda-1065-4119-bebf-44a6f1edfd5f`; NEVER delete the `users` row).
- Live-test on the box: connect a source → status flips fast → feed backfills → items land in the right tiers per the matrix.
- Box: `ssh productivity_app_test` (SSH IP rotates — re-add current egress IP to `sg-0d374ba0556b75951` port 22 first); backend at `/home/ec2-user/productivity-app`, deploy changed files via tar + `sudo systemctl restart productivity-backend`; app served at `https://52-64-67-235.sslip.io` (Caddy).
