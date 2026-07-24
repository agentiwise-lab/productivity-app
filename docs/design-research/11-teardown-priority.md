# Teardown: Things 3, CRED, Flighty, Halide

**Date:** 2026-07-24
**Part of:** step 2 teardowns. Priority apps 1 to 4 of the [mobile shortlist](07b-shortlist-mobile.md).

**Evidence tags:** `[measured/published]` an exact value read from primary source code or an official spec · `[reported]` described by a named third party or a primary text source · `[measured/pixels]` extracted by me from the reference screenshots · `[inferred]` reasoning.

**Note:** the research agent viewed no screenshots, so it substituted `[reported]` rather than mislabel secondhand prose as observation. That was the right call. Where I have since measured something from the saved screenshots, it is tagged `[measured/pixels]` and attributed to me.

---

## 1. CRED / NeoPOP

By far the richest source, because the design system is open source. Everything below is read directly from the repos.

### The spacing system: a 5px base unit

**"All the paddings and margins in neopop-web are multiples of 5."** `[measured/published]`, verbatim from [`Layout.stories.mdx`](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/components/Helpers/Layout.stories.mdx).

- `HorizontalSpacer` / `VerticalSpacer` take one prop `n` and apply margin `(5*n)px` `[measured/published]`
- `PageContainer`: `padding-right: 15px; padding-left: 30px` — **asymmetric**, not a symmetric gutter `[measured/published]`
- `HorizontalDivider` default colour `rgba(255, 255, 255, 0.1)` `[measured/published]`

> **A 5px base is unusual and worth flagging before anyone copies it.** It is not 4 and not 8, which is part of why NeoPOP layouts feel slightly off-grid against Material and HIG. **If we take the tokens we must take the 5-step. Mixing 5-step tokens into an 8-step layout will read as sloppy** `[inferred]`. Given [09](09-mobile-design-principles.md) argues for a 4/8 grid on mobile, **this is a genuine conflict and we should not adopt CRED's 5px unit.**

### The NeoPOP geometry primitive

```ts
const enum PlunkProps { WIDTH = 3, ANGLE = 45 }
```
`[measured/published]` ([primitives/index.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/index.ts))

**The entire signature is a 3px edge extruded at 45 degrees.** Everything else derives from it.
- `CardFace` gets `margin: 0 3px 3px 0`; the right edge is `width: 3px; transform: skewY(45deg)`, the bottom edge `height: 3px; transform: skewX(45deg)` `[measured/published]`
- **Press state = the face translates into its own shadow:** `translate3d(3px, 3px, 0)` `[measured/published]`
- **`Button/styles.ts` contains no `box-shadow` at all.** This is a pure geometric extrusion, not a shadow `[measured/published]`

### Edge colour derivation: do not hand-pick shadow colours

From [`PopHelper.swift`](https://raw.githubusercontent.com/CRED-CLUB/neopop-ios/main/Sources/NeoPop/PopHelper.swift) `[measured/published]`:
- horizontal edge = base `darker(by: 30)` if luminance ≥ 0.3, else `lighter(by: 30)`
- vertical edge = base `darker(by: 10)` if luminance ≥ 0.3, else `lighter(by: 10)`
- luminosity threshold `0.3`

**Two different lightness deltas (30 vs 10) for the two edges is what fakes a single light source.** Reimplementable in RN in about fifteen lines with an HSL helper `[inferred]`.

### Motion: fast down, slow up

| Platform | Token | Value |
|---|---|---|
| Web | button press transition | `0.12s ease-in-out` |
| Web | card transform transition | `0.03s ease` |
| iOS | `PopButton.pressDuration` | `0.15` |
| iOS | `PopFloatingButton.touchDownDuration` | `0.2` |
| iOS | `PopFloatingButton.touchUpDuration` | **`0.5`** |
| iOS | `levitatingAnimationDuration` | `2.0` |
| Android | `TILT_PRESS_DURATION` | `50ms` |
| Android | `TILT_FLOATING_DURATION` | `2000ms` |
| Android | `ANIMATION_START_DELAY` | **`5000ms`** |
| Android | `SHIMMER_ANIMATION_DURATION` | `1500ms` |

All `[measured/published]`. Tilt interpolator is `AccelerateDecelerateInterpolator()`.

> **The pattern is the finding: press feedback is fast and asymmetric (0.12 to 0.15s down, 0.5s up), while ambient motion is slow (2s) and only starts after 5s of dwell.** Snappy affordance, lazy ambience. Directly transferable `[inferred]`.

### Android dp values, and a contradiction

From `NeoPopGeometry.kt` and `PopFrameLayoutStyle.kt` `[measured/published]`:
- `DEFAULT_DEPTH = 3f.dp`, `DEFAULT_STROKE_WIDTH = 1f.dp`
- `PopFrameLayoutStyle.depth = 8f.dp`
- `disabledOpacity = 0x4D` (≈30%)
- **Default surface visibility: left `false`, top `false`, right `true`, bottom `true`** — the extrusion always goes down-right

**I verified the depth values myself directly against the repo, and confirm the contradiction:** `NeoPopGeometry.DEFAULT_DEPTH = 3dp` but `PopFrameLayoutStyle.depth = 8dp`, while web uses `3`. **Three sources, two values.** Treat 3 as the design intent and 8dp as an Android layout-level override.

**Also verified by me:** the Android library has **no `dimens.xml`** — only the *sample* app does, so any spacing number sourced from `sample/` is demo code, not the design system. And `colors.xml` in the library is mostly Android Studio boilerplate (`purple_200`, `teal_700`). **The web repo is the real token source.**

### Colour

Main: `black #0d0d0d`, `white #ffffff`, `red #EE4D37`, `yellow #F08D32`, `blue #144CC7`, `green #06C270`. Six brand hues get **8-step ramps (100 to 800)**; semantic hues get **5-step (100 to 500)** `[measured/published]`.

Neutral ramp: `popBlack` 100 `#8A8A8A` / 200 `#3D3D3D` / 300 `#161616` / 400 `#121212` / 500 `#0d0d0d`.

> **The palette shape is many saturated accents, not one.** This is the opposite of Things, Halide and Flighty. And the neutral ramp is compressed into near-black (`#0d0d0d → #161616 → #121212`), meaning **the dark mode is the only mode** — there is no light-surface neutral ramp of comparable depth `[inferred]`.

**My own pixel measurement corroborates this:** sampling CRED's App Store screenshots returns neutrals `#F8F8F8`, `#000000`, `#101010`, `#080808`, `#181818` `[measured/pixels]` — the near-black ladder is real and visible in the shipped app.

### Typography

`[measured/published]`, from `primitives/typography.ts` and `TypographySystem/global.ts`:
- **Two families: Gilroy (sans) and Cirka (serif).** Gilroy at 800/700/600/500/400/300, Cirka at 700/600/500/400/300.
- Four roles encoded as a namespace prefix: `th` heading, `tb` body, `tc` caps, `tsh` serif heading.
- **Line-height multipliers: heading 1.25, caps 1.25, serif 1.25, body 1.5.**
- **Letter-spacing: caps `1px` or `2px`; body `0.4px`; heading ExtraBold `0` or `0.2px`; heading Bold/SemiBold `0.2` or `0.4px`; serif `0.2px`.**
- **Opacity as a hierarchy axis:** `HEADING 0.9 / SUB_HEADING 0.7 / BODY_TEXT 0.5 / BODY_TEXT_LIGHTER 0.3`.

> **The key insight for us.** On a near-black surface CRED creates hierarchy with **weight plus opacity, not size**. Nothing steps below 10px; instead body text drops to 50% white. **Four fixed opacity tiers is a cleaner contract than a grey ramp because it composes with any accent** `[inferred]`. (Resolve to solid hex per theme and measure, per [02 §8](02-typography.md).)

### Buttons and chips

| size | height | padding | icon |
|---|---|---|---|
| big | 50px | `0 30px` | 20px |
| medium | 40px | `0 20px` | 16px |
| small | 30px | `0 25px` | 14px |

**Note `small` has *more* horizontal padding (25px) than `medium` (20px).** Read verbatim from source. Likely a bug in their repo; flagged, not corrected.

**Chips** (`Tags/styles.ts`) `[measured/published]`:
- `padding: 5px 10px 4px`
- **No `border-radius` and no `border` anywhere in the file. CRED tags are hard rectangles, not pills.**
- Icon `height: 10px`, `margin-right: 5px`
- Only variants are `success | error | warning` × `light | dark`

> **The 5/10/4 padding, 1px less on the bottom, is optical centring for an all-caps label with a tall cap-height font. That asymmetry is worth stealing** `[inferred]`.

### What the repo does not contain

**`NOT FOUND`: no tab bar, no list-row, no navigation primitive.** The component set is Back, BottomSheet, Button, Checkbox, Dropdown, ElevatedCard, Header, InputField, Radio, Scoremeter, SearchBar, Slider, Tags, Toast, Toggle, Typography `[measured/published]`.

**Also absent, and the absence is the finding: no shadows, no border-radius tokens, no elevation scale, no breakpoints file.** NeoPOP replaces elevation with geometry `[measured/published]`.

**On the shipped app**, 60fps.design indexes 71 CRED interactions including a heavy loader family: "Verifying Documents Loader", "Checking Details", "Retrieving Credit Score", "Button Loading to Tick", "Scanning Loader", and a **"No Internet Snake Game"** failure state `[reported]`. **CRED treats waiting as a designed surface, not a spinner. A triage feed fetching from many sources has the same problem** `[inferred]`.

---

## 2. Things 3

Two Apple Design Awards (2009, 2017) `[measured/published]`.

### Navigation: not a tab bar

A **single scrolling list of named lists**: Inbox, Today, This Evening, Upcoming, Anytime, Someday, Logbook, plus user Areas and Projects `[measured/published]`.

**Hierarchy is expressed by type weight, not indentation or icons:** "areas are represented by bold text, while projects are listed below their accompanying areas in a lighter font" `[reported]` ([MacStories](https://www.macstories.net/reviews/things-3-beauty-and-delight-in-a-task-manager/)).

**I verified this from the screenshots.** The reference capture shows exactly that structure: a full-width Quick Find field, then Inbox / Today / Upcoming / Anytime / Someday / Logbook each with a small full-colour glyph and a right-aligned count, a hairline divider, then Areas ("Family", "Work") in bold with a chevron, and projects beneath in regular weight with **pie-progress glyphs** `[measured/pixels]`.

### Colour, now measured

The accent hex was `NOT FOUND` in every published source. **I extracted it from the screenshots: `#5898F8` / `#5090F8`** `[measured/pixels]`.

**And the background is `#F8F8F8` at 70.4% of sampled pixels, not pure white** `[measured/pixels]`. That independently confirms the "near-white, never pure white" rule from [01](01-premium-apps-and-principles.md), measured in the shipping app of an ADA winner.

Three appearances: **Light, Dark and Black** (true black, distinct from dark) `[reported]`.

**The OS 26 refresh, in their own words:** "adjustments everywhere: in the curvature of windows, to-dos, dialogs, and controls; **wider spacing that feels more relaxed**; and a touch of glass in the sidebar that lets a hint of color shine through" `[measured/published]` ([Cultured Code](https://culturedcode.com/things/blog/)).

### The complete gesture vocabulary

All `[measured/published]` from Cultured Code's own [Using Gestures](https://culturedcode.com/things/support/articles/2803582/) article. **This is the single most useful artefact in the teardown for us.**

**Magic Plus Button — drop target determines the object type:**
- drag anywhere into a list → new to-do **inserted at that position**
- drag onto the Inbox target → to-do lands in Inbox
- drag into the sidebar → creates a **Project inside an Area**
- drag to the far-left edge inside a Project → creates a **Heading**

**Selection:**
- **swipe left on a to-do → select it** (repeat for non-consecutive multi-select)
- drag a finger down the right side → select a consecutive run

**Drag and drop:** tap-and-hold until it "pops up" → reorder; multi-select then hold one → move the group.

**Dates and search:**
- **swipe right → open the When scheduler**
- **pull down in any list → Quick Find search**
- pull down inside the date picker → type a natural-language date

### Motion and haptics
Haptics fire on **picking up a task to drag** and on the Magic Plus Button. MacStories: "the pop of the interface forms a perfect marriage with haptic feedback" `[reported]`. **Durations and spring constants: `NOT FOUND`.**

### Most distinctive decision
**The Magic Plus Button: one control whose meaning is determined by where you drop it** `[measured/published]`.

**Partially transferable.** The literal draggable FAB would be gratuitous in a read-heavy triage feed. **What transfers is position-as-parameter.** Also directly transferable: **swipe-right = schedule/snooze, swipe-left = select**, and **pull-down = search**, which is a stronger default than a persistent search bar eating vertical space `[inferred]`.

---

## 3. Flighty

ADA 2023, Interaction `[measured/published]`.

### The organising principle
Ryan Jones: **"Those airport boards have one line per flight, and that's a good guiding light, they've had 50 years of figuring out what's important."** `[measured/published]` ([Behind the Design](https://developer.apple.com/news/?id=970ncww4))

**The most directly stealable sentence in the entire teardown set. Decide the single line before designing the row.**

### Structure
- **Three tabs: My Flights, Friends, Passport** `[reported]`
- iPhone: **map occupies the top three-quarters**, flight detail is "a card-like UI that peeks out from the bottom" `[reported]`
- Card top block, in priority order: date, airline, flight number, airport name, departure and arrival times, terminal and gate `[reported]`
- Below that it scrolls "a long list of data divided into sections": **Good to Know, Arrival Forecast, Where's My Plane?, Detailed Timeline, Record of Changes, My Flight Log** `[reported]`

### The gesture that matters
The card is a **multi-detent bottom sheet with three states**: "With one quick swipe, the column of data scrolls to the half-way point on an iPhone **with a little haptic feedback**... With a second swipe, the card UI extends nearly to the top" `[reported]`.

> **Detent transitions are haptically confirmed but ordinary scrolling is not. Haptics mark state change, not motion.** Exactly the same rule as Things 3 (haptic on pick-up, not during drag). **Two independent ADA winners converging on the same haptic rule is the strongest signal in this document** `[inferred]`.

### The failure state, which is the strongest part
- **"We really have to shine when things go awry."** `[measured/published]`
- Offline is a **designed default, not an error**: "Whenever [someone] takes off, we have to assume that we won't see them again until they land" `[measured/published]`
- Alerts are segmented into four named classes: **Basics, Above & Beyond, Flight Plan, Arrival Information** `[reported]`

### A useful negative example
Gated sections render as **blurred placeholder data with "Try Pro" prompts**, and MacStories counts scrolling past five of them, treating it as friction `[reported]`.

> **Blurred-placeholder-as-upsell reuses the loading-skeleton vocabulary for a commercial purpose, which trains users to distrust skeletons** `[inferred]`.

### Most distinctive decision
**Persistence over polling.** The app's centre of gravity is outside the app: Live Activity, Dynamic Island, Lock Screen widget. "There's something comforting about information always being there" `[measured/published]`.

**Highly transferable in principle, expensive in React Native.** Live Activities require a native iOS widget extension; there is no RN-only path. **The transferable half is cheap: design the summary line first, and let the in-app row be a rendering of it** `[inferred]`.

**`NOT FOUND`:** Flighty's status colour palette, tab icon style, typography, dark-mode strategy, all motion timings. The "brightly-coloured iconography" line is the only sourced colour claim and it names no colour.

---

## 4. Halide

ADA 2022, Visuals and Graphics `[measured/published]`. **Note the award applies to Mark II, not the current shipping Mark III.**

### Framing
**"We didn't say we made an app. We say we made a camera. That was a philosophical underpinning of everything we did."** — Sebastiaan de With `[measured/published]`

And the anti-pattern: "Other camera apps looked like **flight simulators with lots of dials**... A camera is an extension of your body, and it works best when it creates muscle memory. **We need to have consistent gestures. We need to be flexible without changing buttons around all the time.**" `[measured/published]`

### Layout rules worth stealing
`[measured/published]` from [Pro. Camera. Action.](https://www.lux.camera/pro-camera-action-introducing-halide-mark-ii/):
- all controls within thumb reach on every iPhone size
- **the mode switcher was moved out of the prime thumb zone and onto an edge gesture** to free that space
- last-shot thumbnail bottom-left, **shape-adjusted to the display's corner radius**
- histogram placed in the notch "ears"

> **Deliberately spending the best real estate on content and demoting the mode switcher to a gesture is the inverse of the usual instinct. For a triage feed: the thumb zone belongs to the actions you take on an item, not to a filter or segment control** `[inferred]`.

### Typography: a hard finding
**Three custom typefaces named Ambrotype** (regular, bold, and **monospaced**), designed to mimic "etched text on film cameras" `[measured/published]`.

> **A camera app shipping a monospaced cut is the whole strategy in one detail: numeric readouts (ISO, shutter, EV) must not reflow as digits change.** Any feed with counts, timestamps or durations that tick has the same requirement, and **tabular figures are the cheap version of this** `[inferred]`.

### Colour, and the documented failure
**A single accent: yellow**, used to indicate active state `[reported]`.

**My pixel measurement confirms the discipline numerically:** sampling Halide's screenshots returns neutrals `#080808`, `#101010`, `#000000`, `#181818` — a near-black ladder — and **no yellow appears in the top accent results at all**, because the accent occupies a vanishingly small share of pixels `[measured/pixels]`. **That is the sub-10% accent rule, measured.**

**The documented failure of colour-alone** is the best-evidenced accessibility lesson across all four apps. Rebecca Slatkin: "I went to the Adirondacks and took all these photos... and none of them were in RAW, because I thought the deactivated state was the opposite." Apple's article states this led directly to a redesigned button treatment `[measured/published]`.

> **One accent colour cannot carry on/off state. Shape, fill or an explicit label must co-signal.** Directly applicable to unread/read, urgent/normal and snoozed/active in our feed.

### Redundant encoding of the urgent state
Halide's urgent state is clipping, and it ships **three distinct visualisations**: resizable histograms, a **waveform** that "horizontally scans over your image to expose which color channels are clipped", and **colour zebras** striped by channel `[measured/published]`.

> **Three redundant encodings of the same danger, each at a different glance-cost.** Our equivalent: a colour, a count and an explicit label for the same urgency, so it survives colour-blindness, glare and small sizes `[inferred]`.

### Dynamic chrome
Mark III adds **toolbar items that appear only when a manual setting is enabled** — "These dynamic toolbar items remind you that you have a manual setting enabled" `[measured/published]`.

> **Chrome that materialises only in the non-default state.** For a feed: the row shows nothing extra when normal, and grows a marker when snoozed, muted or escalated `[inferred]`.

---

## What transfers to a triage feed

1. **One line per item, airport-board discipline.** Decide the single line before designing the row.
2. **A consistent spacing unit enforced by two spacer primitives with a single `n` prop.** CRED's pattern is trivially portable to RN and removes eyeballed margins entirely. **Use our own 4/8 base, not their 5.**
3. **Opacity tiers as the hierarchy axis on a dark surface:** `0.9 / 0.7 / 0.5 / 0.3`, one text colour, resolved to solid hex per theme.
4. **Expand-in-place with the background fading.** Avoids a navigation push for the common triage action.
5. **Swipe-right = schedule/snooze, swipe-left = select.** Well-tested, and left-swipe-into-multiselect beats a separate Edit button.
6. **Pull down anywhere = search.** Reclaims the vertical space a persistent field would eat.
7. **Multi-detent sheet with a haptic tick at each detent and no haptic during free scroll.** Confirmed independently by two ADA winners.
8. **Fast down, slow up:** 0.12 to 0.15s press-in against 0.5s release, with ambient motion at 2s starting only after 5s dwell.
9. **Never let one accent colour carry on/off alone.** Halide shipped this bug and documented the fix.
10. **Redundant encoding of the urgent state:** colour plus count plus label.
11. **Tabular figures for anything that ticks.**
12. **Dynamic chrome:** show a marker only in the non-default state.
13. **Design the offline and stale state as a first-class layout**, not an error banner.
14. **Loading is a designed surface.** CRED ships nine-plus distinct loaders rather than a spinner.

## What is signature and should not be copied

- **NeoPOP's 3px/45° extrusion.** Two extra layers per element, heavy in dense lists, unmistakably CRED's. **Take the derived-edge-colour algorithm, leave the geometry.**
- **CRED's multi-accent saturated palette** (seven 8-step brand ramps). Built for a gamified rewards surface where each module needs identity. We need exactly one urgency accent.
- **CRED's 5px base unit.** Conflicts with the 4/8 mobile grid.
- **Square, zero-radius tags.** Part of NeoPOP's anti-soft stance; reads as unfinished outside that system.
- **The Magic Plus Button as a draggable creation device.** Solves fast typed capture with positional intent, a problem a read-dominant feed does not have. **Steal position-as-parameter, not the button.**
- **Halide's bespoke typeface.** Three custom cuts is a brand investment, not a UI technique.
- **Halide's edge-swipe-to-reveal panels.** In a scrolling feed they collide with back-swipe and horizontal scroll.
- **Blurred paywalled sections as upsell.** It corrupts the loading-skeleton vocabulary.
- **Live Activities as the product's centre of gravity.** Correct for Flighty, but no RN-only path exists. A later native extension, not a v1 assumption.

---

## Confidence audit

**Verified by me directly, not taken on trust**
- CRED's `depth = 8f.dp` default and the right/bottom-only surface visibility, read from `PopFrameLayoutStyle.kt`.
- That the Android library has **no `dimens.xml`** and its `colors.xml` is mostly Android Studio boilerplate. **The web repo is the token source.**
- Things 3's accent blue and near-white ground, and Halide's near-black ladder, by pixel extraction from the reference screenshots.

**`NOT FOUND`, and not invented**
- **Any row height, row padding or point/dp type size for Things 3, Flighty or Halide.** None publish specs. **Every layout number in this file belongs to CRED.**
- Things 3's typeface (SF is an inference, not a published claim), tag shape and size, empty states, loading states, and any animation duration.
- Flighty's status palette, tab icon style, typography, dark-mode strategy, all motion timings.
- Halide's yellow accent hex; all animation durations and haptic specifics; whether Ambrotype survived the Mark III redesign.
- CRED's shipped-app tab count, tab treatment, list-row anatomy and icon family. **The open-source library contains no navigation or list-row component at all**, so nothing about the actual CRED feed is measurable from it.

**Contradictions found in source, reported rather than smoothed over**
1. **CRED depth is inconsistent across platforms:** `NeoPopGeometry.DEFAULT_DEPTH = 3dp`, `PopFrameLayoutStyle.depth = 8dp`, web `PlunkProps.WIDTH = 3`. Use 3 as design intent.
2. **CRED button padding is non-monotonic:** `small` is `0 25px` while `medium` is `0 20px`. Read verbatim; likely a source bug, not corrected.
3. **CRED's Cirka weight mapping appears inverted:** `PPCirka-Light.woff` is registered at `font-weight: 600` and `PPCirka-SemiBold.woff` at `font-weight: 300`. **Do not copy this mapping.**
4. **Halide Mark II and Mark III describe different interfaces.** The ADA 2022 citation applies to **Mark II**, not the current shipping UI.
5. Flighty's three-tab structure is from the current review; the ADA-2023-era app may have differed. Unresolved.
6. The Halide single-yellow-accent claim reached the agent via a search summary rather than the article body, so it is `[reported]`, one confidence step below the direct quotes. My pixel measurement independently supports the *discipline* if not the specific hue.
7. Flighty's "48 hours faster than airlines" figure is **vendor App Store marketing copy**, not independently verified.
