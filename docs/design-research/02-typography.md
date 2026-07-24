# Research: typography, and what makes text feel premium

**Date:** 2026-07-24
**Part of:** step 1 research. Companion to [00-current-state-audit.md](00-current-state-audit.md).

> ### ⚠ Medium caveat: mixed web and mobile sources
>
> The Apple Dynamic Type scale, the SF tracking table and the iOS line-height figures here are **genuinely mobile** and stand. The Radix, Vercel/Geist, Tailwind and Atlassian scales are **web systems**, and their top-end sizes (48, 60, 64px) are meaningless on a 390pt phone.
>
> The proposed six-step scale below was drawn with mobile in mind and tops out at 34, which matches Apple's largest standard style. It is **re-validated against mobile-only sources** in [09-mobile-design-principles.md §1](09-mobile-design-principles.md), which also covers the accessibility sizes and the mobile legibility floor. Where the two disagree, the mobile file wins.

---

## 1. Type scale: few steps, widely separated

Nathan Curtis (EightShapes, the most-cited writer on design-system typography) says most systems need "three or so" body sizes and to "start with a few and expand as necessary" ([EightShapes](https://medium.com/eightshapes-llc/typography-in-design-systems-6ed771432f1e)).

The cheap-looking failure mode is a scale with 15/16/17/18 all in use: the eye cannot resolve a 1px difference as intent, so it reads as inconsistency rather than structure.

> **This is exactly our problem.** Our current scale has ten steps between 10.3 and 20.7pt with gaps as small as 0.6pt. See [the audit, §3](00-current-state-audit.md).

Published scales, real numbers:

| System | Scale (px) |
|---|---|
| Apple iOS Dynamic Type (Large) | 11, 12, 13, 15, 16, 17, 20, 22, 28, 34 ([learnui.design](https://www.learnui.design/blog/ios-font-size-guidelines.html)) |
| Material 3 | 11, 12, 14, 16, 22, 24, 28, 32, 36, 45, 57 ([Android M3](https://developer.android.com/develop/ui/compose/designsystems/material3)) |
| Radix Themes | 12, 14, 16, 18, 20, 24, 28, 35, 60 ([Radix](https://www.radix-ui.com/themes/docs/theme/typography)) |
| Vercel / Geist | 12, 14, 16, 18, 24, 32, 48, 64 |
| Atlassian | body 12/14/16, heading 12, 14, 16, 20, 24, 28, 32 ([Atlassian](https://atlassian.design/foundations/typography/)) |

**The single most premium structural choice on that list:** iOS does *not* scale titles up much. Titles morph to 17pt, the same size as body, and differentiate by **weight and placement** instead ([learnui.design](https://www.learnui.design/blog/ios-font-size-guidelines.html)).

Common ratios are Major Third 1.250, Augmented Fourth 1.414, Perfect Fifth 1.5, Golden 1.618 ([IBM Design](https://medium.com/design-ibm/a-deep-dive-on-typescales-16c7b1473d83)). For dense product UI the argument is a low ratio near the base with a jump at the top ([Imperavi](https://imperavi.com/books/ui-typography/principles/modular-scale/)). Note that pure modular scales produce fractional px, which is why every shipped system above **rounds to whole numbers rather than obeying the ratio**.

**Proposed scale, six steps:**

```
11  micro / overline / badge   (uppercase, tracked +)
13  tertiary / meta / timestamp
15  secondary / list subtitle
17  body + list title          <- base
22  section header
34  screen title
```

Gaps of 2 / 2 / 2 / 5 / 12. **Nothing between 17 and 22.** If something needs to be "slightly bigger", change weight or colour instead of adding 18 or 19.

---

## 2. Weight: three weights, big jumps, 400 as the default

Apple's rule: prefer Regular, Medium, Semibold, Bold; avoid Ultralight, Thin and Light, which are hard to see at small sizes. And: "use font weight, size, and color to highlight the most important information", three axes, so size need not carry everything ([Apple HIG](https://developers.apple.com/design/human-interface-guidelines/foundations/typography/)).

Vercel ships exactly three weights and bans a fourth: **400 body, 500 UI, 600 headings, with no weight 700 anywhere in the system**. Curtis: "some systems can get away with as few as two or three weights", and "adding fonts and weights is easy; managing download size and changing them is hard" ([EightShapes](https://medium.com/eightshapes-llc/typography-in-design-systems-6ed771432f1e)).

**Why "everything semibold" reads cheap:** hierarchy is relative. If 80% of the screen is 600, the 600 marks nothing, and the remaining regular text reads as de-emphasised rather than as the default.

> **Our app has only `'600'` and implicit regular, and 600 is applied to card titles, group labels, headers, buttons and stat values.** That is the failure above, exactly.

**Proposed:**
- **400 Regular** for all body, list subtitles and metadata. This should be the majority of pixels.
- **500 Medium** for list titles, tab labels, button labels. The "you can act on this" weight.
- **600 Semibold** for section headers and the screen title only.
- Skip 700. Jump 400 to 600 for real emphasis; 400 to 500 is not legible as emphasis, which is why 500 must be earned by *role*, not by importance.
- Never bold a whole row. Bold one element per group.

Rauno Freiberg adds two hard rules: **never let font-weight change on hover or select** (it causes layout shift), and never use weights below 400 ([Web Interface Guidelines](https://github.com/raunofreiberg/interfaces)).

---

## 3. Optical tracking: the highest-leverage detail we are missing entirely

The rule: tracking is a function of optical size. Negative at display sizes, around zero at body, **positive below ~13px and for all uppercase**. On iOS the system font does this automatically at every point size ([Apple](https://developers.apple.com/design/human-interface-guidelines/macos/visual-design/typography/)), which is precisely why hand-set text with `letterSpacing: 0` looks subtly wrong next to native UI.

**Apple's published SF tracking:**

| Size | Tracking (px) | ≈ em |
|---|---|---|
| 34pt | −1.05 | −0.031 |
| 28pt | −0.80 | −0.029 |
| 22pt | −0.70 | −0.032 |
| 17pt | −0.43 | −0.025 |
| 15pt | −0.24 | −0.016 |
| 13pt | −0.08 | −0.006 |
| 12pt | +0.12 | +0.010 |
| 11pt | +0.15 | +0.014 |

([HIG table reproduction](https://gist.github.com/eonist/b9c180a67980c6e18a5184f19bff68fa), cross-checked against [learnui.design](https://www.learnui.design/blog/ios-font-size-guidelines.html))

**Radix** publishes a much gentler curve in em: 12px +0.0025, 14 to 16px 0, 18px −0.0025, 24px −0.00625, 35px −0.01, 60px −0.025 ([Radix](https://www.radix-ui.com/themes/docs/theme/typography)). **Vercel/Geist** is the aggressive end: 48px −4.75%, 32px −4%, normal at 14px and below. That compressed headline look is a deliberate brand signature, not a general rule.

**Inter publishes an actual formula** ([Inter Dynamic Metrics](https://d.rsms.me/inter-website/v3/dynmetrics/)):

```
tracking = -0.0223 + 0.185 * e^(-0.1745 * fontSize)   // em
```

**Proposed for React Native** (RN `letterSpacing` is in px, so these are absolute):

| Size | letterSpacing |
|---|---|
| 34 | −0.9 |
| 22 | −0.5 |
| 17 | −0.35 |
| 15 | −0.2 |
| 13 | −0.05 |
| 11 | +0.15 |
| **11 uppercase label** | **+0.6 to +0.9** |

Uppercase always needs positive tracking; caps were never spaced for setting words. This one change is the difference between an overline label reading as designed and reading as a leftover `<Text>`.

> Our current theme sets `letterSpacing` semi-randomly (−0.1, 0.4, 0.5, 0.6, 1.1) with **no relationship to size**, and applies +0.4 to uppercase 11pt tags where +0.7 is wanted.

---

## 4. Typeface

**Why licensed or bespoke faces read premium.** Two reinforcing reasons. Ownership: Söhne (Klim, Kris Sowersby) is used by Stripe, OpenAI, Rivian and Medium and reads as "contemporary sophistication" partly because you cannot get it free ([Typewolf](https://www.typewolf.com/sohne)). And economics: a four-style custom typeface from a known designer runs **$100,000 to $250,000+**, off-the-shelf custom work $5,000 to $50,000 ([Design Week](https://www.designweek.co.uk/issues/24-30-may-2021/how-commissioning-a-custom-font-could-save-you-money/)).

**Why Inter/Roboto/Poppins/Montserrat read template-y.** "If you open Dribbble, Twitter, or Figma Community in 2026, 90% of the designs use the exact same typeface: Inter... designers are currently forcing Inter onto every single UI, even when the brand needs a distinct personality" ([Bootcamp](https://medium.com/design-bootcamp/inter-how-designers-are-slowly-stripping-away-your-brands-soul-with-a-font-fcf58ee1deaf)). Also: "since it's so popular, it's also dramatically overused. In headings it soon looks very generic or dull" ([Pimp my Type](https://pimpmytype.com/font/inter/)).

**Important corrective, and it should temper how much we spend here.** Linear, the usual premium benchmark, **uses Inter** ([type.fan](https://www.type.fan/site/linear-app), and Linear's own post confirms Inter Display for headings plus Inter for everything else). So the typeface is not what makes Linear look expensive. The scale, weight discipline, tracking and colour ramp are. Do not over-index on this axis.

**Free, high quality, usable in React Native:**

| Face | Licence | Notes |
|---|---|---|
| **Geist Sans / Geist Mono** | **SIL OFL**, free commercial, embeddable ([licence](https://github.com/vercel/geist-font/blob/main/LICENSE.txt)) | Vercel + Basement Studio. Best "looks paid, is free" option. `@fontsource/geist` gives raw .ttf for RN. |
| **Switzer** | Fontshare, free personal + commercial, no signup | Neo-grotesque in the Helvetica/Univers/Akkurat lineage, 18 styles. Closest free thing to a Söhne feel. |
| **General Sans** | Fontshare, free commercial | Swiss-inspired, geometric but warm. |
| **Satoshi** | Fontshare, free commercial | Very widely used now, so less differentiating. |
| **Inter / Inter Display** | SIL OFL | Safe, superb at 11 to 15px. Use Inter Display for the 22 and 34 steps. |
| **IBM Plex Sans** | SIL OFL | Distinctive without being trendy. |

For RN: `expo-font` asset linking, self-host static .ttf per weight, and **load exactly three weights**. The download-size argument applies double on mobile.

**Recommendation to decide in step 2:** Switzer or General Sans for the app face, or Geist Sans + Geist Mono for the zero-risk single-foundry option.

---

## 5. Monospace: keep it, but narrow it drastically

Mono reads **precise and premium** when applied to a narrow semantic slice: numbers, IDs, timestamps, codes, shortcuts, diffs. Polaris states this as policy: "monospace for code, tabular numerals for numbers/currency" ([Polaris](https://polaris-react.shopify.com/design/typography)).

It reads **terminal-ish and cheap** when it becomes the vibe rather than the signal. A designer who built a mono-only design system concluded the typography was "too restrictive" and had to break it: the aesthetic was right, the blanket application was not ([DEV](https://dev.to/micronink/i-built-a-terminal-design-system-then-had-to-break-it-2kl0)). The tell is mono body copy, mono nav labels, mono buttons.

> **This is a direct hit on our locked spec**, which states "The mono pairing is the signature. All repo refs, counts, timestamps, channel names, section labels and chips are mono." Section labels, channel names and chips are the over-reach. Numbers, timestamps and refs are the legitimate slice.

**Faces:** Berkeley Mono ($75) is called "the most-coveted paid monospace of 2026"; Geist Mono is "slightly more designer-conscious than JetBrains Mono"; JetBrains Mono is the best free all-rounder ([roundup](https://madegooddesigns.com/best-monospace-fonts-2026/)). **Menlo, Courier and Consolas are OS defaults, not choices. Using them signals that nothing was decided.**

**Proposed:** ship **Geist Mono** and use it for exactly four things: counts/metrics, durations, timestamps, short IDs and refs. Size mono **1pt smaller** than adjacent sans, since mono x-heights run large.

---

## 6. Numerals

Proportional figures match the typeface's natural spacing and are correct in running text; **tabular figures give every digit identical width so columns align** ([Fontology](https://www.myfonts.com/pages/fontscom-learning-fontology-level-3-numbers-proportional-vs-tabular-figures/)).

The premium tell in a data-dense mobile UI is **numbers that do not jitter when they change**. A live counter or currency column in proportional figures shifts horizontally on every tick, which reads as amateur. Rauno Freiberg states it as a rule: "Where available, tabular figures should be applied with `font-variant-numeric: tabular-nums`, particularly in tables or when layout shifts are undesirable, like in timers" ([Web Interface Guidelines](https://github.com/raunofreiberg/interfaces)).

Caveat before committing to a face: per the 2024 Web Almanac only ~16% of web fonts ship tabular variants ([Kombai](https://kombai.com/tailwind/font-variant-numeric/)). Verify `tnum` exists.

**Lining vs. old-style:** old-style figures are a book and editorial move. In a productivity app they read decorative. **Use lining everywhere.**

**Proposed:**
- Lining + proportional for numbers inside sentences ("3 tasks due").
- Lining + **tabular** for every right-aligned numeric column, every animating or updating number, all durations, all counts in a repeated list row.
- RN: `fontVariant: ['tabular-nums']`, or use Geist Mono which is tabular by construction.

---

## 7. Line-height and measure

WCAG 1.4.12 requires content to survive line-height at 1.5x ([Understanding SC 1.4.12](https://www.digitala11y.com/understanding-sc-1-4-12-text-spacing/)). That is a "must not break", not a "must ship at".

What shipped systems use:
- **Apple:** 17 → 22 (1.29), 15 → 19 (1.27), 13 → 16 (1.23), 34 → 41 (1.21)
- **Material 3:** 16/24 (1.5), 14/20 (1.43), 22/28 (1.27), 57/64 (1.12)
- **Radix:** 16/24 (1.5), 24/30 (1.25), 35/40 (1.14), 60/60 (1.0)
- **Atlassian:** 16/24, 14/20, 12/16, all on a 4px grid

**The universal pattern: the line-height ratio decreases as size increases.** Body 1.4 to 1.5, headings 1.2 to 1.25, display 1.0 to 1.15. A 34pt title at 1.5 looks loose and cheap; a 13pt caption at 1.15 looks cramped and cheap.

**Proposed, all on a 4px grid, which matters more than the exact ratio:**

| Size | Line height | Ratio |
|---|---|---|
| 34 | 40 | 1.18 |
| 22 | 28 | 1.27 |
| 17 (list title) | 22 | 1.29 |
| 17 (paragraph) | 24 | 1.41 |
| 15 | 20 | 1.33 |
| 13 | 18 | 1.38 |
| 11 | 16 | 1.45 |

**Note the two 17s.** Tighter leading for single-line list titles, looser for multi-line prose. This is the highest-leverage line-height decision in a list-heavy app: tight leading inside a row makes the row read as one object.

**Measure:** the 45 to 75 character rule applies to prose, not list rows. On a 390pt iPhone with 16pt gutters, 17pt body already gives roughly 45 to 50 characters, at the low end. **Do not add horizontal padding to "breathe"**, it drops us below readable measure. Breathe vertically.

---

## 8. Text colour hierarchy

**Apple uses an alpha ramp** on a tinted near-black/near-white ([Noah Gilmore's extracted values](https://noahgilmore.com/blog/dark-mode-uicolor-compatibility)):

| Role | Light | Dark |
|---|---|---|
| label | `rgba(0,0,0,1.0)` | `rgba(255,255,255,1.0)` |
| secondaryLabel | `rgba(60,60,67,0.60)` | `rgba(235,235,245,0.60)` |
| tertiaryLabel | `rgba(60,60,67,0.30)` | `rgba(235,235,245,0.30)` |
| quaternaryLabel | `rgba(60,60,67,0.18)` | `rgba(235,235,245,0.18)` |

Two premium details hidden there: the secondary colour is **not pure grey**, it is `60,60,67`, blue-tinted. And the ramp is **1.0 / 0.6 / 0.3 / 0.18**, big non-linear drops, the same well-separated-steps logic as the size scale.

**Vercel uses discrete solid tokens instead:** primary `#171717`, secondary `#4D4D4D`, muted `#8F8F8F`.

**The accessibility tradeoff is real and one-directional.** Alpha text "can trick automated accessibility tools into thinking that your site has better contrast than it actually does" ([Vispero](https://vispero.com/resources/an-argument-against-css-opacity/)). Check the numbers: Apple's tertiaryLabel at 0.30 alpha on white is roughly 2.2:1, so **it fails 4.5:1 outright**. Apple gets away with it because tertiary is used for placeholders and disabled states, not information. Copy the ramp for real content and you ship inaccessible text.

**Proposed, alpha ramp for authoring, resolved to solid tokens per theme:**

```
Light                          Dark
primary    #0A0A0B  (~19:1)    #FAFAFA
secondary  #5A5A63  (~6.8:1)   #A0A0AB
tertiary   #8A8A94  (~3.4:1)   #6E6E78
disabled   #C2C2C9  (fails, non-informational only)
```

- Only **three informational tiers**. A fourth means a layout problem, not a colour problem.
- Keep the blue tint (B channel above R and G). **Pure `#888` grey is the single most common cheap-UI tell after wrong tracking.**
- Resolve alpha to flat hex per theme so contrast checkers see the truth.
- **Timestamps and counts are secondary, not tertiary.** Never put information the user must read in tertiary.
- Prefer dropping **colour** rather than **size** for de-emphasis. A 13px secondary caption looks more considered, and is more accessible, than an 11px primary one.

---

## Implementable summary

```
FAMILY   Switzer or Geist Sans, weights 400/500/600, + Geist Mono 400/500

SIZE  WEIGHT  LH   TRACKING  ROLE
34    600     40   -0.9      screen title
22    600     28   -0.5      section header
17    500     22   -0.35     list item title
17    400     24   -0.35     paragraph
15    400     20   -0.2      list subtitle
13    400     18   -0.05     metadata
11    500     16   +0.15     caption
11    500     16   +0.75     UPPERCASE overline

NUMERALS  lining; tabular-nums on all columns, counters, durations
COLOUR    light  #0A0A0B / #5A5A63 / #8A8A94
          dark   #FAFAFA / #A0A0AB / #6E6E78
```

**Three rules do most of the work:** no size between 17 and 22; negative tracking above 15 and positive below 13; 400 is the default and 600 appears at most twice per screen.

---

## Sources

EightShapes [typography in design systems](https://medium.com/eightshapes-llc/typography-in-design-systems-6ed771432f1e) · Apple HIG [typography](https://developers.apple.com/design/human-interface-guidelines/foundations/typography/) and [macOS visual design](https://developers.apple.com/design/human-interface-guidelines/macos/visual-design/typography/) · [learnui.design iOS font sizes](https://www.learnui.design/blog/ios-font-size-guidelines.html) · [HIG size/tracking table](https://gist.github.com/eonist/b9c180a67980c6e18a5184f19bff68fa) · [Material 3 Compose](https://developer.android.com/develop/ui/compose/designsystems/material3) · [Radix typography](https://www.radix-ui.com/themes/docs/theme/typography) · [Atlassian typography](https://atlassian.design/foundations/typography/) and [colour](https://atlassian.design/foundations/color) · [Tailwind font-size](https://tailwindcss.com/docs/font-size) · [Polaris typography](https://polaris-react.shopify.com/design/typography) · [Inter Dynamic Metrics](https://d.rsms.me/inter-website/v3/dynmetrics/) · [IBM, a deep dive on typescales](https://medium.com/design-ibm/a-deep-dive-on-typescales-16c7b1473d83) · [Imperavi, modular scale](https://imperavi.com/books/ui-typography/principles/modular-scale/) · [Fontfabric on weight](https://www.fontfabric.com/blog/typography-knowledge-weight-typography/) · [Typewolf, Söhne](https://www.typewolf.com/sohne) · [Bootcamp, Inter critique](https://medium.com/design-bootcamp/inter-how-designers-are-slowly-stripping-away-your-brands-soul-with-a-font-fcf58ee1deaf) · [Pimp my Type, Inter](https://pimpmytype.com/font/inter/) · [type.fan, Linear](https://www.type.fan/site/linear-app) · [Design Week, custom font cost](https://www.designweek.co.uk/issues/24-30-may-2021/how-commissioning-a-custom-font-could-save-you-money/) · [Geist licence](https://github.com/vercel/geist-font/blob/main/LICENSE.txt) · [Fontshare](https://madegooddesigns.com/fontshare/) and [Switzer](https://madegooddesigns.com/switzer-font/) · [best monospace fonts 2026](https://madegooddesigns.com/best-monospace-fonts-2026/) · [terminal design system retrospective](https://dev.to/micronink/i-built-a-terminal-design-system-then-had-to-break-it-2kl0) · [Fontology, proportional vs tabular](https://www.myfonts.com/pages/fontscom-learning-fontology-level-3-numbers-proportional-vs-tabular-figures/) · [Kombai, font-variant-numeric](https://kombai.com/tailwind/font-variant-numeric/) · [Matthew Ström, design better data tables](https://medium.com/mission-log/design-better-data-tables-430a30a00d8c) · [WCAG SC 1.4.12](https://www.digitala11y.com/understanding-sc-1-4-12-text-spacing/) · [Noah Gilmore, dark mode UIColor](https://noahgilmore.com/blog/dark-mode-uicolor-compatibility) · [Vispero, against CSS opacity](https://vispero.com/resources/an-argument-against-css-opacity/) · [WebAIM contrast](https://webaim.org/articles/contrast/) · [Rauno Freiberg, Web Interface Guidelines](https://github.com/raunofreiberg/interfaces)
