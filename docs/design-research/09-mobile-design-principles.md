# Mobile design principles, and how each differs from web

**Date:** 2026-07-24
**Part of:** step 1 research, mobile-only pass.
**Why this file exists:** the first research pass imported web numbers. This file re-derives them from mobile sources and, in every section, states explicitly what is different on a phone. **Where this file and a round-one file disagree, this one wins.**

**Sourcing note:** Apple's HIG typography pages and `m3.material.io` specs are client-rendered and could not be fetched directly. Values were taken from retrievable canonical sources (the Material Components repos, Apple developer docs, WWDC sessions) or from credible secondary sources. **Anything that could not be confirmed is marked `[unverified]` rather than stated as fact.**

---

## 1. Type scale

**iOS Dynamic Type, default (Large) setting:**

| Style | Size |
|---|---|
| Large Title | 34pt |
| Title 1 | 28pt |
| Body (default) | **17pt** |
| Secondary | 15pt |
| Tertiary / caption | 13pt |
| Tab bar label | 10pt |
| **Absolute minimum** | **11pt** |

([learnui.design](https://www.learnui.design/blog/ios-font-size-guidelines.html), [Median](https://median.co/blog/apples-ui-dos-and-donts-typography))

**The size-category ladder:** 7 standard steps (xSmall to xxxLarge), plus **5 accessibility steps AX1 to AX5**, so 11 total. **Different text styles scale at different rates** between them ([Dept Agency](https://engineering.deptagency.com/ios-accessibility-part-1-dynamic-type)).

`[unverified]` The full per-style by per-AX matrix lives only in Apple's unfetchable HIG tables. **Do not hardcode AX values.** Read them at runtime via `PixelRatio.getFontScale()` in RN.

**Font family crossover:** SF Pro **Text** at ≤19pt, SF Pro **Display** at ≥20pt. Tracking varies from **−2.5% to +1.2%** across the range.

**Material 3 type scale:** Display 57/45/36sp, Headline 32/28/24, Title 22/16/14, Body 16/14/12, Label 14/12/11. Confirmed: displayLarge 57/64 line-height/−0.25 tracking, bodyLarge 16/24/+0.15. **Android minimum 12sp**, 14sp recommended for secondary, 16sp for body.

### How this differs from web

- **Web scales run to 48 and 64px for hero type. Mobile tops out around 34pt.** On a **390pt-wide** phone, a 48pt headline fits about 8 characters per line and a 64pt one about 6. It stops being typography and becomes a graphic. **Practical ceiling 34pt, with 28pt as the safe workhorse.**
- **iOS creates hierarchy with weight and position, not size.** The clearest demonstration: a page title is **34pt before scroll and 17pt after scroll**. It collapses into the nav bar at *body size* and stays distinguishable **through medium weight alone**. A web scale would never ask a title to survive at body size.
- **Fewer steps.** Mobile realistically uses six (34/28/17/15/13/11). Web ships 10 to 12 because it must span hero-to-caption across a 1440px viewport.
- **Web's 12px minimum does not transfer, and the reason is deeper than size.** A web `12px` is a *final rendered size*. An iOS `11pt` is **the bottom of a range whose top the user controls**, and it must hold even at the smallest setting. **Every mobile layout must survive text growing several hundred percent.** There is no default web equivalent of that constraint.

> **Impact on our proposal.** The six-step scale in [02](02-typography.md) (11/13/15/17/22/34) is **validated**: it matches Apple's real ladder almost exactly, and 34 is correctly the ceiling. **What must change: it has to survive Dynamic Type**, which our fractional `s()`-scaled sizes cannot, since they are fixed points with no scaling relationship.

---

## 2. Tab bars

**This is the single biggest gap in the round-one research, because web has no equivalent primitive at all. It is also our worst-looking component.**

### iOS baseline
- **Height 49pt** portrait, **83pt with the home indicator**. iPad 50pt.
- **Container 390x49pt. Icons 25x25pt. Labels 10pt.** At five tabs, item width is about **78pt**.
- **49pt exists precisely to clear the 44pt minimum touch target.**
- **3 to 5 tabs.** Beyond that iOS converts the last slot to a **"More" tab**. The guidance is blunt: More is a fallback, **not a plan**. Needing it means the IA is wrong.
- **Tabs stay enabled** when temporarily unavailable, rather than disappearing or greying out. Predictable position is the point.
- Selected = filled symbol, unselected = outline. `[unverified]` as an Apple mandate, but universally followed.

([uiuxdesigning](https://uiuxdesigning.com/ios-tab-bar/), [hacknicity](https://hacknicity.medium.com/ipad-navigation-bar-and-toolbar-height-changes-in-ios-12-91c5766809f4))

### iOS 26 Liquid Glass: the new premium bar
A genuine break, not a reskin:
- The tab bar **floats above content**, semi-transparent, **no longer glued to the bottom edge**, and reacts to background and lighting ([Donny Wals](https://www.donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/)).
- **Minimize on scroll:** `tabBarMinimizeBehavior(.onScrollDown)` collapses the bar and re-expands on reverse scroll ([WWDC25 323](https://developer.apple.com/videos/play/wwdc2025/323/)).
- **Bottom accessory view:** `tabViewBottomAccessory` sits above the bar (the Music mini-player pattern) and **animates down and blends into the bar when minimized** ([Create with Swift](https://www.createwithswift.com/enhancing-the-tab-bar-with-a-bottom-accessory/)).
- **Search gets its own role:** `Tab(role: .search)` renders a dedicated affordance separate from the standard tabs.

**Premium vs cheap, per the sources:** content must **flow underneath the floating bar with blur**, not be blocked by an opaque slab. Cheap now reads as: an opaque bar hard-docked to the edge, 6+ items or a More tab, icons without labels, custom heights that break 44pt.

> **Note the tension.** [06 §1](06-social-sentiment.md) found glassmorphism reads as AI slop. **That applies to glass used decoratively on arbitrary cards.** Apple's system-level Liquid Glass on the tab bar is different: it is platform furniture, applied by the OS, and it now signals *current* rather than *tacky*. **Use the platform's glass on the platform's chrome. Do not apply glass to our own cards.**

### Android bottom navigation
- **Height 80dp** in M3 (**64dp** in M3 Expressive). **Icons 24dp.** Labels 14sp Medium, bold when active.
- **Active indicator pill: 56 x 32dp, fully rounded, 4dp horizontal margin.**
- **3 minimum, 5 maximum.** Labels always shown at ≤3 items, selected-only at 4+.

([BottomNavigation.md](https://github.com/material-components/material-components-android/blob/master/docs/components/BottomNavigation.md))

### How this differs from web
Web has **no equivalent primitive**. A web app's global nav is a top bar or sidebar: it holds 8 to 12 items, has no touch-target floor, no OS-imposed height, no overflow convention and no motion contract. **Mobile's tab bar is OS-owned furniture** with fixed height, a hard item cap, and system-driven scroll behaviour you opt into rather than author. **Porting a multi-item web nav into a tab bar is the most common web-contamination failure there is.**

> **Our tab bar** has four items (Home, Sources, Later, You), which is correctly inside 3 to 5. **The icons are empty squares and circles.** At 25x25pt on a 78pt-wide item, sitting above a 10pt label, they are the most-seen graphics in the product. Fixing them is the highest-leverage change available.

---

## 3. Safe areas, thumb zones and reach

**Confirmed insets** ([Use Your Loaf](https://useyourloaf.com/blog/supporting-iphone-x/)):

| | iPhone 8 | iPhone X and later |
|---|---|---|
| Top inset | 20pt | **88pt** portrait |
| Bottom inset | 0 | **34pt** home indicator |
| Nav bar | 44pt | 44pt |
| Landscape side insets | 0 | **44pt each side** |

The 34pt bottom inset **grows when a tab bar is added**, which is where 49 + 34 = 83pt comes from. Dynamic Island is roughly 54pt tall plus ~5pt below `[unverified, from developer forum threads rather than an Apple spec]`.

### The thumb zone, with the correction that matters

Steven Hoober's original 2013 study ([UXmatters](https://www.uxmatters.com/mt/archives/2013/02/how-do-users-really-hold-mobile-devices.php)): **1,333 observations**, 780 involving screen contact. Grips: **one-handed 49%, cradled 36%, two-handed 15%.** One-handed splits right thumb 67% / left 33%.

**The important correction comes from Hoober himself.** He describes his own reach diagrams as "coarse and vague", derived from informally sampling coworkers and photos, and later said: **"please, please everyone ignore those drawings."** He warns the data cannot support claims about what percentage of people use phones a given way at a given moment, and that it captured no demographics, devices or tasks.

**So: cite the grip percentages. Do not cite the green/yellow/red heatmap as research.** The ubiquitous three-zone map is a design heuristic built on top of the study, not a finding of it. This matters because that heatmap gets quoted as fact constantly.

**What still holds:** roughly **75% of interaction is thumb-driven** and **49% is one-handed**, which is enough to justify bottom-anchoring primary actions. On a 390x844pt device the top ~200pt is a grip change away.

### How this differs from web
Two things with no web analogue.

**First, the OS physically occupies pixels you must not draw into:** 88pt top, 34pt bottom, 44pt per side in landscape. Web has viewport edges and nothing else; `env(safe-area-inset-*)` is a mobile-Safari retrofit of a mobile problem.

**Second, web inverts the anchoring.** A mouse reaches every pixel at equal cost, so web puts primary nav and CTAs **top-anchored**, because reading order beats reach. On a phone, top-anchored is **the worst location**: furthest from the resting thumb, and it forces a grip change. **Bottom-anchored primary actions are correct on mobile for a reason that does not exist on desktop web.**

---

## 4. Bottom sheets vs modals

**iOS `UISheetPresentationController` (iOS 15+):**
- **Detents:** `.medium()` rests at about half screen height; `.large()` is full-height and is the **default**. Supplying both lets the user drag between them ([Sarunw](https://sarunw.com/posts/bottom-sheet-in-ios-15-with-uisheetpresentationcontroller/)).
- **Grabber:** `prefersGrabberVisible`, **default false**. It is the affordance signalling resizability. **Turn it on whenever you ship more than one detent.**
- Sheets can **omit the dimming view**, keeping the background interactive. This is what makes a sheet a *companion* to content rather than an interruption of it.

**Material 3:** modal and standard variants share specs; **modal blocks the app, standard does not**. `BottomSheetDragHandleView` has a **48dp minimum width and height** to satisfy the touch-target rule, so **reserve ≥48dp at the top of the sheet** even though the visible bar is roughly 30x5dp.

**When a sheet beats a full-screen modal:** when the task is secondary to visible content, when the user needs the background in view, and when the interaction is short. Use a full-screen modal when the task is a distinct mode with its own commit and cancel.

### How this differs from web
Web defaults to a **centred dialog**, because the viewport is wide and the pointer is free, so a centred box is equidistant from everywhere and the page stays visible around all four edges. **On a phone a centred dialog is the worst of both:** it covers the middle where the content is, leaves useless slivers top and bottom, and puts its buttons mid-screen away from the thumb.

A sheet **enters from the reachable edge, keeps context above it, dismisses by gesture rather than a hunt for an ✕, and resizes by detent.** The web `<dialog>` element has no detent, no grabber and no drag-dismiss.

> **Our `DetailSheet` uses `height: '82%'`**, a single fixed height with no detents and no grabber. That is a web dialog wearing a sheet's clothes.

---

## 5. List rows and density

**iOS:** standard row **44pt**, subtitle row 60pt `[unverified for 60]`. 44 is firmly grounded because it is the same number as the minimum touch target.

**Material 3:** **one-line 56dp, two-line 72dp, three-line 88dp.** The source notes that deviating from these makes an app feel **"un-native"** ([getwidget](https://www.getwidget.dev/blog/top-10-best-flutter-list-tile-widgets/)). Useful framing: **on mobile, row height is a nativeness signal, not a taste choice.**

**Swipe actions:** SwiftUI's `swipeActions(edge:allowsFullSwipe:)` defaults to the trailing edge. **`allowsFullSwipe`** (swipe past a threshold to fire the primary action without lifting) **is one of the cheapest premium signals available** ([Use Your Loaf](https://useyourloaf.com/blog/swiftui-swipe-actions/)).

**How to make a feed denser on mobile:** **not** by shrinking rows below 44/56. By keeping row height and **reducing within-row content**: one line of primary text, secondary metadata as a single trailing element, actions moved into swipe rather than visible buttons. Section headers give scan structure without per-row chrome.

### How this differs from web
A web table row is **40 to 48px and can go lower**; 32px rows are common in dense data tables. Mobile cannot, because **the row is the touch target.** A 40px web row works because a cursor is a 1px point; a 44pt row exists because a fingertip contact patch is not.

The consequence: mobile shows roughly **half the rows per screen**. An 844pt phone fits about 14 rows at 44pt; a 900px web viewport fits about 22 at 40px. **Web solves density by shrinking rows. Mobile must solve it by removing content from rows and pushing actions into gestures.**

> **Direct application.** Our feed card carries a chip, a heading, a body block and two visible buttons. **Those two buttons should be swipe actions.** That is the mobile answer to density, and it is also how Things 3 does it.

---

## 6. Touch targets, and the absence of hover

- **Apple 44x44pt. Material 48x48dp (about 9mm).**
- A **30x30pt** target fails a meaningful share of users outright, and fails everyone when hands are cold, wet, or the user is moving.
- **Visual size and target size are separate.** Material's drag handle enforces a 48dp hit area behind a ~5dp visual. **Expand the target with padding or `hitSlop`; do not inflate the graphic.**

### The hover consequence: the sharpest divergence in this document

Web leans on hover for an enormous amount of work: revealing row actions, previews, tooltips, helper text, "this is clickable" signalling, and overflow menus. **A touchscreen has no hover state at all.** The first contact *is* the commit. Every one of those affordances must be re-solved:

| Web solves with hover | Mobile must use |
|---|---|
| Row actions appear on hover | **Swipe actions**, or an always-visible trailing chevron |
| Tooltip / helper text | **Always-visible** secondary label, or tap to reveal |
| Overflow "…" on hover | **Long-press** context menu, or a persistent affordance |
| Hover means "clickable" | Chevrons, elevation, colour, and **pressed states** |
| Progressive detail on hover | **Progressive disclosure**: sheets, expandable rows, drill-down |

Two constraints on the gesture answers:
1. **Never make a gesture the only path** to a function. Indicate it visually and keep a tappable route ([TestParty](https://testparty.ai/blog/mobile-accessibility-patterns)).
2. Because affordances cannot hide behind hover, **mobile screens carry more visible chrome per row than their web counterparts**, which compounds the density problem in §5.

> **This retires a round-one recommendation.** [06 §2](06-social-sentiment.md) quotes a designer saying "several icons can be hidden behind hover." **That advice is void for us.** Our equivalent is swipe, long-press, or a sheet.

---

## 7. Gestures: the premium signal with no web analogue

The canonical gestures: **pull-to-refresh** (invented by Loren Brichter in Tweetie), **swipe actions** on rows, and **edge-swipe back**, where the recognizer watches for a left-edge swipe and **drives the pop transition interactively**.

**Why gesture quality is the marker.** The interactive pop is the tell. A cheap implementation fires a fixed 350ms animation on release. **A premium one maps transition progress to finger position continuously**, so releasing halfway and reversing returns you where you were, and the animation can be grabbed again mid-flight.

Apple built explicit machinery for this: `UIViewPropertyAnimator` animations can be **scrubbed to any position and played backwards**, and `interruptibleAnimator(using:context:)` is the hook that makes a transition interruptible ([Apple](https://developer.apple.com/documentation/uikit/uiviewpropertyanimator), [Christian Selig on how hard this actually is](https://christianselig.com/2021/02/interruptible-view-controller-transitions/)). The design rationale is WWDC 2018 "Designing Fluid Interfaces", analysed in [Nathan Gitter's Building Fluid Interfaces](https://medium.com/@nathangitter/building-fluid-interfaces-ios-swift-9732bb934bf5).

**The two questions to ask of any gesture: does it track the finger 1:1, and can it be reversed or re-grabbed mid-flight?**

### How this differs from web
There is no web analogue. Web navigation is **discrete**: a click navigates or it doesn't, and browser back is a button press with a fixed result. There is no continuous, reversible, finger-tracked page transition on the web, no swipe-to-delete convention, and no pull-to-refresh (the browser owns overscroll). **A web app can be excellent without a single interruptible animation.**

**On mobile, gesture fidelity is often the entire difference between "feels native" and "feels like a wrapped website"**, and it is the first thing users perceive without being able to name it. Given our app already has swipe gestures, this is where a large part of the premium gain is available.

---

## 8. Haptics: probably the highest-ROI item on this list

| Generator | Use for |
|---|---|
| `impactAsync` (light / medium / heavy / soft / rigid) | A UI element engaging: snap-to, drag pickup and drop, toggle commit |
| `selectionAsync` | **Selection changing**: picker wheel, segmented control, slider notch |
| `notificationAsync` (success / warning / error) | The **outcome** of a task or action |

([Expo Haptics](https://docs.expo.dev/versions/latest/sdk/haptics/))

**Practical guidance:** Light, Medium and `selectionAsync` cover the large majority of worthwhile cases. **Avoid Heavy by default. "Dramatic isn't the same as good"** ([LogRocket](https://blog.logrocket.com/customizing-haptic-feedback-react-native-apps/)).

**Two implementation facts that bite:**
- `UIFeedbackGenerator` is **main-thread only**. Off-thread deactivation crashes ([expo/expo#19127](https://github.com/expo/expo/issues/19127)).
- **Call `prepare()` ahead of time** to remove first-tap latency. Without it the first haptic of a session lags noticeably.

**Evidence for perceived quality:** a 2026 study in the *International Journal of Consumer Studies* found haptic feedback in AR shopping apps **increased trust in the retailer and perceived usefulness of the app**, moderated by need for touch ([Wiley](https://onlinelibrary.wiley.com/doi/10.1111/ijcs.70189)). See also [ACM TOCHI, A Unified Model for Haptic Experience](https://dl.acm.org/doi/10.1145/3711842).

### How this differs from web
The Web Vibration API is a **blunt on/off motor buzz** with no impact styles, no selection generator and no notification semantics, and **it is unsupported on iOS Safari entirely**. Desktop web has no haptic channel at all.

**This is an entire perceptual dimension that exists only on mobile.** It is cheap to implement, immediately felt, and impossible for a competitor to screenshot. Combined with [06 §12](06-social-sentiment.md), where a user chose Breathwrk over a better-looking competitor *purely for its haptics*, this is the strongest single recommendation in the mobile pass.

---

## 9. Motion: springs, not durations

**iOS uses springs.** SwiftUI's default is **`response: 0.55, dampingFraction: 0.825`**. `response` controls speed; `dampingFraction` controls overshoot, lower being bouncier.

**Why springs, and this is the part that matters:**
1. **There is no point in a spring curve where the animation completes suddenly.** It settles asymptotically, which reads as physical rather than scheduled.
2. **Springs accept an initial velocity**, so a gesture-driven animation can hand its release velocity to the animation and continue without a visible seam. **A fixed-duration cubic-bezier cannot do this. It always starts from zero velocity, which is exactly why interrupted bezier animations look broken.**

Navigation transitions on iOS use **non-bouncy springs**.

**Reduce Motion** must be honoured: cross-fade instead of slide or scale. RN: `AccessibilityInfo.isReduceMotionEnabled()`.

### How this differs from web
Web motion is specified as **duration plus cubic-bezier** because web animation is overwhelmingly **discrete and non-interruptible**. That model is a poor fit for mobile, where much animation is **continuous with a user's finger** and must accept handoff velocity.

> **This retires a round-one recommendation.** [04 §8](04-proportion-spacing-icons.md) proposed a duration-and-easing token set (225ms enter, 195ms exit, cubic-bezier curves) taken from Material and web sources. **Porting a web duration/easing token set into React Native is a concrete symptom of web contamination:** it produces animations that are technically smooth and still feel wrong, because they always start from rest. **Use springs via Reanimated instead.** The frequency budget from [04 §8](04-proportion-spacing-icons.md) still stands; the curve specification does not.

---

## 10. Dark mode on mobile

- **OLED mechanism:** pixels are individually powered and **true black pixels are simply off**. This is why dark mode saves real power on OLED, unlike LCD.
- **But do not ship pure black everywhere:** pure `#000000` on OLED causes a **smearing artifact during scrolling**, because pixels take time to light back up. **Apple's own approach: `#000000` for the system background, `#1C1C1E` for elevated surfaces** ([design tokens guide](https://theswiftk.it.com/blog/swiftui-dark-mode-design-tokens-guide)).
- **Use semantic colours, not literals.**
- **Elevation without shadows is the key small-screen adaptation.** On a dark background a drop shadow is invisible: there is nothing darker to cast onto. Both iOS and M3 signal elevation in dark mode by **lightening the surface**. **Your light-mode shadow tokens have no dark-mode equivalent.** You need a parallel surface-tint ramp.
- RN: `useColorScheme()`.

### How this differs from web
Three reasons dark mode matters more on mobile:
1. **It has a physical payoff.** OLED power savings. On a desktop LCD, dark mode saves nothing.
2. **The OS owns the setting and users actually flip it**, often on a schedule. A mobile app that ignores `useColorScheme` looks broken next to every system app, whereas a web app defaulting to light is unremarkable.
3. **Elevation breaks.** Web dark mode often keeps its shadow tokens because desktop layouts separate surfaces with whitespace and borders across a wide viewport. **A phone stacks surfaces vertically with no room to spare, so layering must be carried by surface colour.** Mobile dark mode is a genuine second design system, not a colour-inverted skin.

> This reinforces [08 §6](08-mobile-apps.md), where Nubank's three documented fixes are effectively our checklist.

---

## 11. App icon and widgets: premium signals unique to mobile

**iOS 26 turned the app icon from an image into a document.** Xcode 26 ships **Icon Composer**, which builds **multi-layered** icons from Background / Midground / Foreground transparent PNGs. The system then applies Liquid Glass (blur, translucency, shadows, specular highlights) and generates every platform and appearance variant from a **single `.iconcomposer` file**.

- **Author at 1024x1024, but preview constantly at 60x60.** Recognisability at small size is the actual test.
- **The premium tell in 2026 is a properly layered icon that responds to system lighting**, versus a flat raster that renders inert next to system apps.

**Widgets** put the app's value on the home screen without a launch. `[unverified for specific sizing specs]`

### How this differs from web
A favicon is 32x32, static, and appears in a tab strip nobody looks at. **An app icon sits on the user's home screen at 60pt, permanently, adjacent to Apple's own icons, in four appearance modes, with system-applied lighting. It is the only piece of your UI a user sees when not using your app.** Neither it nor widgets has any web equivalent, and both are pure premium signal.

---

## 12. React Native and Expo: what is achievable, and what bites

**Well supported**
- Safe areas: `react-native-safe-area-context` / `useSafeAreaInsets`.
- Haptics: `expo-haptics` covers impact, selection and notification on both platforms.
- **Springs and interruptible gestures: `react-native-reanimated` + `react-native-gesture-handler`.** Interruptibility comes from **storing the initial position in the gesture context** so a gesture can pick an object up mid-animation ([Reanimated: handling gestures](https://docs.swmansion.com/react-native-reanimated/docs/fundamentals/handling-gestures/)).
- Dark mode: `useColorScheme()`.
- Native tabs: `expo-router` `NativeTabs` gives real platform tab bars.

**Known pitfalls, all sourced**
- **Variable fonts do not work in React Native.** Ship individual static weight files.
- **No font fallback stacks.** Passing an array uses only the first entry.
- **Font-name mismatches fail silently on iOS while appearing to work on Android.** The classic "works on my emulator" bug.
- **`expo-font` does not reliably respect `fontFamily` plus `fontWeight` together.** Register each weight as its own family name ([expo/expo#27647](https://github.com/expo/expo/issues/27647)).
- Prefer the **`expo-font` config plugin** (build-time embedding) over runtime `useFonts` to avoid the flash.
- **Do not mix `SafeAreaView` and `useSafeAreaInsets`.** They update at different times and cause flicker. Standardise on the hook.
- **`NativeTabs` pre-renders all tabs at launch**, so nested `SafeAreaProvider`s measure root insets first then re-measure with the tab bar, producing **a visible layout flash on first visit to each tab** ([expo/expo#42486](https://github.com/expo/expo/issues/42486)).
- **`UIFeedbackGenerator` is main-thread only.**

**Two things to verify before locking tokens, flagged rather than guessed:** RN `letterSpacing` takes **density-independent pixels, not em or percent**, so Apple's percentage tracking must be converted per font size; and `StyleSheet.hairlineWidth` is the correct value for 1-device-pixel separators rather than a hardcoded `1`. Neither could be confirmed against a retrievable source in this pass.

---

## What this file changes about the round-one recommendations

| Round-one recommendation | Status after the mobile pass |
|---|---|
| Six-step type scale 11/13/15/17/22/34 | **Validated.** Matches Apple's real ladder. But it must survive Dynamic Type, which fixed fractional sizes cannot. |
| Three weights, 400/500/600 | **Stands**, and is reinforced: iOS uses weight where web would use size. |
| Size-indexed negative tracking | **Stands**, but convert to RN's dp units per size, not em. |
| Duration + cubic-bezier motion tokens | **Retired.** Use springs via Reanimated. Web curves cannot accept handoff velocity. |
| "Hide some icons behind hover" | **Void.** No hover on mobile. Use swipe, long-press or a sheet. |
| Hairlines over shadows | **Stands and strengthens.** On a dark phone screen a shadow has nothing to cast onto. |
| Chip proportions from Material 3 | **Stands.** Material specs are in dp and mobile-native. |
| Nested radius formula | **Stands.** Pure geometry, medium-independent. |
| Linear's component padding (8/14 etc.) | **Do not use the absolute values.** Web-derived. Use the ratios with iOS/Material dimensions. |
| Motion frequency budget | **Stands**, and is reinforced by Family's delight budget in [08](08-mobile-apps.md). |

---

## Three gaps left open rather than guessed

1. **The full Dynamic Type per-style by AX1 to AX5 matrix.** Read it at runtime; do not hardcode.
2. **Material 3 line heights and tracking** beyond displayLarge and bodyLarge. Take them from the Compose `Typography` defaults.
3. **RN `letterSpacing` unit semantics and `hairlineWidth`.** Verify against the RN Text and StyleSheet docs before encoding tokens.

---

## Sources

[UXmatters, Hoober grip study](https://www.uxmatters.com/mt/archives/2013/02/how-do-users-really-hold-mobile-devices.php) · [Smashing, the thumb zone](https://www.smashingmagazine.com/2016/09/the-thumb-zone-designing-for-mobile-users/) · [Use Your Loaf, supporting iPhone X](https://useyourloaf.com/blog/supporting-iphone-x/) · [Use Your Loaf, SwiftUI swipe actions](https://useyourloaf.com/blog/swiftui-swipe-actions/) · [learnui.design iOS font sizes](https://www.learnui.design/blog/ios-font-size-guidelines.html) · [learnui.design Android font sizes](https://www.learnui.design/blog/android-material-design-font-size-guidelines.html) · [Median, Apple typography](https://median.co/blog/apples-ui-dos-and-donts-typography) · [Dept Agency, Dynamic Type](https://engineering.deptagency.com/ios-accessibility-part-1-dynamic-type) · [Sarunw, scaling custom fonts](https://sarunw.com/posts/scaling-custom-fonts-automatically-with-dynamic-type/) · [Sarunw, bottom sheets](https://sarunw.com/posts/bottom-sheet-in-ios-15-with-uisheetpresentationcontroller/) · [Create with Swift, tab bar accessory](https://www.createwithswift.com/enhancing-the-tab-bar-with-a-bottom-accessory/) · [Donny Wals, iOS 26 tab bars](https://www.donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/) · [WWDC25 323](https://developer.apple.com/videos/play/wwdc2025/323/) · [WWDC25 284](https://developer.apple.com/videos/play/wwdc2025/284/) · [uiuxdesigning, iOS tab bar](https://uiuxdesigning.com/ios-tab-bar/) · [hacknicity, iOS 12 bar heights](https://hacknicity.medium.com/ipad-navigation-bar-and-toolbar-height-changes-in-ios-12-91c5766809f4) · [Material BottomNavigation.md](https://github.com/material-components/material-components-android/blob/master/docs/components/BottomNavigation.md) · [M3 bottom sheets](https://m3.material.io/components/bottom-sheets/specs) · [M3 typography cheatsheet](https://medium.com/@vosarat1995/material-3-you-typography-cheatsheet-ffc58c540181) · [Compose Typography](https://composables.com/docs/androidx.compose.material3/material3/classes/Typography) · [getwidget, M3 list tiles](https://www.getwidget.dev/blog/top-10-best-flutter-list-tile-widgets/) · [mobileviewer, touch target size](https://www.mobileviewer.io/blog/touch-target-size) · [LogRocket, touch target sizes](https://blog.logrocket.com/ux-design/all-accessible-touch-target-sizes/) · [IxDF, tappability affordances](https://www.interaction-design.org/literature/article/how-to-use-tappability-affordances) · [TestParty, mobile accessibility patterns](https://testparty.ai/blog/mobile-accessibility-patterns) · [Apple, UIViewPropertyAnimator](https://developer.apple.com/documentation/uikit/uiviewpropertyanimator) · [Apple, swipeActions](https://developer.apple.com/documentation/swiftui/view/swipeactions(edge:allowsfullswipe:content:)) · [Christian Selig, interruptible transitions](https://christianselig.com/2021/02/interruptible-view-controller-transitions/) · [Nathan Gitter, building fluid interfaces](https://medium.com/@nathangitter/building-fluid-interfaces-ios-swift-9732bb934bf5) · [Wikipedia, pull-to-refresh](https://en.wikipedia.org/wiki/Pull-to-refresh) · [GetStream, SwiftUI spring animations](https://github.com/GetStream/swiftui-spring-animations) · [Hacking with Swift, spring animations](https://www.hackingwithswift.com/quick-start/swiftui/how-to-create-a-spring-animation) · [Expo Haptics](https://docs.expo.dev/versions/latest/sdk/haptics/) · [LogRocket, RN haptics](https://blog.logrocket.com/customizing-haptic-feedback-react-native-apps/) · [expo/expo#19127](https://github.com/expo/expo/issues/19127) · [Racat et al., IJCS 2026](https://onlinelibrary.wiley.com/doi/10.1111/ijcs.70189) · [ACM TOCHI, haptic experience](https://dl.acm.org/doi/10.1145/3711842) · [Software Mansion, haptics and trust](https://swmansion.com/blog/how-haptic-feedback-affects-sales-trust-and-product-perception/) · [Reanimated, handling gestures](https://docs.swmansion.com/react-native-reanimated/docs/fundamentals/handling-gestures/) · [MacRumors, dark mode battery](https://www.macrumors.com/2019/10/21/ios-13-dark-mode-extends-iphone-battery-life/) · [SwiftUI dark mode tokens](https://theswiftk.it.com/blog/swiftui-dark-mode-design-tokens-guide) · [offform, iOS 26 icon](https://www.offform.design/how-to-create-ios-26-icon-with-icon-composer/) · [Skyscraper, Liquid Glass icons](https://getskyscraper.com/blog/liquid-glass-app-icon-design-ios-26-guide) · [IconBundlr, icon sizes 2026](https://iconbundlr.com/blog/ios-app-icon-sizes-2026-complete-guide) · [Expo safe-area-context](https://docs.expo.dev/versions/latest/sdk/safe-area-context/) · [Expo Fonts](https://docs.expo.dev/versions/latest/sdk/font/) · [Expo native tabs](https://docs.expo.dev/router/advanced/native-tabs/) · [React Navigation safe areas](https://reactnavigation.org/docs/handling-safe-area/) · [expo/expo#42486](https://github.com/expo/expo/issues/42486) · [expo/expo#27647](https://github.com/expo/expo/issues/27647) · [Ibukun Ogundipe, RN fonts](https://medium.com/@ibukunogundipe2/mastering-font-families-in-react-native-expo-the-ultimate-guide-d5db2e3cc299)
