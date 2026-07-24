# Design system v2

**Date:** 2026-07-24
**Status:** the implementable rule set. This is the contract.
**Supersedes:** [`design-system.md`](design-system.md), which is **retired**. Do not implement against it.

---

## Why the old spec is retired

`design-system.md` was labelled "locked" and declared itself "the contract for the mobile UI". It never matched the code. It specifies a cool-grey, green-accented, dual-mode panel; [`mobile/src/theme.ts`](../mobile/src/theme.ts) ships a warm-cream, slate-accented, light-only one with drop shadows the spec bans. Two designs, one repo, and the audit found the divergence is the reason every recent commit has been a correction.

Retiring it deliberately, rather than reconciling it, is the point. **Where this file and any other design document disagree, this file wins.**

The evidence behind every rule below is in [`design-research/`](design-research/). The five-rule formula is [16](design-research/16-what-visually-rich-actually-means.md); the defect list it fixes is [00](design-research/00-current-state-audit.md); the mobile constraints are [09](design-research/09-mobile-design-principles.md).

---

## 0. The direction, in one paragraph

**Type A with a thin material layer.** Near-black canvas, dense data, one luminous accent, gradient washes tied to meaning: all of it built in code. Material arrives through gradients, SVG, grain and Lottie, applied **once per screen**, never as ambient decoration. No commissioned 3D, no stock photography, no spot illustration.

The research reason for the ceiling: every app that renders real material inside the product has a physical object to render. CRED has a credit card, Oura a ring, WHOOP a band. Across ~180 apps swept, companies overwhelmingly render metal for the App Store screenshot and ship a flat app behind it. **We have no physical product**, so inventing a hero object with no referent would be cost without payoff.

---

## 1. Colour

### The ladder logic

Dark is the default. Light is the alternate. Both are authored as a **lightness ladder on a neutral axis**, with hue arriving only through the accent and the alarm.

**Elevation is carried by surface lightness in dark, and by hairlines in light. Shadows are banned in both modes.** On a near-black canvas a drop shadow has nothing to cast onto, so a light-mode shadow token has no dark-mode equivalent at all. This is the single rule that most reliably separates a real dark theme from an inverted light one.

### Dark (default)

| Token | Hex | Use |
|---|---|---|
| `canvas` | `#0A0A0A` | The app background. Everything sits on this |
| `surface` | `#121212` | A card or a filled row |
| `surfaceRaised` | `#1A1A1A` | A card that outranks its neighbours; sheet background |
| `surfaceOverlay` | `#232323` | Pressed states, sheet handles, inline chips |
| `hairline` | `#2B2B2B` | Separators. Always `StyleSheet.hairlineWidth` |
| `border` | `#383838` | A visible edge on an interactive element |
| `textFaint` | `#545454` | Disabled. Decorative only, never information |
| `textLow` | `#757575` | Tertiary metadata |
| `textMid` | `#A0A0A0` | Secondary text, subtitles |
| `textHigh` | `#F2F2F2` | Primary text |

**Not pure `#000000`.** Pure black on OLED smears during scrolling because pixels take time to relight. `#0A0A0A` keeps the near-black read without the artifact, and it matches what pixel measurement found in the references: Halide runs `#080808 → #101010 → #181818`, CRED `#0d0d0d → #101010 → #181818` ([15](design-research/15-measured-palettes.md)).

### Light (alternate)

| Token | Hex |
|---|---|
| `canvas` | `#F7F7F6` |
| `surface` | `#FFFFFF` |
| `surfaceRaised` | `#FFFFFF` |
| `surfaceOverlay` | `#EFEFED` |
| `hairline` | `#E6E6E4` |
| `border` | `#D6D6D3` |
| `textFaint` | `#A3A3A0` |
| `textLow` | `#8A8A87` |
| `textMid` | `#5C5C59` |
| `textHigh` | `#141414` |

### Authoring rule for text

Author the hierarchy as alpha (`0.95 / 0.66 / 0.46 / 0.33`) to reason about it, then **resolve to solid hex per theme and ship the hex**. Never ship `rgba()` text. Translucent text composites differently over every surface in the ladder, so the same token silently changes contrast depending on what it lands on: exactly the kind of drift that makes an interface look unmaintained.

> **Verify before locking.** The pairs above are designed against APCA targets of **Lc 90 for body and Lc 60 for secondary** ([03](design-research/03-colour-dark-and-light.md)). I have not run every pair through a calculator. Run all of them and adjust the ladder, not the individual usage, if any fall short.

### The two hues

Everything else is neutral. **One accent and one alarm, and no screen shows more than two hues.** This is formula rule 4: colour arrives as atmosphere tied to meaning, never as a palette of equal-weight chips.

| Role | Dark | Light | Means |
|---|---|---|---|
| `accent` | `#5FE3C0` mint | `#0E8F72` | Yours, active, progress, done |
| `alarm` | `#FF5A5F` coral | `#D9342B` | Urgent. Someone is blocked on you |

The mapping onto the product falls out cleanly, and it is the reason to prefer mint over the alternatives:

- **Urgent** → alarm
- **By you** → accent
- **Can wait** → neutral, no hue at all

**The accent stays under ~2% of screen pixels.** It is a light source, not a fill. The moment it becomes a background for large areas it stops reading as luminous.

There is a narrative payoff worth protecting: as work clears, the screen moves from coral toward mint. The gamified layer therefore needs no new colour, because progress is already the accent.

### Accent alternatives, if mint is wrong

| Option | Value | Why | Cost |
|---|---|---|---|
| **Mint (recommended)** | `#5FE3C0` | Alpian and SwissBorg use it on near-black. Calm, private-bank, and maximally distant from the alarm hue | None |
| Electric lime | `#C8F751` | WHOOP and Othership. More gamified, more energetic | Louder; harder to keep under 2% |
| Amber gold | `#F0A94A` | Slash and Zolve. Warmest, closest to the current Warm Sand heritage | **Collides with the alarm hue.** Picking it forces the alarm to move to magenta or violet, which reads less like danger |

### Source tints

Per-context tinting is the one mechanic the rich apps keep independently reinventing: Rainbow recolours all chrome to the active wallet, Oura shifts with biometrics, Arc Search tints to the site. **For us it tints to the source being triaged**, which is information and atmosphere at once ([16](design-research/16-what-visually-rich-actually-means.md)).

| Source | Tint |
|---|---|
| `github` | `#A371F7` violet |
| `linear` | `#5E6AD2` indigo |
| `slack` | `#36C5F0` cyan |
| `google_docs` | `#4285F4` azure |
| `calendar` | `#34A853` green |
| `gmail` | `#EA4335` coral-red |

Three constraints, and the third is not optional:

1. A tint appears **only** as a radial wash at **6–10% opacity** behind the top edge of a card, and as the brand mark's own colour. It never fills a surface, never colours text, never colours a border.
2. One tint per card. Never two on one screen except in the Feed, where each full-screen card owns its own.
3. **Gmail's tint sits next to the alarm hue.** That adjacency is real and must not be papered over. It is safe only because tier is never carried by colour alone: form and tag carry it, and the source tint appears in a different position (behind the mark) from the tier signal (the leading edge). If the two ever land in the same position, the tint loses.

---

## 2. Typography

### Faces

**No system sans at default weight anywhere.** Formula rule 3, and the cheapest single upgrade available: none of the apps that rate 5/5 use it, and it is precisely why Things 3, Structured and Streaks read as unfinished despite excellent craft.

| Role | Face | Licence |
|---|---|---|
| UI and text | **Geist** 400 / 500 / 600 | OFL |
| Numerals, timestamps, refs | **Geist Mono** 400 / 500 | OFL |
| Display | **Archivo** 600, and **Archivo Condensed** 600 for uppercase labels | OFL |
| One greeting line per screen | **Instrument Serif** Regular | OFL |

All four are SIL Open Font Licence, so they can be embedded and shipped with no attribution burden in-app and no commercial restriction.

**`Menlo` is retired.** It is a 2009 terminal face and it currently sets every timestamp, count, label, tag and divider in the app, which is a large share of why the UI reads as a developer default.

**The mono signature survives, narrowed.** Mono is for things that are genuinely machine values: counts, timestamps, relative ages, IDs and refs. It is **not** for eyebrows, tier tags or section labels: those are Archivo Condensed in uppercase. The old theme used mono for all of them indiscriminately, which is what turned a signature into a texture.

**The serif is rationed to one line per screen**: the greeting on Your Day, and nothing else. This is Investec's move: strict monochrome everywhere, a serif greeting as the single warm moment. Used twice on a screen it stops being a moment.

### Scale

Six steps, plus one graphic exception. This matches Apple's real Dynamic Type ladder, and 34 is correctly the ceiling for text: on a 390pt phone a 48pt headline fits about eight characters and stops being typography.

| Role | Size | Line height | Tracking (dp) | Weight | Face |
|---|---|---|---|---|---|
| `hero` | 56 | 56 | −1.4 | 600 | Archivo |
| `display` | 34 | 40 | −0.7 | 600 | Archivo |
| `title` | 22 | 28 | −0.4 | 600 | Geist |
| `heading` | 17 | 24 | −0.1 | 600 | Geist |
| `body` | 15 | 20 | 0 | 400 | Geist |
| `secondary` | 13 | 20 | +0.1 | 400 | Geist |
| `label` | 11 | 16 | +0.8 | 600 | Archivo Condensed, uppercase |

**`hero` is a graphic, not a text style.** One per screen, numerals only, and it is the only role permitted above 34. Note that the "~72pt hero numeral" often attributed to WHOOP is an unmeasured estimate from a marketing post, not a spec: 56 is our own choice, not a copied number.

**Tracking is in dp, not em.** React Native's `letterSpacing` takes density-independent pixels, so Apple's percentage tracking has to be converted per size. The values above are already converted. Deriving new ones: `dp = size × percent ÷ 100`.

**Line heights sit on a 4pt grid** so text blocks stack predictably against the spacing scale.

**Three weights only: 400 / 500 / 600.** The current app ships two, which is why hierarchy is being asked to come almost entirely from ten barely-distinguishable sizes while the strongest lever goes untouched. iOS creates hierarchy with weight and position where web uses size: a page title survives collapsing from 34pt to 17pt on scroll through medium weight alone.

### Numerals

`fontVariant: ['tabular-nums']` on **everything that ticks or aligns in a column**: counts, times, durations, stat tiles. Proportional figures make a number jitter horizontally as it changes, which is a small thing that reads as cheap every single time.

### Dynamic Type

Every layout must survive text growing several hundred percent. An iOS `11pt` is not a rendered size, it is the bottom of a range the user controls.

- Read the scale at runtime with `PixelRatio.getFontScale()`. **Never hardcode the AX1–AX5 matrix**; it exists only in Apple's unfetchable HIG tables.
- `body`, `secondary`, `heading` and `title` scale **fully**.
- `display`, `hero` and `label` scale to a **cap of 1.3×**, because they are graphic elements whose job is composition. Clamp, do not disable.
- **`allowFontScaling={false}` is banned** everywhere except `hero`.

### React Native font traps

All four of these are real, sourced, and cost hours if hit late ([09 §12](design-research/09-mobile-design-principles.md)):

- **Variable fonts do not work.** Ship individual static weight files.
- **No fallback stacks.** Passing an array uses only the first entry.
- **`expo-font` does not reliably respect `fontFamily` + `fontWeight` together.** Register each weight as its own family (`Geist-Regular`, `Geist-Medium`, `Geist-SemiBold`) and never rely on `fontWeight` to select a file.
- **Font-name mismatches fail silently on iOS while appearing to work on Android.** The classic "works on my emulator" bug. Verify on a real iOS build before assuming a weight loaded.

Prefer the **`expo-font` config plugin** (build-time embedding) over runtime `useFonts`, to avoid the first-paint flash.

---

## 3. Spacing

```
4  8  12  16  24  32  48  96
```

Eight values. Nothing else. The current app uses roughly nineteen ad-hoc values covering nearly every integer from 2 to 16, each multiplied by 1.379, so no two gaps in the app are deliberately related. **That is the mechanism behind "we have the components but we don't have the proportionality."** The eye does not consciously measure, but it reliably detects the absence of repetition.

- **Screen gutter: 16.** One value, every screen.
- **Within a card: 16.** Between cards: 12.
- **Between sections: 32.** Above a section label: 48.
- **96** is for one thing: the empty space that makes a hero moment land.

Ship two spacer primitives, `<VStack n>` and `<HStack n>`, taking a scale index rather than a number. If a gap cannot be expressed on the scale, the layout is wrong; do not add a value.

**Delete `SCALE` and `s()`.** Every size in the app is currently an arbitrary mockup measurement times 1.379, so nothing lands on a whole point. Sub-pixel rendering at fractional sizes softens stem weights unevenly, which is a real contributor to text looking mushy rather than crisp.

---

## 4. Radii

| Token | Value | Use |
|---|---|---|
| `xs` | 4 | Tags, pips, inline marks |
| `sm` | 8 | Chips, buttons, small tiles |
| `md` | 12 | Rows, stat tiles |
| `lg` | 16 | Cards, sheets |
| `pill` | 999 | Segmented controls and filter pills only |

Five values replacing eleven. The current set includes 15.2 / 16.5 / 19.3 / 20.7, which all read as "roughly the same rounded corner" and therefore communicate no difference in elevation while conspicuously failing to match.

**Nested radii are derived, never chosen:**

```
inner = outer − padding
```

A card at `lg` (16) with 16 padding contains children at **0**. A card at `lg` with 12 padding contains children at **4**. If the result is negative, the child is square. Unmanaged concentric corners are one of the most reliable tells of unrefined work, and the current app has a radius-20.7 card with padding 16.5 containing a radius-5.5 tag.

---

## 5. Chips and tags

One chip shape. The app currently ships three, with three paddings and two competing radius philosophies.

| | Value |
|---|---|
| Height | **28** (min touch target expanded to 44 via `hitSlop`, never by inflating the graphic) |
| Padding | 10 horizontal, 0 vertical (height does the work) |
| Radius | `sm` (8) |
| Type | `label`, 11pt Archivo Condensed 600, uppercase, +0.8 tracking |

**Not pill-shaped.** Material's own chip spec is an 8dp radius at a 32dp minimum height, and pills read as filter controls. Reserve `pill` for things that genuinely are filters.

Three variants, and the difference is fill, not shape:

- **Solid**: accent or alarm background, `canvas` text. For the tier tag on an urgent card. One per card.
- **Outline**: `border` stroke, `textMid` text, no fill. Default.
- **Ghost**: no stroke, no fill, `textLow` text. For metadata that is not a control.

---

## 6. Icons

**Phosphor** (`phosphor-react-native`), one family, no exceptions.

Chosen over Lucide for one specific reason: Phosphor ships six weights including `regular` and `fill`, which maps directly onto the iOS tab bar convention of **outline when unselected, filled when selected**. With a single-weight family that state change has to be faked with colour, and colour alone is not enough.

| Context | Size | Weight |
|---|---|---|
| Tab bar | 25 | `regular` / `fill` when selected |
| Row leading | 20 | `regular` |
| Inline with `secondary` text | 16 | `regular` |
| Action button | 20 | `bold` |

**Stroke weight scales with size**, which Phosphor handles internally. Do not scale an SVG up and leave the stroke thin.

**Optical sizing:** a circular glyph needs to be ~10% larger than a square one to read at the same size. Material's own keylines put the square at 18dp and the circle at 20dp. Trust the eye over the box.

Two things this replaces:

- **The tab bar icons are currently empty squares and outlined circles.** Four navigation items, four geometric primitives, no semantic content. They sit at the bottom of every screen and are the most-seen graphics in the product. This is the highest-leverage single fix in the app.
- **Source identity is currently two-letter monogram tiles** (`SL`, `GH`, `LN`) on washed pastel backgrounds. Text-in-a-box is a fallback pattern, not an icon system. Replace with real brand marks (see §9).

---

## 7. Motion

**Springs, via Reanimated. Not durations, not cubic-bezier.**

This retires the duration-and-easing token set proposed in [04 §8](design-research/04-proportion-spacing-icons.md), which was taken from Material and web sources. **Porting a web duration/easing set into React Native is a concrete symptom of web contamination:** it produces animations that are technically smooth and still feel wrong.

Two reasons, and the second is the one that matters:

1. A spring has no point at which it completes suddenly. It settles asymptotically, which reads as physical rather than scheduled.
2. **A spring accepts an initial velocity.** A gesture can hand its release velocity to the animation and continue with no visible seam. A fixed-duration bezier always starts from zero velocity, which is exactly why interrupted bezier animations look broken.

| Token | Config | Use |
|---|---|---|
| `snappy` | `{ damping: 26, stiffness: 340, mass: 0.9 }` | Chips, toggles, taps |
| `standard` | `{ damping: 22, stiffness: 190, mass: 1 }` | Cards, sheets, most things |
| `gentle` | `{ damping: 30, stiffness: 110, mass: 1 }` | Full-screen transitions |

Derived from SwiftUI's default (`response: 0.55, dampingFraction: 0.825`). **Navigation transitions use non-bouncy springs**: keep damping high enough that nothing overshoots on a screen change.

### The two questions every gesture must answer

1. **Does it track the finger 1:1?**
2. **Can it be reversed or re-grabbed mid-flight?**

Interruptibility in Reanimated comes from **storing the initial position in the gesture context**, so a gesture can pick an object up mid-animation. Release halfway through a Feed card swipe and reverse, and it must return where it came from. This is the difference between "feels native" and "feels like a wrapped website", and it is the first thing users perceive without being able to name it.

### Budget

**The feed row is the highest-frequency surface in the product, so it gets the most restraint.** Delight is spent where it is rare: clearing the last urgent item, a streak landing, a source connecting. An animation the user sees forty times a day must be under 200ms of perceived settle and must never block input.

**Honour Reduce Motion** via `AccessibilityInfo.isReduceMotionEnabled()`. Cross-fade instead of slide or scale.

---

## 8. Haptics

`expo-haptics`. **Haptics mark a change of state, never motion.** A haptic that fires continuously during a drag is noise; one that fires at the moment a card commits is information.

| Event | Call |
|---|---|
| Tier filter changes, segmented control moves | `selectionAsync()` |
| Card swipe passes the commit threshold | `impactAsync(Light)` |
| Snooze, mark read, toggle commits | `impactAsync(Medium)` |
| Action succeeded | `notificationAsync(Success)` |
| Action failed | `notificationAsync(Error)` |
| Last urgent item cleared | `notificationAsync(Success)` + the one Lottie moment |

**Never `Heavy`.** Dramatic is not the same as good.

Two implementation facts that bite:

- **`UIFeedbackGenerator` is main-thread only.** Off-thread deactivation crashes ([expo/expo#19127](https://github.com/expo/expo/issues/19127)). Fire haptics from the JS thread, not from inside a Reanimated worklet without `runOnJS`.
- **Call `prepare()` ahead of time.** Without it the first haptic of a session lags noticeably.

This is the highest-ROI item on the list: cheap, immediately felt, and impossible for a competitor to screenshot.

---

## 9. Assets: the material layer

This is the explicit boundary on how far the material direction goes.

### Permitted

| Asset | Package | Use |
|---|---|---|
| Gradient washes | `expo-linear-gradient` | Formula rule 4. Source tints, tier fields |
| Radial glows, rings, gauges, etched patterns | `react-native-svg` *(already installed)* | The hero object. Ring gauges, guilloché-style line fields |
| One hero animation | `lottie-react-native` | Exactly one per app, for a rare moment |
| Grain overlay | A single tiled 128×128 PNG at 3–5% opacity | See below |
| Real brand marks | **Simple Icons** (CC0) | Source identity |
| Platform blur | `expo-blur` | **Tab bar only** |

**Grain is the cheapest expensive trick there is.** A gradient on an 8-bit display bands visibly; a few percent of monochrome noise over it destroys the banding and simultaneously reads as film, paper or brushed metal. One tiled PNG, one `<Image>` at low opacity, applied over every gradient in the app.

**Brand marks:** Simple Icons ships the SVG paths CC0, so there is no copyright constraint. **Trademark policy is separate from copyright and still applies**: using a mark to identify the service it belongs to is exactly the permitted use, and that is all we do. Do not restyle, recolour arbitrarily, or use a mark as decoration.

### Forbidden

- **Bespoke 3D renders.** No referent, real ongoing asset cost, and almost nobody else achieves it either.
- **Stock photography.** The 5/5 apps use photography as a *material* with real art direction (a mountain inside a score card, mist inside a session card). Generic stock reads worse than none.
- **Spot illustration.** The single strongest visual dividing line between the 5/5 set and the 2/5 set.
- **Glass on our own cards.** [06 §1](design-research/06-social-sentiment.md) found glassmorphism now reads as AI slop, and Dribbble's own engagement data shows restrained system shots outperforming glass effect shots by roughly 10–20×. **Use the platform's glass on the platform's chrome, never on our own surfaces.** The tab bar is furniture the OS owns; a card is not.

### One material object per screen

Formula rule 2, and the discipline that makes it work: **one hero object with real light, and flat UI around it.** Not decoration everywhere.

Since we have no physical product, the hero object is the data itself:

- **Your Day** → the **day arc**. An SVG ring or arc whose stroke is a gradient from alarm to accent, showing the shape of the day's load. Oura's and WHOOP's move, and it is the natural home for the gamified layer.
- **A Feed card** → the **source glow**. A radial wash in the source tint behind the brand mark, the mark itself rendered on a dark tile with a one-pixel specular top edge.
- **Activity, per source** → the **hero numeral** plus one sparkline.

Everything else on those screens stays flat.

---

## 10. Rules that are not about tokens

These came out of the teardowns and each one is a specific failure someone else already shipped.

1. **Colour alone cannot carry state.** Halide's documented failure. Every tier, status and selection must differ in **form** as well as hue, and must survive a greyscale screenshot.
2. **A filled dot reads as a notification badge.** Use an **outline** for "you are here" and reserve the filled dot for "there is something new". The app currently uses a filled pip for tier, which competes with the meaning it will need later.
3. **Never fake an empty state as a full one.** The highest-severity trust failure found in the whole research effort. No placeholder rows, no sample data, no skeleton that resolves into nothing.
4. **No hover exists.** Every affordance is swipe, long-press, or always visible. **And no gesture is ever the only path to a function**: indicate it visually and keep a tappable route.
5. **Density is a feature.** Small sizes, hairline rules, tiny uppercase labels, a lot of information at once. The expensive feeling comes from confidence that the user can handle it. This reverses the usual whitespace advice, which was measured on websites and light apps.
6. **Row height is a nativeness signal, not a taste choice.** 44pt minimum, 56 one-line, 72 two-line. **Do not create density by shrinking rows**: the row is the touch target. Create it by removing content from rows and pushing actions into gestures.
7. **Bottom-anchor primary actions.** Roughly 75% of interaction is thumb-driven and 49% is one-handed. (Cite the grip percentages from Hoober's study; **do not cite the green/yellow/red reach heatmap**, which Hoober himself asked people to stop using.)
8. **Sheets get detents and a grabber.** `DetailSheet` currently uses `height: '82%'`, a single fixed height, no detents, no grabber. That is a web dialog wearing a sheet's clothes.

---

## 11. Token layer shape

```
theme/
  primitives.ts   // raw ladders: greys, mint, coral, source hues. No meaning.
  semantic.ts     // canvas, surface, accent, alarm, textHigh... × { dark, light }
  type.ts         // the 7 roles, with the Dynamic Type clamp baked in
  space.ts        // the 8 values + the 5 radii
  motion.ts       // the 3 springs
  haptics.ts      // the event map
  index.ts        // useTheme() → resolved semantic tokens for the active mode
```

Two layers, and the separation is the point. **Components import semantic tokens only.** A component that reads `primitives.mint400` has hardcoded a decision it does not own, and it will be wrong in the other mode.

Mode comes from `useColorScheme()`, defaulting to dark, with an explicit override persisted in `AsyncStorage` so a user can pin light regardless of the system.

---

## 12. Packages to add

Currently installed and sufficient: `react-native-svg`, `react-native-safe-area-context`.

```
react-native-reanimated
react-native-gesture-handler
expo-haptics
expo-linear-gradient
expo-blur
expo-font
lottie-react-native
phosphor-react-native
```

**A trap in the brief does not apply here.** Expo's `NativeTabs` is alpha and breaks with `FlatList` (scroll-to-top and minimize-on-scroll unsupported, scroll-edge detection failing so the bar renders transparent). **We are not on it.** The app uses `@react-navigation/bottom-tabs` v7, which takes a `tabBar` prop and hands over full control of the bar. We build it ourselves and the alpha risk never arrives.

One real trap that does apply: **do not mix `SafeAreaView` and `useSafeAreaInsets`.** They update at different times and cause flicker. The app currently uses `SafeAreaView` throughout; standardise on the hook.

---

## 13. What this fixes, against the audit

| Audit finding | Rule |
|---|---|
| Placeholder tab-bar icons | §6, Phosphor with fill-on-select |
| Ten type sizes, gaps under 1pt, two weights | §2, seven roles and three weights |
| ~19 spacing values, 11 radii, unmanaged nesting | §3, §4 |
| Spec/implementation divergence, no dark mode | §1, §11, and this file retiring the old one |
| Three chip shapes | §5, one shape and three fills |
| Muddy palette, monogram fallbacks | §1, §9 |
| Box-in-box, no focal point | §9, one material object per screen |
| Shadows despite being banned | §1, elevation by surface lightness |
| `Menlo` | §2, Geist Mono, narrowed to machine values |
