# Shortlist: 18 apps to tear down in step 2

**Date:** 2026-07-24
**Status: SUPERSEDED. Do not action this list.**

> ### Superseded by [07b-shortlist-mobile.md](07b-shortlist-mobile.md)
>
> **Why:** this shortlist is web and desktop contaminated. Linear (web/desktop), Raycast (macOS), Vercel/Geist (web), Mercury (web-first), Monzo (the cited evidence is their *web* design system post) and Superhuman (desktop-first) were all included on the strength of their web or desktop UI. That was a mistake.
>
> Mobile is a different medium: tab bars, thumb reach, safe areas, a compressed type scale, sheets instead of modals, gestures instead of hover, and haptics. Design principles do not transfer cleanly from a 1440px canvas to a 390pt one, and mixing the two pollutes the spec we are about to write.
>
> **Kept, not deleted**, because the *principles* sourced here (accent discipline, concentric radii, spacing ratios, weight over size) are medium-independent and still hold. **What does not transfer is the app list and any absolute size or spacing number taken from a web system.** Every such number is re-derived from mobile sources in the replacement research.
>
> The mobile-only replacement research is [08-mobile-apps.md](08-mobile-apps.md), [09-mobile-design-principles.md](09-mobile-design-principles.md) and [10-mobile-sentiment.md](10-mobile-sentiment.md).

---

**Original status: awaiting approval. Retained below for reference only.**

Step 2 does not begin until you cut this list. Studying 18 apps at the level of detail you asked for (chip sizes, tab placement, exact proportions) is roughly 18 focused teardowns. **Six to eight is the realistic number.** My recommendation is marked.

---

## How each app was validated

Three independent gates, and every app below states which it passed:

- **P: primary design evidence.** The company's own design blog, Apple's own award citation, or the designer's own published writing. The strongest grade.
- **U: user or practitioner sentiment.** Named and praised by real people on Reddit, YouTube or Dribbble with visible engagement. See [06-social-sentiment.md](06-social-sentiment.md).
- **R: relevance.** Dense, list-based, data-carrying, dark-capable, mobile. How close it is to what we are actually building.

**No app is on this list on my taste alone.** Where evidence is thin, it says so.

---

## Tier 1: study these. Highest evidence, highest relevance.

### 1. Linear — P, U, R
The best-documented case in existence, because Linear publishes its rationale. Also the only app on this list where a *specific* interaction was praised by a real user: "the drag and drop feels so precise."
**Extract in step 2:** the LCH/OKLCH theme-generation model reduced to three variables (base, accent, contrast); the surface elevation ladder; the "not every element carries equal visual weight, navigation must recede" rule; the icon reduction pass; their actual component padding (button 8/14, tab pill 6/14, status badge 2/8).
**Why it matters most to us:** it is the closest thing to a proven answer for "dense, dark, list-based, engineer-facing, and expensive-looking."

### 2. CRED — P (system is open-source), U, R
Your reference, and it survives scrutiny. NeoPOP is open-sourced with a live token playground.
**Extract:** the exact accent-discipline ratio (black chrome, white cards, saturated colour only at points of action); **the big-but-light numeral**, which is the specific detail separating it from the "cartoonishly big and bold" hero that got roasted; the borderless circular icon buttons; the three-radii-by-size approach.
**Caveat:** the hard-edged offset "pop" shadow is CRED's signature, not a neutral pattern. Understand why it works before deciding whether to borrow it. Their typeface is Cirka (retail, Pangram Pangram), not custom, so it is licensable rather than unreachable.

### 3. Things 3 — P (two Apple Design Awards), U, R
The premium bar for a task app, and the reference for restraint in completion feedback.
**Extract:** the filling-pie progress device; row density and vertical rhythm; how it achieves hierarchy in a list without boxes; the checkbox animation, which reviewers consistently describe as "subtle, deeply satisfying." **The reward is motion quality, not a payload.**

### 4. Superhuman — P (strongest typography case), R, U mixed
**Extract:** the typography-as-differentiation thesis, and the specific craft moves: rounding punctuation and tittles to match the logo geometry, shipping smart quotes inside the font file.
**Honest note:** user sentiment is genuinely mixed. "Design is decent. Could be tastier but regardless, it's extremely utilitarian", with a replier disagreeing outright. Study it for the typography reasoning, not as an all-round exemplar.

### 5. Halide — P (Apple Design Award, Apple's own words), R partial
The single best source on accent discipline, with a documented failure worth learning from.
**Extract:** the "**single yellow highlight colour** used to indicate active state" model; the anti-flight-simulator stance; and the failure, that **colour alone was insufficient to signal state and the button form had to change too.** That last one directly affects how we mark urgency.

### 6. Oura — P (company + agency writeups), R
The reference for progress and score display, and for cutting navigation.
**Extract:** how a single 0-to-100 numeral plus a one-word qualifier carries a whole screen; "progressive disclosure, a unified semantic colour language, and a data-visualization framework that scales"; **and how they went from 5 tabs to 3.**
**Counter-evidence to weigh:** DC Rainmaker found the 2025 redesign "dilutes the information too much." Minimalism has a floor.

---

## Tier 2: strong evidence, narrower extraction

### 7. Raycast — P, R
**Extract:** the icon system rebuilt with a specialist under "the same rules for stroke width and corner radii", and the decision to make one hero element bigger to reflect its importance. **Directly applicable to our placeholder tab bar and our three-equal-tiles problem.**

### 8. Vercel / Geist — P, R
**Extract:** the published type ramp with size-indexed negative tracking; three weights with no 700 anywhere; status colour confined to ~10px indicator dots and never used as a fill. Geist Sans and Geist Mono are OFL, so this is the one system we could adopt wholesale for free.

### 9. Family — P (designer published his principles), R partial
The best-documented motion case anywhere.
**Extract:** component persistence across transitions; and **the delight-impact curve**, "the potential for delight increases as the frequency of feature usage decreases." For a triage app used dozens of times a day, this is the rule that decides where our animation budget goes.

### 10. Gentler Streak — P (2024 Apple Design Award), U, R partial
The answer to "gamified but classy."
**Extract:** comparing the user to **their own history, never to a target or to others**; translating statistics into words. "Statistics are just numbers. Without knowing how to interpret them, they are meaningless."

### 11. Mercury — U weak, R, P only `[derived]`
**Extract, treating every number as unverified:** the intermediate weight axis (360/420/480/530) avoiding the bold/light binary, with **heading weight 480** as the signature; one accent reserved exclusively for the primary CTA. **And the token counts: 6 radii, 9 spacing values, against our 11 and 19.**

### 12. Monzo — P, R partial
**Extract:** the semantic-token architecture built to support future themes without refactoring, and the discipline of holding the brand colour back because red means failure in UI. That is the same reasoning as our own `signal`-for-urgency-only rule.

---

## Tier 3: specific single lessons

### 13. Streaks (iOS) — P (Apple Design Award), R partial
One lesson, and it is a good one: when they needed more capacity they **"turned Streaks' single view into a card and put additional goals on the back" rather than adding density.**

### 14. Flighty — P (Apple's own citation), U
One lesson: **borrow a real domain's visual conventions.** Apple praised "a look that mirrors time-honored airport design conventions." Our analogous domains are the instrument panel, the trading terminal and the departure board, which is what `design-system.md` was already reaching for.

### 15. Granola — P (design press), R partial
The counter-example that keeps us honest: **premium via warmth, not dark minimalism.** A rebrand explicitly framed as rejecting "tech slop." Worth studying precisely because it would invalidate a lazy "dark equals premium" conclusion.

### 16. Bear — P (Apple Design Award), R partial
One lesson: an award won on **typography and speed**, with no ornament at all.

### 17. UI8's "TaskEz" Dribbble system — U (2.8k likes / 712k views)
Not an app, but the **highest-engagement productivity-iOS design on Dribbble by a wide margin**, and therefore the best crowd-validated reference for our exact category. Worth a proportions teardown.

### 18. The roasted "institutional FinTech OS" — U (net-downvoted, 22 comments)
**Deliberately included as the anti-reference.** Someone built the naive premium recipe (`#050505`, frosted glass, neon cyan) and was told it was AI slop by near-unanimous vote. Study it to know exactly what not to do, and read the comments as the checklist. See [06 §1](06-social-sentiment.md).

---

## Deliberately excluded, and why

Honesty about what did not make it matters as much as the list itself.

- **Notion Calendar, Amie, Bezel, Sunsama, Reflect, Height, Craft, Rise, Whoop, Strava, Robinhood, Revolut, Cash App, Monarch, Rainbow, Phantom, Cursor, Perplexity, Stripe dashboard.** Widely praised, but **no specific citable design commentary was found in this pass.** Absence of evidence is not a judgment on their design. If you want any of them in, say so and I will research them properly rather than assert.
- **Duolingo, Habitica, Finch.** Studied only as loud counter-examples in [05](05-gamification-that-stays-premium.md). Note the irony that Duolingo is both the most-recommended app to study *and* the identified source of the "looks too basic" problem in another thread.
- **21st.dev.** Investigated and **rejected as a positive reference.** Its most-installed components are aurora gradients, glowing orbs and Spline scenes, which is the exact vocabulary designers roasted. Treat it as a catalog of what is cheap to add. See [06 §10](06-social-sentiment.md).
- **Copilot Money and Structured** appear in many "award-winning design" lists, but Copilot was a 2024 ADA **finalist**, not a winner, and Structured was a 2025 **App Store Awards** finalist, not an Apple Design Award recipient. Both corrected here so we do not repeat the claim.

---

## My recommendation

**Cut to these seven for step 2:**

| # | App | The one thing it gives us |
|---|---|---|
| 1 | **Linear** | The whole system model: OKLCH themes, elevation ladder, receding navigation, real padding numbers |
| 2 | **CRED** | Accent discipline and the big-but-light numeral |
| 3 | **Things 3** | List density, row rhythm, and restrained completion feedback |
| 4 | **Halide** | Single-accent state marking, and why form must change too |
| 5 | **Oura** | The score-plus-qualifier device, and cutting 5 tabs to 3 |
| 6 | **Gentler Streak** | Gamification that compares you to yourself |
| 7 | **The roasted FinTech OS** | The anti-reference checklist |

Seven teardowns is achievable and covers every open question in [the audit §8](00-current-state-audit.md): palette, type, icon set, scale ratio, and the gamified layer.

**Vercel/Geist is the likely eighth**, but as a *token source to adopt* rather than an app to tear down, since its type ramp and OFL fonts are directly usable.

---

## What step 2 produces, once you approve

1. **A teardown doc per approved app.** Measured, not described: chip heights and padding ratios, row heights, type sizes and weights, radii, icon sizes and stroke weights, tab-bar treatment, accent surface area.
2. **A new design system spec** with dark as default and light as the alternate, in OKLCH, on Radix step roles: 6 type sizes, 3 weights, 8 spacing values, 4 radii plus a pill, one accent, one icon family.
3. **A resolution of the `design-system.md` versus `theme.ts` conflict**, since one of the two has to be retired deliberately. See [the audit §2](00-current-state-audit.md).
4. **A redlined redesign of the Home screen**, the worst offender, before anything is generalised.
5. **Only then, code.**

---

## Three questions I need answered before step 2

These genuinely change the output, and I am not going to guess at them.

**1. Which apps do you actually want torn down?** My seven, or a different cut.

**2. Deep green or electric blue as the single accent?** Both are well evidenced ([03 §10](03-colour-dark-and-light.md)). Green reads calm and permanent and matches the "quiet instrument" positioning in the product brief. Blue reads precise and technical and matches the developer wedge. **This is a brand call, not a research call, so it is yours.**

**3. Does the mono-for-data signature survive?** Our locked spec says "the mono pairing is the signature" and sets *all* labels, chips and channel names in it. The research says mono reads premium on a narrow semantic slice (numbers, timestamps, refs, IDs) and reads costume-y when it becomes the vibe ([02 §5](02-typography.md)). **My recommendation is to keep mono and narrow it to those four uses, and to replace Menlo with Geist Mono.** Confirm or overrule.

---

## One thing worth saying plainly

The research turned up a finding that changes the brief slightly, and you should see it before approving anything.

**The naive premium recipe is now a cheapness signal.** Gradients, frosted glass and neon-on-black used to read expensive. They are now the default output of AI codegen, and working designers reject them on sight as "vibe coded." Dribbble's own engagement data backs this: restrained system shots outperform glassmorphic effect shots by roughly 10 to 20x.

What survived is unglamorous and hard to fake: **spacing, a tight type scale, one accent colour, concentric radii, real icons, motion and haptics.** Every one of those is a systems problem, which is exactly what our audit says we are missing, and none of them is a style we can apply on top.

That is the good news. It means the fix is bounded and durable rather than a re-skin that dates in a year.
