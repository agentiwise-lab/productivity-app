# Teardown: Sequel, Gentler Streak, Nubank

**Date:** 2026-07-24
**Part of:** step 2 teardowns. Priority apps 5 to 7 of the [mobile shortlist](07b-shortlist-mobile.md).

**Evidence tags:** `[published]` a real value or quote from a primary source · `[observed]` described from a screenshot or video actually viewed · `[inferred]` reasoning, not evidence.

---

## 1. Sequel: the navigation question

**MacStories Selects 2025, Best Design winner.** Previously Best App Update 2023 ([MacStories](https://www.macstories.net/stories/macstories-selects-2025-recognizing-the-best-apps-of-the-year/)).

### The finding that reframes this app

MacStories credits Sequel with "a complete navigation rethink." **The mechanics are almost entirely stock iOS 26 API. The craft is in the reduction, not in custom animation code.** `[inferred, from the published API docs below]`

- MacStories: "Sequel on the iPhone is taking advantage of the fact that Liquid Glass makes tab bars for apps with simple navigation much more attractive than before." `[published]`
- Universal search lives in "the app's third navigation button residing in the bottom-right corner" which **"expands upon being pressed into a search bar."** `[published]`
- The developer's own 2.6 changelog: a new tab bar "where navigation is simpler and more flexible... giving quick access to Search from anywhere", with Liquid Glass making the tabs "lighter and less obtrusive" `[published]` ([changelog](https://www.getsequel.app/changelogs/2-6-changelog)).
- **SwiftUI ships `Tab(role: .search)`**, which places a button bottom-right; on selection **the tab morphs into a search field and the remaining tabs collapse** `[published]` ([Donny Wals](https://www.donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/)).
- The scroll behaviour is also a system modifier: **`tabBarMinimizeBehavior(.onScrollDown)`**, which only works when the tab bar overlays scrollable content `[published]`.

**So the editorial decision is the design work:** collapse to **two primary destinations (Saved, Collections)** and demote search from a tab to a role.

### Detail view

"Header images that morph seamlessly into blurred backgrounds as you scroll" `[published]`. The developer describes artwork that "dynamically blurs into the background" while scrolling, drawing "unique visual identity per title" `[published]`.

**Blur radius, scroll offsets and easing curves: NOT FOUND.** No breakdown documents the parameters.

### Other notes
- **Grid-of-artwork dominant, not text rows.** Row and card metrics, radii and spacing: **NOT FOUND**.
- **Empty states by omission:** categories "don't populate until you add an item from that category", deliberately avoiding empty-shelf clutter `[published]`.
- **Tap-only interaction.** The 2.0 review documents no swipe actions. **Haptics: NOT FOUND.**
- Search results carry "a handy set of buttons beneath the search field" filtering by media type `[published]`.

### Can we build this in React Native? Verified independently.

Mostly yes via Expo Router `NativeTabs`, **but with a limitation that hits us directly.** I fetched the Expo docs myself rather than trust the agent:

> **"Native tabs is in alpha and is available in SDK 54 and later. Its API is subject to change."**
>
> **"FlatList integration: Features like scroll-to-top and minimize-on-scroll aren't supported. Additionally, detecting scroll edges may fail, causing the tab bar to appear transparent."**
>
> "On Android, there is a limitation of having a maximum of 5 tabs in the tab bar."
>
> Dynamically adding or removing tabs "remounts content and resets state." Native tabs "cannot be nested inside other native tabs."
>
> `role="search"` requires **SDK 55+ and Xcode 26+**. `minimizeBehavior="onScrollDown"` requires SDK 55+.

`[published]` ([Expo native tabs](https://docs.expo.dev/router/advanced/native-tabs/))

> ### This is the most actionable engineering finding in the whole teardown set
>
> **Our feed is a `FlatList`.** The two behaviours that make the iOS 26 tab bar read premium, minimize-on-scroll and correct scroll-edge detection, are **explicitly unsupported with FlatList today**, and the failure mode is not subtle: "the tab bar to appear transparent."
>
> So the plan has to be one of: accept a static (non-minimizing) native tab bar; migrate the feed off `FlatList` to a supported list; or build the tab bar ourselves and forgo the system glass. **This must be decided before any tab bar work starts, not discovered during it.**

For arbitrary glass surfaces there is [`@callstack/liquid-glass`](https://github.com/callstack/liquid-glass) (`interactive`, `effect`, `tintColor`, and a container view whose `spacing` prop makes adjacent glass elements merge). Limits: `interactive` is set on mount only and is not dynamic, and above 65pt height text colour does not auto-adapt `[published]`. A "max ~3 stacked glass layers for 60fps" figure circulates but **the Callstack blog returned HTTP 403**, so it is second-hand and unverified.

**The header-artwork-to-blur morph is not a system affordance and is in no RN library.** It would be hand-built with Reanimated plus a blur view `[inferred]`.

### Single most distinctive decision
**Search is demoted from a place to a mode.** For a triage feed this transfers directly: we rarely need more than two persistent destinations, and search is a mode, not a place.

---

## 2. Gentler Streak: the classy-gamification question

**Apple Design Award winner, 2024, Social Impact** `[published]`. Its sibling **The Outsiders: Athlete Tracker** is a **2026 ADA finalist in Interaction, not a winner** `[published]`.

### The thesis, in their words
- **"Statistics are just numbers. Without knowing how to interpret them, they are meaningless. We wanted to change that and focus on the humanity."** `[published]` ([Apple](https://developer.apple.com/news/?id=3m0ht22s))
- "We think of it more as a lifestyle app. We want it to feel like a compass." `[published]`
- "We weren't primarily addressing the audience that most fitness apps seemed to target. We focused on everyone else, the people who maybe didn't feel like they belonged in a gym." `[published]`
- Monthly Summary "shows how you're doing in relation to your history" `[published]`.

### The single most copyable idea: a corridor, not a score

The central visual on the Streak tab is the **Activity Path**: **"a green band, which represents your Activity Path, and a white dotted line, which shows your actual activity level over time."** The goal is to "keep the white line within the green path" `[published]` ([docs.gentler.app](https://docs.gentler.app/understanding-your-activity-path/interpret-the-activity-path)).

Zones are **positional and qualitative, not numeric**: the dark-green upper band means you are approaching your limit, the middle is balanced, the light-green lower band means you are ready for intense effort `[published]`. **No numeric thresholds and no zone labels are published** `[published, explicit absence]`.

So the structure is a **banded-range chart**: a target corridor plus an actual series. **It replaces a score you maximise with a corridor you are inside or outside of.**

> **For a triage feed this is excellent:** "you are inside a healthy backlog range" is a far better frame than "you have 47 items", and it removes the implicit instruction to drive a number to zero.

### Qualitative state words
Statuses are words: **Active Recovery, On a Break, Injured, Sick** (formalised in The Outsiders) `[published]`. **"Go Gentler"** is the named recommendation surface, offering rest, active recovery, strength or cooldown `[published]`.

**An important nuance that qualifies the "no numbers" principle:** The Outsiders, the sibling app for performance athletes, **reintroduces a numeric Training Readiness Score** `[published]` ([gentlerstories.com](https://gentlerstories.com/theoutsiders)). **The no-numbers rule is audience-conditional, not absolute.**

### The mascot: what it does and does not do
**Yorhart** ("your heart"), created with illustrator Sören Selleslagh, "a love letter from your heart" `[published]` ([Sketch](https://www.sketch.com/blog/gentler-streak/)). It appears **over** the Activity Path as a reaction to state `[published]`; a motion catalogue lists a "sad reaction" on wellbeing screens `[observed, third-party]` ([60fps.design](https://60fps.design/apps/gentler-streak)).

**What it does not do:** it is not a navigation element, not persistent chrome, and carries **no streak-shaming or loss-aversion mechanic** `[inferred from absence across all sources]`.

### Copy tone, which is a design material here
Their spec: **"motivating but not fake-hyped"** and **"light-hearted, to not take itself too seriously"** while staying professional and accurate `[published]`.

A third-party UX-writing audit found non-judgmental framing (no "underperforming"), neutral comparisons such as **"Below Typical Thursday"**, and permissive phrasing ("You might" rather than "You should"). **The same audit criticises:** raw minute durations forcing mental math, calorie framing risky for eating-disorder sensitivity, an unexplained "Zone 0", and repeated identical push copy going stale `[published]` ([Bootcamp](https://medium.com/design-bootcamp/ux-writing-review-of-gentler-streak-8babf8cb2594)).

### Gaps
**Typeface, weights, hex values, watchOS readiness-bar geometry, haptics and error states: all NOT FOUND.** Apple states the app is "built largely in UIKit" but **gives no reason** `[published]`; do not repeat any "why" without a source.

**A disputed source, excluded:** pixso.net claims a bottom nav of "Activity / Sleep / Insights / Settings" and a "soft blues and greens" palette. The official docs name a **Streak tab** and an **Insights tab**, and the only sourced colours are the green Activity Path bands. **Treated as unreliable and excluded.** The full official tab list remains **NOT FOUND**.

---

## 3. Nubank: dark mode at scale

Primary source: [The birth of the Dark Mode](https://building.nubank.com/the-birth-of-the-dark-mode-a-journey-into-nubanks-app-evolution/).

### Palette decisions, all `[published]`
- **Pure black background**, to match iOS and Android natively and because **OLED turns pixels off at pure black**.
- **Neutral greys, chosen deliberately over warm or cool:** "We opted for a palette of neutral grays, when we could have chosen cool or warm grays." Rationale: keep a **blank canvas** for product experiences.
- **Brand purple:** naive inversion produced light purple with black text, which read as off-brand. Fix: **darken the purple, reduce saturation, keep white text on those surfaces.**
- The business-account purple needed further darkening, which then collided with the dark grey UI tones, resolved by iterating across contrast ratios.
- **Text:** "Text colors were adjusted to remain lighter on black backgrounds, avoiding excessive contrast." Note the direction: they targeted **reduced** contrast against pure black.
- **Saturation reduced globally** to prevent eye discomfort, while holding minimum contrast ratios.
- **Illustrations work in both modes rather than forking assets.** Ground shadows disappear in dark; very light greys are darkened.

**HEX VALUES: NOT FOUND.** Neither the dark-mode article nor the NuDS colour write-up publishes a single hex code. **Nobody should quote a "Nubank dark grey" value.**

### Token architecture, the deepest available detail
From the [NuDS Colors Foundation review](https://zezorzan.com/work/nuds-colors-foundation-review), corroborated by [Figma's case study](https://www.figma.com/customers/nubank-design-system-accessible-experiences-with-figma/):

- **Two layers: primitive, then semantic** `[published]`.
- **Primitive:** palettes of 10 swatches, each with a defined contrast ratio, built from "a scale of 41 contrast ratios (from 1:1 to 21:1)" `[published]`.
- Key colours use an **HSB model**, producing "a matrix of brightness and saturation for each hue", letting yellow darken toward orange and purple shift bluish `[published]`.
- **Generated with Adobe Leonardo**, chosen to "generate palettes based on contrast ratios, ideal for accessibility purposes" `[published]`.
- **Semantic layer, four categories** `[published]`:
  1. **UI elements**, named by role: **background, surface, content, border**
  2. **Feedback:** Neutral, Success, Attention, Critical
  3. **Accent:** the brand purple, for buttons and selected states
  4. **Decorative:** illustrations, charts, customisation
- **Outcome: 100% of semantic token combinations meet WCAG AA; 70% reach AAA** `[published]`.
- **The literal token string format is NOT FOUND.** The role vocabulary is published; the syntax is not.

### The migration mechanic, and the best idea in this teardown
"Instead of having to upgrade more than 3 thousand screens one by one and delaying the feature's launch, we were able to deliver it faster" `[published]`.

The mechanism, verbatim: **"When a given screen isn't updated on the latest version of the Nu Design System (i.e. the tokens aren't available for the current version, therefore the screen 'wouldn't know' how to change colors for Dark Mode"** — a fallback ensured uninterrupted service for those screens `[published]`.

**Reading:** screens pinned to an older design-system version resolve to a safe default rather than breaking, so dark mode shipped **before** full token adoption `[inferred from that quote]`.

> **This is a shipping strategy, not a visual one, and it is directly applicable.** We have an existing app with no dark mode. A theme provider whose lookup falls back to a known-good default when a component requests a token the current theme version lacks would let us ship dark mode incrementally instead of converting every screen first.

Also relevant to why this was tractable at all: **80% of app screens use server-driven UI**, and NuDS spans 100+ components and 320,000 lines of code `[published]`. **That scale is theirs, not ours** — do not import the architecture, only the fallback idea.

### Gaps
**Row unit, typography, chips, icons, gestures, motion, haptics and empty/error states: NOT FOUND.** Their blog is systems-deep and component-shallow. The agent explicitly refused to reconstruct these from Figma-community fan recreations, which is the right call.

---

## What transfers to a dark-first triage feed

1. **Pure black plus neutral greys, with saturation pulled down globally.** Neutral greys keep the canvas blank so content colour carries meaning; desaturating accents prevents halation on OLED `[published]`.
2. **Lower text contrast against pure black, do not raise it.** "Lighter on black backgrounds, avoiding excessive contrast." **Pure `#FFF` on pure `#000` is the amateur move** `[published]`.
3. **Two-layer tokens with the four-category semantic vocabulary: background / surface / content / border, plus feedback, accent, decorative.** Directly liftable into an RN theme `[published]`.
4. **A version-aware token fallback** so un-migrated screens degrade safely `[published as concept]`.
5. **Two primary tabs plus search-as-a-role.** But see the FlatList constraint above before committing.
6. **A banded corridor instead of a score.** "Am I inside a healthy range" rather than "what is my number."
7. **Qualitative state words instead of numeric urgency**, which reads as respectful rather than punitive.
8. **Empty states by omission.** An empty section should not exist rather than be a decorated void.
9. **Copy rules, verbatim:** "motivating but not fake-hyped", permissive over imperative, comparison against your own history only.
10. **Accessibility as an acceptance criterion**, not a layer. Nubank's 100% AA / 70% AAA token audit is a measurable bar.

## What is signature and should not be copied

- **The artwork-to-blur header morph (Sequel).** It exists because every Sequel record ships with hero poster art. Our items are PRs, emails and messages with no artwork, and it is the one part covered by no system API or RN library, so we would pay full custom cost for a borrowed signature.
- **Category-specific visual identity per media type (Sequel).** Right when categories are films vs books. In triage it fragments scanning, which depends on rows being visually identical.
- **Yorhart the mascot.** It works because it is literally "what your heart would be telling you" about your body. A mascot reacting to an unread queue reads as condescending.
- **The Activity Path's green semantics.** Copy the **corridor**, not the **green**. Green-good is domain-bound; we need neutral by default with colour reserved for genuine urgency.
- **Brand-colour-as-accent-everywhere (Nubank purple).** Their accent tier defends an enormously valuable brand asset. Ours should appear rarely and mean one thing.
- **Server-driven UI across 80% of screens.** A 3,000-screen, multi-country answer. Pure overhead at our scale.
- **Liquid Glass as an aesthetic goal.** Adopt it where the OS gives it free (tab bar, search role) and stop there. Hand-rolling glass in RN costs GPU budget and has documented gaps.

---

## Confidence audit

**Verified independently by me, not taken on trust**
- The Expo `NativeTabs` limitations, quoted verbatim from the Expo docs. **The FlatList caveat is real and it constrains us.**
- ADA statuses cross-checked: Gentler Streak **winner** 2024 Social Impact; The Outsiders **finalist** 2026 Interaction. The two agents' accounts of the 2026 Inclusivity category ("Pine Hearts and Guitar Wiz" vs "Guitar Wiz") are **not in conflict** — ADA names separate app and game winners per category.

**Could not verify / explicitly NOT FOUND**
- **Any hex value for any of these three apps.**
- Sequel: blur radius, scroll thresholds, easing, row metrics, typography, haptics, error states. The developer publishes no design write-ups beyond changelogs.
- Gentler Streak: typeface, weights, watchOS readiness-bar geometry, haptics, error states, and **why UIKit over SwiftUI** (Apple states the fact, gives no reason).
- Nubank: literal token syntax, the actual tab list or IA diagram, and every component-level specific.
- The "max 3 Liquid Glass layers for 60fps" figure: the Callstack blog returned **HTTP 403**, so it is second-hand.

**Where sources disagreed**
- **Gentler Streak's tab structure.** pixso.net contradicts the official docs on both tab names and palette. Excluded as unreliable; the official list remains NOT FOUND.
- **Numeric vs qualitative scoring across the Gentler Stories portfolio** is a genuine product divergence, not a sourcing conflict. It matters: **the no-numbers principle is audience-conditional.**

**Framing correction worth stating plainly**
MacStories' "complete navigation rethink" is editorial praise for a **reduction decision**. The mechanics are stock iOS 26 API, all exposed to React Native today via Expo Router. **What is not free is the header morph.**
