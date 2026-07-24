# Research: proportion, spacing, shape, icons and motion

**Date:** 2026-07-24
**Part of:** step 1 research. This is the file that most directly answers "why do the chips and icons look wrong".

> ### ⚠ Medium caveat: mixed web and mobile sources
>
> **Stands for mobile:** the Material 3 chip specs (dp, mobile-native), Apple's 44pt row and tap-target figures, the Material icon keylines, SF Symbols weight matching, the nested-radius formula (pure geometry, medium-independent), and the Material motion tokens.
>
> **Web-derived, do not take the absolute numbers:** Linear's component padding (8/14 button, 6/14 tab pill, 24 card), the Tailwind and Carbon spacing scales, and the border and shadow values, all of which come from web systems. The *ratios* hold; the absolute values need mobile validation.
>
> **Missing entirely, because it has no web equivalent:** tab bars, safe areas, thumb zones, bottom sheets, swipe actions, haptics, and the fact that **mobile has no hover state**, so every affordance web solves with hover must be solved another way. All of that is in [09-mobile-design-principles.md](09-mobile-design-principles.md). Where the two disagree, the mobile file wins.

---

## 1. Spacing: adopt a scale, do not invent values

**Why 4 and 8.** Every layout value is a multiple of 8 (8, 16, 24, 32, 40, 48), with 4 as a half-step for tight relationships like icon-to-label. The reason 4 and not 5 or 6: "8pt increments are the right balance of being visually distant while having a reasonable number of variables", and when an icon and its label are pushed to 8pt apart they read disconnected, so 4pt keeps them cohesive ([Bootcamp](https://medium.com/design-bootcamp/designing-in-the-8pt-grid-system-f3c1183ea6e8)).

**What our 4.1 / 8.3 / 12.4 / 17.9 values actually break.** Three concrete failures, all caused by the 1.379x scale factor:

1. **Sub-pixel rendering.** On a 3x iPhone, 8.3pt is 24.9px. RN rounds to device pixels, so nominally equal gaps land on different physical pixels: two "equal" gaps become visibly unequal, and 1px hairlines at fractional offsets go blurry or drop out entirely.
2. **No perceivable difference.** 4.1 vs 4.0 is not a decision, it is noise. The grid's real value is decision elimination: "instead of agonizing over whether a button needs 13px or 15px of padding, the grid narrows your choices" ([Rejuvenate](https://www.rejuvenate.digital/news/designing-rhythm-power-8pt-grid-ui-design)).
3. **Broken concentricity.** Nested radius math (§4) requires `inner = outer − padding`. With padding 17.9 and radius 12.4, every derived value is irrational and nothing aligns.

**Published scales:**

| System | Base | Scale |
|---|---|---|
| **Tailwind v4** | 4px, strictly linear | 4, 8, 12, 16, 20, 24… |
| **IBM Carbon** | 2px mini-unit, **non-linear** | 2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96, 160 |
| **Linear** | 4px base, 8-heavy | 4, 8, 12, 16, 24, 32, 48, 96 |
| **Material 3** | 4/8dp | 4, 8, 12, 16, 24… |

**Geometric vs. linear.** Carbon's rationale is explicit: the scale needs "small increments... for detail-level designs as well as larger increments used to control the density" ([Carbon](https://github.com/carbon-design-system/carbon-website/blob/main/src/pages/elements/spacing/overview.mdx)). At the small end you need 2/4/8 resolution because 2px in a badge is visible; at the large end 64 → 80 → 96 → 160, because 4px in section spacing is invisible and just bloats the token set.

**Recommendation: adopt Linear's eight tokens verbatim (4/8/12/16/24/32/48/96).** Round every existing value to the nearest *token*, never to the nearest integer, which would just produce a new arbitrary set.

---

## 2. Density: how tight is premium, and where

**Hard floors.** iOS standard row **44pt**, subtitle row **60pt**, 44pt minimum for custom cells, and a 44x44pt minimum tap target ([Apple HIG](https://developer.apple.com/design/human-interface-guidelines/ios/views/tables/)). Material: **48dp minimum touch target** even when the visible chip is 32dp, the extra 16dp being invisible padding ([Chip.md](https://raw.githubusercontent.com/material-components/material-components-android/master/docs/components/Chip.md)).

**The key move: decouple visual size from tap size.** "The tappable region should be 44x44 at least, but the visible part of it could be smaller" ([Zac Dickerson](https://medium.com/@zacdicko/size-matters-accessibility-and-touch-targets-56e942adc0cc)). In RN that is `hitSlop`. A 28pt chip with `hitSlop={{top:8,bottom:8,left:4,right:4}}` is both premium-tight and accessible. This is how you get Linear-grade density without failing accessibility.

**Linear's actual component padding**, the most useful published reference set:

- Button **8 vertical / 14 horizontal** (1.75:1)
- Form input **8 / 12** (1.5:1)
- Tab pill **6 / 14** (2.33:1), height ≥36, ≥44 on touch
- **Status badge 2 / 8** (4:1)
- Card 24 · Top nav height 56

**Tight vs. cramped, airy vs. empty.** A 2025 *Journal of Sensory Studies* study found "large white spaces and luxurious typefaces enhanced perceived luxury and product quality" ([Wiley](https://onlinelibrary.wiley.com/doi/10.1111/joss.70026)). But the operational rule that reconciles that with Linear-style density is about *ratio*, not absolute value:

- **Between unrelated groups, be generous** (24 to 32). This is the whitespace that reads premium.
- **Within a single object, be tight** (4 to 8). This is what makes an object read as one thing.
- **Cramped** = tight everywhere, so inner padding equals outer gap, grouping collapses, everything is one mass.
- **Empty** = airy everywhere, so there is no ratio between levels and nothing groups either.

**Aim for roughly 2x between adjacent levels:** 4 inside a chip → 8 between chips → 16 inside a row → 32 between sections. Linear's scale is exactly this shape.

Linear's own framing of its redesign confirms the goal is density *with* hierarchy: the changes were made "to reduce visual noise, maintain visual alignment, and increase the hierarchy and density of navigation elements" ([Linear](https://linear.app/now/how-we-redesigned-the-linear-ui)).

---

## 3. Chips, tags and badges: the specific pain point

**Material 3 chip, exact values** ([Chip.md](https://raw.githubusercontent.com/material-components/material-components-android/master/docs/components/Chip.md)):

| Property | Value |
|---|---|
| Min height | **32dp** |
| Min touch target | **48dp** |
| Corner radius | **8dp**, *not* a pill |
| Icon size | 18dp |
| Effective horizontal padding | 12dp each side |
| Stroke | 1dp |
| Spacing between chips | 8dp |

**Polaris Badge** ([Badge.module.css](https://raw.githubusercontent.com/Shopify/polaris/main/polaris-react/src/components/Badge/Badge.module.css)):
- Default padding **2 vertical / 8 horizontal**, a **4:1 ratio**; large is 4/8, **2:1**
- Radius **8px**, but **4px when nested inside a filter** (that is §4 in practice)
- **No `min-height`.** Height derives from line-height plus padding, so the chip can never disagree with its text.

**The padding ratio rule.** Horizontal padding should be about 2x vertical, sometimes 2.5 to 3x. The reason is typographic, not arbitrary: "words are longer than they are tall, so it's preferable to comply with a 'natural' rule of having more horizontal padding than vertical" ([Oscar Otero](https://oscarotero.com/design-tips/posts/014-paddings-for-buttons/)).

Observed in the wild: Linear button 1.75:1, Linear tab pill 2.33:1, Linear status badge 4:1, Polaris badge 4:1, Polaris large badge 2:1.

**Pattern: the smaller the chip, the higher the H:V ratio.** A tall chip at 4:1 looks like a stretched pill; a 20pt chip at 2:1 looks like a square blob.

**Proposed chip table for a 13 to 14pt label:**

| Chip role | Font | V pad | H pad | Height | Ratio | Radius |
|---|---|---|---|---|---|---|
| Inline status badge | 11 to 12 | 2 | 8 | ~20 | 4:1 | 6 |
| Metadata tag | 12 to 13 | 4 | 8 | ~24 | 2:1 | 6 to 8 |
| Filter chip (tappable) | 13 to 14 | 6 | 12 | ~32 | 2:1 | 8 |
| Large / selected | 14 | 8 | 14 | ~36 | 1.75:1 | 8 to 10 |

**Height relative to font size.** Both M3 and Polaris derive height rather than hard-coding it. Heuristic from the numbers: **chip height ≈ 1.7 to 2.3x font size**. Below ~1.6x the text touches the edges; above ~2.6x it floats and reads as a button rather than a tag.

**Corner radius relative to height.** M3 uses 8dp on a 32dp chip, so **radius ≈ height/4**, deliberately not a pill.
- **Pill** (`height/2`) for interactive filter and choice chips and segmented controls. The round form signals "toggle me".
- **Small rect** (`height/4`, 6 to 8) for static status badges and metadata tags inside cards, so the radius stays concentric with the card.
- **Never mix both in one row.** That alone reads as inconsistency.

> **Our app currently mixes both**, and across three different paddings. See [the audit, §4](00-current-state-audit.md).

**Avoiding chip soup.** "Avoid using too many chips as they can clutter the interface and make it hard to scan" ([Mobbin](https://mobbin.com/glossary/chip)); and on badges, "if everything has a badge, none of them feel important anymore" ([Setproduct](https://www.setproduct.com/blog/badge-ui-design)). Practical constraints: **max two chips per list row; one filled or coloured chip per row (the status); everything else is plain text with an icon, not a chip.**

---

## 4. Nested radii: the rule we are breaking everywhere

**The formula:** `innerRadius = outerRadius − gap` ([Cloud Four](https://cloudfour.com/thinks/the-math-behind-nesting-rounded-corners/)).

**Why.** Border-radius is a circle at each corner. For two nested rounded rects to look right their corner circles must be **concentric**, sharing a centre point. That only happens when the radii differ by exactly the gap. When inner and outer share the same radius "their curves don't follow the same arc. The corners of the inner element appear to bulge outward relative to the outer element, creating an uneven visual gap" ([PV21Design](https://pv21design.pt/concentric-radius-nested-corners-done-right/)).

That bulge is the specific thing that reads amateur: the gap is uniform along straight edges and pinches at the corners. Users do not consciously see it. They read the card as "slightly off". This is a large part of the "nobody put effort in" reaction.

**Worked example:** card radius 24, padding 8, inner **16**. Derive it, never hand-set it:

```
inner = outer - padding      // 24 - 8 = 16
```

**Edge case:** when the subtraction reaches zero or below, use a **2 to 4px minimum** rather than square corners, "to take the harshness off the hard corners" ([PV21Design](https://pv21design.pt/concentric-radius-nested-corners-done-right/)).

**Recommendation:** collapse our eleven radii to **four plus a pill**: 4 / 8 / 12 / 16 / pill. Every nested radius is derived from its parent and its padding, not chosen.

---

## 5. Icons

**Standard grids.**
- **Material:** 24dp render size, **20x20dp live area with 2dp padding**, keyline shapes 18x18 square and 20dp-diameter circle, consistent **2dp** stroke, 2dp silhouette corner radius ([Material](https://m1.material.io/style/icons.html)).
- **Lucide:** 24x24 viewBox, 1px minimum safe padding, **2px stroke**, round linecap and linejoin, 2px corner radius above 8px, 2px minimum gap between elements, `fill="none"` + `stroke="currentColor"` ([Lucide](https://lucide.dev/contribute/icon-design-guide)).
- **SF Symbols:** **nine weights** deliberately matched to San Francisco's font weights so a symbol can be weight-matched to adjacent text, and three scales that change size while holding stroke and baseline. Symbols are optically centred to cap height, so baseline alignment is automatic ([WWDC19 206](https://developer.apple.com/videos/play/wwdc2019/206/)).

**Optical vs. mathematical sizing: the single most useful concept here.** "If you keep the circle and the square at the exact same size, the square will always look larger" ([Streamline](https://blog.streamlinehq.com/grids-and-keyshapes/)). Circles, diamonds and triangles must be *larger* than a square to carry equal visual weight, because what you want is **similar area, not similar bounding box** ([Helena Zhang](https://minoraxis.medium.com/icon-grids-keylines-demystified-5a228fe08cfd)). Material's keylines encode this: the square keyline is 18dp while the circle is **20dp**, 11% larger, to look the same size.

**Consequence for us:** setting every icon to `size={20}` means a circular glyph (clock, user, globe) will read smaller than a square one (calendar, inbox). That is the "why do my icons look wrong" layer. Use a set that already applies keylines and do not nudge individual sizes; if you must, nudge circular glyphs up 1 to 2px, never down.

**Stroke weight must match text weight.** SF Symbols' nine weights exist precisely so "you can achieve precise weight matching between symbols and close-by text" ([WWDC19](https://developer.apple.com/videos/play/wwdc2019/206/)). A 2px stroke at 24px is a 1/12 ratio, matching Regular/Medium. Take a 24px 2px-stroke icon down to 16px and the stroke is optically 1.33px relative to its box, so it reads lighter than the label. **Scale strokeWidth with size:** 16px → 1.75, 20px → 2, 24px → 2.

**Filled vs. outline.** Do not mix within one set. "Create a set with one style, and possibly create the other variant" separately; filled offers better recognisability, stroked allows finer detail ([Design Systems](https://www.designsystems.com/iconography-guide/)). The one legitimate pattern is **outline = inactive, filled = active**, which is exactly what a tab bar wants. Also: stroke gaps must never be thinner than the stroke, and do not build stroked icons below **10px**.

**Why mixing families reads cheap.** Each family encodes different terminals (round vs. butt caps), a different stroke-to-box ratio, different corner radii and different keylines. Two families side by side produce two different optical weights at the same nominal size, and the eye reads that as "assembled from whatever was free". **One family, no exceptions.** If a glyph is missing, draw it on that family's grid rather than importing one.

**Icon sets for React Native:**

| Set | Licence | RN package | Notes |
|---|---|---|---|
| **SF Symbols** | Apple licence, **restricted to Apple platforms**. Exporting as SVG/PNG for other platforms violates it ([Apple forum](https://developer.apple.com/forums/thread/739523)) | `expo-symbols`, which renders SF Symbols on iOS and **Material Symbols on Android/web**, which is how it stays compliant ([Expo](https://docs.expo.dev/versions/latest/sdk/symbols/)) | Most native on iOS, requires an Android fallback by design |
| **Lucide** | MIT | `lucide-react-native` | Safest default, identical cross-platform |
| **Phosphor** | MIT | `phosphor-react-native` | **Six weights (thin to fill)**, the closest OSS analogue to SF Symbols' weight-matching |
| **Iconoir** | MIT | official `iconoir-react-native` | 1600+ |
| **Remix Icon** | Remix Icon Licence v1.0, free commercial | via react-native-svg | "Neutral style system symbols" |
| **Hugeicons** | ~5,400 free, 54,000+ needs a paid licence | `@hugeicons/react-native` | Check tier before shipping |
| **Untitled UI Icons** | Proprietary. Usable in apps, but **may not** be redistributed, published online, or used in a competing UI kit ([licence](https://www.untitledui.com/license)) | SVG export | Fine for the app, not fine if the design system is ever open-sourced |

**Recommendation: Phosphor or Lucide as the single family.** Phosphor if we want the weight axis to match icons to text weight (which pairs well with the 400/500/600 type proposal). Lucide for the smallest surface and most conventional look. **Do not use SF Symbols** unless we ship an explicit Android substitute.

---

## 6. Icon containers and roundels

**Glyph-to-container ratio.** The anchor is Material's icon anatomy: a 24dp icon with a 20x20dp live area, so the glyph occupies **~83%** of its own box. Extend one level out to a container tile:

| Container | Glyph | Ratio | Container radius |
|---|---|---|---|
| 28 | 16 | 0.57 | 8 |
| 32 | 18 | 0.56 | 8 to 10 |
| 36 | 20 | 0.56 | 10 |
| 40 | 20 to 22 | 0.50 to 0.55 | 12 |
| 48 | 24 | 0.50 | 14 |

**Rule: glyph ≈ 50 to 58% of container width.** Below ~45% the glyph floats and the tile reads as an empty box; above ~65% it reads as a cropped sticker. This is tighter than icon-in-button padding, because a roundel is a display object, not a hit target.

**Why our low-chroma pastel tiles read cheap.** Three compounding reasons:

1. **Contrast failure.** A pastel tile behind a stroked icon puts a low-saturation fill against a mid-tone glyph. The icon was designed for `currentColor` on a neutral surface; on a 10% tint the effective contrast drops and the glyph goes muddy rather than crisp. Our Slack tile is `#7A5A2E` on `#E4DCCB`, which is exactly this.
2. **Colour as decoration, not information.** Pastel roundels assign a different hue per row for variety. That is decoration, and it triggers badge fatigue: "if everything has a badge, none of them feel important anymore" ([Setproduct](https://www.setproduct.com/blog/badge-ui-design)). Colour that means nothing trains users to stop reading colour. It also directly contradicts our own locked rule that colour is reserved for urgency.
3. **It contradicts the mechanism by which restraint reads premium.** Whitespace reads premium because it "signals that the designer, and by extension the brand, has the confidence to leave things out" ([Made Good](https://madegooddesigns.com/white-space-design/)). Twelve pastel tiles is the visual opposite.

**The premium alternative:** neutral container (`rgba(0,0,0,0.04)` light, `rgba(255,255,255,0.06)` dark), monochrome glyph at text colour, and **one** accent-tinted tile reserved for the genuinely exceptional item.

---

## 7. Elevation: hairlines, not shadows

**The current consensus.** Linear, Vercel, Stripe and Anthropic all moved to hairline borders in their 2025 to 2026 refreshes; Linear's design system is reported as using **three border tokens and zero shadow tokens** ([Pravin Kumar](https://www.pravinkumar.co/blog/webflow-card-shadows-replaced-with-borders-2026)).

**Concrete values:**

| Purpose | Light | Dark |
|---|---|---|
| Default hairline | `rgba(15,15,15,0.08)` | `rgba(255,255,255,0.12)` |
| Emphasis / hover | 0.16 alpha | 0.16 alpha |
| Accent border | accent at 0.4 | accent at 0.4 |

**Why hairlines beat shadows**, three mechanical reasons:
1. **Dark mode.** A shadow is a dark blur; on a dark surface it disappears or renders as a grey smudge. A border renders identically in both modes with one alpha flip.
2. **Retina.** Modern displays render 1px and 0.5px hairlines crisply. `StyleSheet.hairlineWidth` is the one place a fractional value is correct.
3. **Accessibility.** Hairlines pass WCAG non-text contrast without per-mode tuning; shadow-only separation does not.

**When shadows are still right.** Reserve them for genuinely floating layers: modals, popovers, sheets. "Shadow opacity rarely needs to exceed 0.15 for ambient layers and 0.25 for the deepest layer" ([box-shadow guide](https://dev.to/snappy_tools/css-box-shadow-the-complete-guide-to-shadows-layers-and-design-patterns-46i9)). The premium pattern is a 1px semi-transparent border **plus** a very soft low-opacity shadow: "restrained shadows imply elevation without announcing it".

**Why heavy shadows read dated.** They are a Material-2013 signature, a literal paper metaphor that stopped working once dark mode became a first-class requirement, because the metaphor has no answer for what paper looks like on black. A 0.25-alpha 20px-blur shadow under a card in 2026 places the app in 2016.

**Third mechanism, the one Linear leans on hardest: separate by fill.** Elevated surface = base lightened 2 to 4% in dark, darkened 2 to 3% in light. Zero border, zero shadow, cheapest to render.

**Proposed ladder:**
- **Level 0**, list rows: no border, no shadow. Separate by an 8 to 12px gap or a single hairline at `rgba(0,0,0,0.06)`.
- **Level 1**, cards: 1px `rgba(15,15,15,0.08)` plus a surface lightness shift. **No shadow.**
- **Level 2**, sheets and modals: same border plus `0 8px 24px rgba(0,0,0,0.12)`.

---

## 8. Motion

**Material 3 duration tokens:** short1 50, short2 100, short3 150, short4 200, medium1 250, medium2 300, medium3 350, medium4 400, long1 450, long2 500 ([Motion.md](https://raw.githubusercontent.com/material-components/material-components-android/master/docs/theming/Motion.md)).

**Easing:** Standard `0.2, 0, 0, 1` · Emphasized decelerate `0.05, 0.7, 0.1, 1` · Emphasized accelerate `0.3, 0, 0.8, 0.15`.

Emil Kowalski (Linear design engineer, author of Sonner and Vaul) gives: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`, iOS drawer `cubic-bezier(0.32, 0.72, 0, 1)`, and the hard rule **"never use ease-in for UI animations"** because it makes the interface feel sluggish ([SKILL.md](https://github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md)).

**Platform baselines:** mobile 300ms baseline, **225ms enter / 195ms exit**. Rauno Freiberg: "animation duration should not be more than 200ms for interactions to feel immediate" ([interfaces](https://github.com/raunofreiberg/interfaces)).

**Why enter and exit differ.** Entering elements decelerate into place, because the eye must track and settle on new content. Exiting elements accelerate away, because nobody needs to read something leaving. **Using one symmetric duration for both is the most common tell of unconsidered motion.**

**Two more rules worth adopting verbatim:**
- **Animate proportionally, never from zero.** Dialogs fade and scale from ~0.8; buttons press to ~0.96. "Nothing in the real world appears from nothing", so avoid `scale(0)`.
- **Only animate `transform` and `opacity`.** Never width, height, padding or margin.

**The frequency budget.** Emil's matrix: 100+ uses per day means *no animation, ever*; tens per day means drastically reduce; rare or first-time means delight is allowed. Family's designer arrived at the same rule independently: "the potential for delight increases as the frequency of feature usage decreases" ([benji.org](https://benji.org/family-values)). **For a triage app this is decisive:** the feed row and the swipe are used dozens of times a day, so they get near-zero animation. The daily-complete moment is rare, so it can carry the delight.

**Proposed budget:**
- Chip and button press: **100ms**, or none. An instant opacity change often reads crisper.
- Local state change (check, select, expand): **150 to 200ms**, standard easing.
- Screen transitions: **225ms enter** emphasized-decelerate, **195ms exit** emphasized-accelerate.
- Over **400ms** needs a justification. Over 500ms in a productivity app is a bug.
- Honour Reduce Motion by replacing translate and scale with a cross-fade, never by disabling.

---

## Sources

[8pt grid](https://medium.com/design-bootcamp/designing-in-the-8pt-grid-system-f3c1183ea6e8) · [Power of the 8pt grid](https://medium.com/peopleofpapara/the-power-of-the-8pt-grid-system-in-design-1c9dbc683ad8) · [8pt guide](https://www.rejuvenate.digital/news/designing-rhythm-power-8pt-grid-ui-design) · [Tailwind v4 theme.css](https://raw.githubusercontent.com/tailwindlabs/tailwindcss/main/packages/tailwindcss/theme.css) · [Carbon spacing](https://github.com/carbon-design-system/carbon-website/blob/main/src/pages/elements/spacing/overview.mdx) · [Linear redesign](https://linear.app/now/how-we-redesigned-the-linear-ui) · [Material Chip.md](https://raw.githubusercontent.com/material-components/material-components-android/master/docs/components/Chip.md) · [Polaris Badge.module.css](https://raw.githubusercontent.com/Shopify/polaris/main/polaris-react/src/components/Badge/Badge.module.css) · [Oscar Otero, button padding](https://oscarotero.com/design-tips/posts/014-paddings-for-buttons/) · [Apple HIG lists and tables](https://developer.apple.com/design/human-interface-guidelines/ios/views/tables/) · [Zac Dickerson, touch targets](https://medium.com/@zacdicko/size-matters-accessibility-and-touch-targets-56e942adc0cc) · [Cloud Four, nesting rounded corners](https://cloudfour.com/thinks/the-math-behind-nesting-rounded-corners/) · [PV21Design, concentric radius](https://pv21design.pt/concentric-radius-nested-corners-done-right/) · [Material icons](https://m1.material.io/style/icons.html) · [Lucide icon design guide](https://lucide.dev/contribute/icon-design-guide) and [licence](https://lucide.dev/license) · [WWDC19 SF Symbols](https://developer.apple.com/videos/play/wwdc2019/206/) · [SF Symbols licence thread](https://developer.apple.com/forums/thread/739523) · [Expo Symbols](https://docs.expo.dev/versions/latest/sdk/symbols/) · [Phosphor licence](https://github.com/phosphor-icons/core/blob/main/LICENSE) · [Iconoir RN](https://iconoir.com/docs/packages/iconoir-react-native) · [Remix Icon licence](https://github.com/Remix-Design/RemixIcon/blob/master/License) · [Hugeicons RN](https://www.npmjs.com/package/@hugeicons/react-native) · [Untitled UI licence](https://www.untitledui.com/license) · [Streamline, grids and key shapes](https://blog.streamlinehq.com/grids-and-keyshapes/) · [Icon grids demystified](https://minoraxis.medium.com/icon-grids-keylines-demystified-5a228fe08cfd) · [Design Systems iconography guide](https://www.designsystems.com/iconography-guide/) · [Mobbin, chips](https://mobbin.com/glossary/chip) · [Setproduct, badges](https://www.setproduct.com/blog/badge-ui-design) · [Borders over shadows](https://www.pravinkumar.co/blog/webflow-card-shadows-replaced-with-borders-2026) · [Soul, elevation](https://soul.emplifi.io/latest/foundations/foundations/elevation-QmKzPlel) · [box-shadow guide](https://dev.to/snappy_tools/css-box-shadow-the-complete-guide-to-shadows-layers-and-design-patterns-46i9) · [Material Motion.md](https://raw.githubusercontent.com/material-components/material-components-android/master/docs/theming/Motion.md) · [M3 easing and duration](https://m3.material.io/styles/motion/easing-and-duration/tokens-specs) · [Apple HIG motion](https://developer.apple.com/design/human-interface-guidelines/motion) · [Emil Kowalski, design engineering](https://github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md) · [Rauno Freiberg, interfaces](https://github.com/raunofreiberg/interfaces) · [benji.org, Family values](https://benji.org/family-values) · [Iseki et al. 2025, perceived luxury](https://onlinelibrary.wiley.com/doi/10.1111/joss.70026) · [White space in design](https://madegooddesigns.com/white-space-design/)

---

**Source-quality caveats, flagged honestly.** The Linear token values come from a third-party reverse-engineering of linear.app (`awesome-design-md`), not from Linear's own publication: treat them as observed rather than official. `m3.material.io`, `polaris-react.shopify.com` and `atlassian.design` are JS-rendered and could not be fetched directly, so Material and Polaris values were taken from their canonical source repos, which are the implementations those spec pages describe.
