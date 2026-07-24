# Design research: making the app read as premium

**Date:** 2026-07-24
**Status:** step 1 of 2 complete. **Step 2 is blocked on approval of [the shortlist](07-shortlist.md).**

---

## Why this exists

The MVP UI was reviewed as functional but not premium. This folder is the research behind fixing that, deliberately separated into two steps so the redesign is grounded in evidence rather than in taste.

- **Step 1 (this folder):** diagnose the current UI from the code, research what actually makes interfaces read as premium, and shortlist reference apps for approval.
- **Step 2 (not started):** tear down the approved apps at the level of measured detail, write a new design system spec covering dark and light, redline the Home screen, then implement.

**Nothing in this folder changes the app.** No existing file was modified. Every file here is new.

---

## A correction that shapes this folder

**The first research pass was web and desktop contaminated and had to be redone.** Round one shortlisted Linear, Raycast, Vercel, Mercury, Monzo and Superhuman, all of which earned their design reputation on a browser or desktop canvas.

That was a real error. **We are building a phone app, and mobile is a different medium:** tab bars, thumb reach, safe areas, a compressed type scale that tops out around 34pt instead of 64px, sheets instead of modals, gestures instead of hover, and haptics, which have no web equivalent at all. Mixing the two pollutes the spec.

**Nothing was deleted.** Round-one files are kept because their *principles* (accent discipline, concentric radii, spacing ratios, weight over size) are medium-independent and well sourced. Each now carries a caveat banner naming exactly what transfers and what does not. **Where a round-one file and a mobile file disagree, the mobile file wins.**

---

## Read in this order

**Mobile-only research. This is what step 2 is built on.**

| File | What it answers |
|---|---|
| **[00-current-state-audit.md](00-current-state-audit.md)** | Why *our* UI does not read as premium. Measured from the code, with file and line references. Start here. |
| **[07b-shortlist-mobile.md](07b-shortlist-mobile.md)** | The mobile app shortlist and the questions I need answered. **The decision point.** |
| [08-mobile-apps.md](08-mobile-apps.md) | The mobile app catalog, phone apps only, with awards stated precisely. |
| [09-mobile-design-principles.md](09-mobile-design-principles.md) | Tab bars, safe areas, thumb zones, sheets, gestures, haptics, mobile type scale, and how each differs from web. |
| [10-mobile-sentiment.md](10-mobile-sentiment.md) | Mobbin, mobile subreddits, YouTube and Dribbble mobile. What real people say about phone app design. |

**Round-one research. Principles stand, app lists and absolute web numbers do not.**

| File | Status |
|---|---|
| [05-gamification-that-stays-premium.md](05-gamification-that-stays-premium.md) | **Clean.** Every app studied (Apple Fitness, Oura, Whoop, Gentler Streak, Streaks, Things 3, Finch, Duolingo) is a phone app. No caveat needed. |
| [03-colour-dark-and-light.md](03-colour-dark-and-light.md) | **Mostly clean.** Colour theory is medium-independent, and the OLED and CRED sections are mobile-native. |
| [06-social-sentiment.md](06-social-sentiment.md) | **Mixed.** Contains the single most important finding of the whole effort (§1). Some critique threads are about websites. |
| [01-premium-apps-and-principles.md](01-premium-apps-and-principles.md) | **Catalog contaminated, 31 principles stand.** |
| [02-typography.md](02-typography.md) | **Mixed.** Apple's scale and tracking tables stand; the web scales do not. |
| [04-proportion-spacing-icons.md](04-proportion-spacing-icons.md) | **Mixed.** Material chip specs and the radius geometry stand; Linear's web padding does not. |
| [07-shortlist.md](07-shortlist.md) | **Superseded.** Retained for reference only. |

---

## The three findings that matter most

**1. We have components but no system.** Ten type sizes with gaps as small as 0.6pt, nineteen ad-hoc spacing values, eleven corner radii, three different chip shapes, and only two font weights. All of it produced by scaling a 272pt mockup by 1.379, so nothing lands on a whole point or a grid. Perceived quality comes almost entirely from the repetition and restraint a system enforces, and that constraint layer has never existed here. This is why the last five commits are all corrections.

**2. The spec and the implementation are two different designs, and dark mode does not exist.** `docs/design-system.md` describes a cool-grey, green-accented, dual-mode instrument panel with hairlines and no shadows. `mobile/src/theme.ts` ships a warm-cream, slate-accented, light-only design with drop shadows. Dark is meant to be the default and there is no mode dimension in the token layer at all.

**3. The naive premium recipe has inverted into a cheapness signal.** Gradients, frosted glass and neon-on-black are now the default output of AI codegen, and working designers reject them on sight as "vibe coded." Dribbble's own engagement data shows restrained system shots outperforming glassmorphic effect shots by roughly 10 to 20x. What survived is unglamorous and hard to fake: spacing, a tight type scale, one accent colour, concentric radii, real icons, motion and haptics.

---

## Evidence standards used here

- **`[primary]`** means the company's own design blog, Apple's own award citation, or the designer's own writing.
- **`[derived]`** means a third-party reverse-engineered token dump. These publish very specific hex and weight values but are scraped or generated breakdowns, not published design systems. **Treated as plausible but unverified throughout, and always labelled.**
- Where sentiment or commentary could not be found for an app, that is stated rather than padded. Several widely-praised apps are excluded on exactly this basis, and listed as excluded.
- Two commonly repeated claims are corrected: Copilot Money was a 2024 Apple Design Award **finalist**, not a winner, and Structured was a 2025 **App Store Awards** finalist, not an ADA recipient.
- One correction to the original brief: **CRED did not commission a custom typeface.** It uses Cirka, a retail serif by Nick Losacco from Pangram Pangram, with Gilroy and Overpass Mono.

---

## A note on images

Reference screenshots could not be written to disk: the browser tooling returned in-session image IDs rather than filesystem paths. Rather than guess at paths or fabricate them, **every visual reference is cited by its stable URL** so it can be reopened directly. The `references/` folder is reserved for step 2, when the teardowns will need annotated captures.

The existing mockups in [`../mockups/`](../mockups/) are the reference for the current state and were reviewed as part of the audit.
