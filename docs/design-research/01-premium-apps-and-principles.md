# Research: which apps read as premium, and the principles behind it

**Date:** 2026-07-24
**Part of:** step 1 research. This is the catalog and the principle set.

> ### ⚠ Medium caveat: this file is web and desktop contaminated
>
> **The app catalog in Part A is majority web and desktop** (Linear, Raycast, Vercel, Mercury, Monzo's web design system, Superhuman desktop). It is retained because the *principles* in Part B are medium-independent and well sourced, but **the app list should not be used to pick mobile references.**
>
> Use [08-mobile-apps.md](08-mobile-apps.md) for the mobile app catalog and [07b-shortlist-mobile.md](07b-shortlist-mobile.md) for the shortlist.
>
> **What transfers to mobile:** accent discipline, hierarchy by weight not size, fewer borders, concentric radii, optical alignment, tabular numerals, the motion frequency budget, "not every element carries equal visual weight".
> **What does NOT transfer:** any absolute size, spacing or padding number taken from a web system, and anything about hover states. Those are re-derived from mobile sources in [09-mobile-design-principles.md](09-mobile-design-principles.md).

**Evidence grading used throughout.** `[primary]` means the company's own design blog, Apple's own award citation, or the designer's own writing. `[derived]` means a third-party reverse-engineered token dump (925studios, blakecrosley, shadcn.io/design, getdesign.md, `awesome-design-md`). Derived sources publish very specific hex and weight values but are scraped or LLM-generated breakdowns, not published design systems. **Treat every `[derived]` number as plausible but unverified.**

---

## Part A: the app catalog

### Linear (web, desktop) — the best-documented case
Linear publishes its own rationale, which makes it the most useful reference we have.

- `[primary]` **Type:** "We started using **Inter Display** to add more expression to our headings while maintaining their readability and kept using regular **Inter** for the rest of the text elements." ([Linear](https://linear.app/now/how-we-redesigned-the-linear-ui))
- `[primary]` **Colour space:** "We kept using **LCH** for our theme generation, as it is one of the closest color spaces to the human eye and allowed us to deal with different **elevations for our surfaces**." The same post describes a **contrast variable** enabling auto-generated high-contrast themes.
- `[primary]` **Desaturating for timelessness:** achieved by "**limiting how much chrome (blue in our case) was used** in the calculations applied to our color system. The contrast of the content has also been improved by making our text and neutral icons **darker in light mode and lighter in dark mode**."
- `[primary]` **Optical alignment is real labour:** "I also spent time **aligning labels, icons, and buttons, both vertically and horizontally** in the sidebar and tabs."
- `[primary]` **Warmer, not cooler:** a later refresh moved from "a **cool, blue-ish hue**" toward "a **warmer gray that still feels crisp, but less saturated**" ([Linear](https://linear.app/now/behind-the-latest-design-refresh)).
- `[primary]` **Fewer dividers, fewer icons:** "The new borders reduce visual noise with **fewer separators**", and the refresh "**reduces icon usage, scales their sizes down, and removes unnecessary visual treatments** like colored team icon backgrounds."
- `[primary]` **The governing rule:** "**not every element of the interface should carry equal visual weight**... ones that support orientation and navigation should **recede**." The sidebar was made "a few notches dimmer."
- `[primary]` **Craft as a company value:** craft is "the deliberate attention put into making something excellent, **not because someone is checking, but because it matters to the maker**". Operationally: zero-bug policy with 7-day fixes, no half-baked public MVPs, 3 to 5 person teams ([Linear](https://linear.app/now/why-is-quality-so-rare)).
- `[primary]` Karri Saarinen's rules include "**The best design is opinionated**" and "**The simplest way to increase quality is to reduce scope**" ([Figma](https://www.figma.com/blog/karri-saarinens-10-rules-for-crafting-products-that-stand-out/)).
- `[derived, unverified]` Canvas `#08090a`, single violet accent `#5e6ad2`, Inter with OpenType `cv01` and `ss03`, and a signature **font-weight 510**.

> **Most transferable to us:** the "not every element carries equal weight" rule, and the icon reduction. Our Home screen currently gives three equal-weight count tiles and a placeholder tab bar equal prominence to the actual answer.

### Vercel / Geist (web)
- `[primary]` Geist supplies "the colors, typography, materials, layout, and React components", explicitly a "**high contrast, accessible color system**", with **grid** as "a core part of the Vercel aesthetic", plus "presets for **radii, fills, strokes, and shadows**" ([Vercel](https://vercel.com/geist/introduction)). Two proprietary faces: Geist Sans and Geist Mono, both now OFL.
- `[derived]` Negative tracking scaling with size, only 400/500/600 with **no 700 anywhere**, `#fafafa` body on `#171717` ink, status colours used only at ~10px indicator-dot scale and never as fills.

### Raycast (macOS)
- `[primary]` Three stated principles: "**fast, simple, and delightful**" ([Raycast](https://www.raycast.com/blog/a-fresh-look-and-feel)).
- `[primary]` **Scale hierarchy on the one hero element:** "We've made the bar bigger to reflect its importance"; "increased the size of the leading icon of the search results, making it **quicker to scan**."
- `[primary]` **Icon system rebuilt with a specialist:** "He kept the icons **simple with an outline style, and a bolder stroke width**"; "The icons follow the **same rules for stroke width and corner radii**."

### Superhuman (email) — the strongest typography-as-luxury case
- `[primary]` Typeface **Messina** by Luzi Type: "its sans could rival Inter for its extremely functional qualities in product, while the **serif adds some elegant writerly qualities** to the brand" ([Smith & Diction](https://medium.com/smith-diction/branding-superhuman-and-grammarly-and-coda-8c57f970bead)).
- `[primary]` **Custom glyph surgery:** "Our most noticeable customization was **rounding all the punctuation and tittles** to match the rounded qualities of Hero."
- `[primary]` **The differentiation thesis, worth quoting to your manager:** "In an era where **every product looks almost identical**, maybe a beautiful swashy italic would be the thing to make users feel like this was something different."
- `[primary]` They shipped smart quotes **inside the font file** rather than in app logic ([Superhuman](https://blog.superhuman.com/how-to-hack-beautiful-flourishes-into-your-font/)).

### Halide (iOS camera) — Apple Design Award winner
The single best source on accent discipline, because Apple describes it directly.
- `[primary, Apple]` "Color, too, is used carefully and deliberately in Halide, with a **single yellow highlight color** (another homage to classic cameras) used to indicate active state for a feature." ([Apple](https://developer.apple.com/news/?id=x6bv1a36))
- `[primary, Apple]` **The anti-density stance:** "Other camera apps looked like **flight simulators with lots of dials**, which was intimidating, even for someone like me who loves film cameras."
- `[primary, Apple]` **Muscle memory:** "We need to have **consistent gestures**. We need to be flexible **without changing buttons around all the time**."
- `[primary, Apple]` **A documented failure worth learning from:** colour alone proved insufficient to signal active mode. They had to change the **button form**, not just the hue.
- `[primary]` Custom typeface **Halide Router** drawn from **etched type on camera bodies and lenses** ([Halide](https://halide.cam/)).

### Mercury (business banking)
- `[derived, unusually specific]` Two custom faces **Arcadia** and **Arcadia Display** on an intermediate weight axis **360 / 420 / 480 / 530**, deliberately avoiding the bold/light binary, with **heading weight 480** as the signature ("heavier than regular but distinctly lighter than semibold"). Near-black canvas `#171721`, monochrome ivory-on-onyx, a single cobalt `#5266eb` reserved **exclusively for the primary CTA**. Token counts: 18 colour tokens, 14 type levels, **6 corner radii, 9 spacing values**.
- `[secondary]` Positioning: "a **dark cinematic palette, a custom typeface (Arcadia), and art-directed photography** to position itself alongside luxury brands", against a fintech norm of bright palettes and stock photography ([925 Studios](https://www.925studios.co/blog/mercury-design-breakdown)).

> **Note the token counts even if the values are unverified: 6 radii and 9 spacing values.** We have 11 radii and ~19 spacing values.

### Family (Ethereum wallet, iOS) — the best-documented motion case
The designer published his principles ([benji.org](https://benji.org/family-values)).
- `[primary]` Three named principles: **Simplicity, Fluidity, Delight**.
- `[primary]` **Component persistence:** "If a component occupies a space and will persist in the next phase of the user's journey, it should **remain consistent**."
- `[primary]` **Shared-letter animation:** morph text by animating shared glyphs, because "by animating the change, we **reinforce the user's awareness of their action**."
- `[primary]` **The delight-impact curve, the most actionable motion rule found:** "the potential for delight **increases as the frequency of feature usage decreases**." Spend the animation budget on rare moments, not frequent ones.

### Granola (AI meeting notes) — premium via warmth, not dark minimalism
A useful counter-example to the assumption that premium means dark and cold.
- `[press]` Rebrand by Ragged Edge framed as a **rejection of "tech slop"** and clinical AI aesthetics ([Design Week](https://www.designweek.co.uk/ragged-edge-rejects-tech-slop-with-human-centric-granola-rebrand/)).
- `[press]` Type: **Quadrant** (mechanical slab serif) + **Melange** (neutral UI), plus **Granola Script** custom-drawn from a co-founder's actual handwriting, with a deliberately imperfect 'G' ([Creative Boom](https://www.creativeboom.com/inspiration/ragged-edge-rebrands-ai-notepad-granola-with-a-co-founders-handwriting-and-a-deliberately-imperfect-logo/)).
- `[primary]` The brief: "calm and steady to use... approachable and optimistic, a bit rough around the edges, **but sharp enough to feel like a serious tool**" ([Granola](https://www.granola.ai/blog/a-new-look-for-granola)).

### Monzo (banking)
- `[primary]` **Restraint on the brand colour, for semantic reasons:** "**Hot Coral is our soul, but in UI land, red shades usually mean 'something has gone horribly wrong'.** So we used it **very intentionally as a moment of delight**." ([Monzo](https://monzo.com/blog/reimagining-monzo-com-building-a-modular-high-fidelity-web-design-system-that-scales))
- `[primary]` "**Semantic design tokens** for colour, typography, spacing, and motion... supporting future themes without refactoring", with Figma and code at "maximum API parity".
- `[press]` Type: **Oldschool Grotesk** for display plus a custom cut of Universal Sans called **Monzo Sans**.

### Oura (health)
- `[primary]` The 2025 redesign delivered "clearer layouts and **refined typography**, **dynamic color cues** direct attention to what matters most and make it easier to **scan, compare, and act**", and condensed navigation from **5 tabs to 3** ([Oura](https://ouraring.com/blog/new-oura-app-experience/)).
- `[primary, agency]` Instrument names the ingredients: "**progressive disclosure**, a **unified semantic color language**, and a **data-visualization framework that scales**" ([Instrument](https://www.instrument.com/work/oura-app)).

### Things 3 and Bear — both Apple Design Award winners
- Things 3 won in 2009 and 2017 ([Cultured Code](https://culturedcode.com/things/blog/2017/06/back-from-wwdc/)). Credited for "fluid animations, careful typography, natural gestures" and a product strategy of **rigorously applying Apple's own design principles rather than expanding features**.
- Bear won in 2017 ([Bear](https://blog.bear.app/2017/06/thank-you-yes-you-for-our-2017-apple-design-award/)), credited for "simple and clean design, **beautiful typography**, and a consistently fast experience". Typography and performance, not ornament.

### CRED (the reference you gave)
- `[secondary]` Monochrome-plus-neon: "largely monochromatic layout with a **black background and white cards**", neon reserved for campaigns. Type is **Gilroy** + **Overpass Mono**, with serif **Cirka** for headings. The first iteration ("Topaz") was built on "**flat and reductionist minimalism**" ([Morff](https://medium.com/@morffdesign/cred-designing-a-minimalistic-and-intuitive-app-8d157b1861a7)).
- `[secondary]` The positioning line worth remembering: its design "doesn't scream finance; instead, it whispers luxury" ([Arthnova](https://arthnova.com/cred-built-india-exclusive-fintech-paying-users-bills/)).
- Full CRED analysis including the NeoPOP system and a correction about its typeface is in [03-colour-dark-and-light.md §9](03-colour-dark-and-light.md).

### Apple Design Award citations — Apple's own vocabulary for "premium"
The least noisy signal available, because it is Apple stating what earned an award.
- **Flighty** (2023, Interaction): "beautifully designed... an intuitive interface, comprehensive live maps, and **a look that mirrors time-honored airport design conventions**." Borrowing a real domain's visual conventions as a premium signal.
- **Crouton** (2024, Interaction): a "**clean interface**" letting users "keep their focus on the counter rather than the screen."
- **Gentler Streak** (2024 winner, Social Impact): recognised for emphasising "**individual progression rather than comparison against others**". A tone decision reading as design quality.
- **Play** (2025, Innovation): a UI "**both powerful and easy to navigate**." **Taobao** (2025, Interaction): takes into consideration "**placement, position, controls, size, and function**."

**Two corrections to widely repeated claims**, worth knowing before we cite anything:
- **Copilot Money** was a 2024 ADA **finalist**, not a winner ([MacRumors](https://www.macrumors.com/2024/05/28/2024-apple-design-award-finalists/)).
- **Structured** was a **2025 App Store Awards finalist**, not an Apple Design Award recipient ([Apple](https://www.apple.com/newsroom/2025/11/apple-announces-finalists-for-the-2025-app-store-awards/)).
- **Arc Search** was a 2024 ADA finalist; Arc Browser itself did not win a 2023 ADA.

### Candidates with thin evidence, listed honestly
Praised widely, but no specific citable design commentary was found in this pass. **Absence of evidence here is not a judgment on their design.**
- **Notion Calendar (ex-Cron)**, **Amie**, **Bezel**: review-blog level praise only, no primary design source.
- **Sunsama, Reflect, Height, Craft, Rise, Whoop, Strava, Robinhood, Revolut, Cash App, Monarch, Rainbow, Phantom, Cursor, Perplexity, Stripe dashboard**: no credible specific commentary found. Treat as unsourced.

---

## Part B: cross-cutting principles

Ranked roughly by how directly they apply to our problem.

### Colour and surface
1. **Near-black and near-white, never pure black or white.** ([Anthony Hobday, rule 1](https://anthonyhobday.com/sideprojects/saferules/))
2. **Saturate your neutrals, and pick one temperature, warm or cool, not both.** (Hobday, rules 2 and 10.) Corroborated by Linear moving "toward a warmer gray that still feels crisp, but less saturated."
3. **A single saturated accent on a low-chroma field.** Halide: "a **single yellow highlight color**... used to indicate active state." Mercury reportedly reserves one cobalt exclusively for the primary CTA `[derived]`. Vercel keeps status colour at ~10px dot scale only `[derived]`.
4. **Deliberately limit brand-hue contamination of the neutral ramp.** Linear: "limiting how much chrome (blue in our case) was used in the calculations applied to our color system."
5. **Generate themes in a perceptual colour space (LCH/OKLCH), not sRGB**, so surface elevations step evenly to the eye. (Linear.)
6. **Never grey text on a coloured background.** Use the same hue with adjusted S/L, or white at reduced opacity. ([Refactoring UI, tip 2](https://medium.com/refactoring-ui/7-practical-tips-for-cheating-at-design-40c736799886))

### Hierarchy
7. **Not every element carries equal visual weight; navigation must recede.** (Linear.) **This is our Home screen's core problem.**
8. **Create hierarchy with colour and weight, not size.** ([Refactoring UI, tip 1](https://medium.com/refactoring-ui/7-practical-tips-for-cheating-at-design-40c736799886))
9. **Reject the "flight simulator."** Density of visible controls is the dominant cheap-signal. Halide named it; Apple's ADA citations reward the opposite.
10. **Reduce scope to increase quality.** Saarinen: "The simplest way to increase quality is to reduce scope"; "The best design is opinionated."

### Borders, shadows, depth
11. **Use fewer borders.** Replace with a background shift, a shadow, or just more space. ([Refactoring UI, tip 4](https://medium.com/refactoring-ui/7-practical-tips-for-cheating-at-design-40c736799886)) Corroborated by Linear: "the new borders reduce visual noise with fewer separators."
12. **No shadows at all in dark interfaces, and never mix depth techniques.** (Hobday, rules 26 and 27.) Directly relevant given dark is our default.
13. **Offset shadows vertically rather than inflating blur and spread.** (Refactoring UI, tip 3.) Numeric companion: "make drop shadow blur values double their distance values" (Hobday, rule 16).

### Typography
14. **Lower letter-spacing and line-height as type gets larger; raise them as it gets smaller.** (Hobday, rule 6.)
15. **Tabular numerals wherever numbers update or align.** "Where available, tabular figures should be applied... particularly in tables or when layout shifts are undesirable, like in timers." ([Rauno Freiberg](https://github.com/raunofreiberg/interfaces))
16. **Never let font-weight change on hover or select** (layout shift); never use weights below 400. (Rauno Freiberg.)
17. **A custom or customised typeface is the highest-leverage single premium signal.** Superhuman modified Messina's punctuation; Halide and Kino drew faces from etched camera type; Granola commissioned a script from a founder's handwriting; Monzo commissioned Monzo Sans. **The cheap substitute is OpenType stylistic sets on an existing face**, which Linear and Raycast reportedly use `[derived]`.

### Icons
18. **Fewer, smaller, monochrome icons.** Linear's refresh "reduces icon usage, scales their sizes down, and removes unnecessary visual treatments like coloured team icon backgrounds." Raycast standardised "the same rules for stroke width and corner radii" across the whole set.
19. **Lower the contrast of icons paired with text**, and use two typefaces at most. (Hobday, rules 28 and 23.)

### Spacing and shape
20. **Outer padding ≥ inner padding; button horizontal padding = 2x vertical; nest corner radii properly.** (Hobday, rules 19, 22, 24.)
21. **Optical alignment beats mathematical alignment**, and it is real labour: Linear's designer "spent time aligning labels, icons, and buttons, both vertically and horizontally."

### Motion
22. **Duration under ~200 to 300ms; ease-out for enter and exit; never ease-in.** Emil Kowalski: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`, iOS drawer `cubic-bezier(0.32, 0.72, 0, 1)`, and "never use ease-in for UI animations" because it "makes the interface feel sluggish" ([SKILL.md](https://github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md)).
23. **Animate proportionally, never from zero.** "Nothing in the real world appears from nothing", so avoid `scale(0)`.
24. **Only animate `transform` and `opacity`.**
25. **The animation frequency budget.** 100+ uses per day means no animation ever; tens per day means drastically reduce; rare or first-time means delight is allowed. Independently arrived at by Family: "the potential for delight increases as the frequency of feature usage decreases."
26. **Component persistence across transitions.** A component surviving into the next screen keeps its position and identity rather than being destroyed and recreated. (Family.)

### Interaction
27. **Consistent gestures over configurable controls.** (Halide.)
28. **Colour alone is insufficient to encode state; form must also change.** (Halide's documented failure.)
29. **Borrow a real-world domain's visual conventions.** Apple praised Flighty for mirroring "time-honored airport design conventions"; Halide borrowed etched camera type. **For us the analogous domains are the instrument panel, the trading terminal and the flight board**, which is what `design-system.md` was already reaching for.

### Meta
30. **Cheapness is diagnosed as inconsistency, not ugliness.** "Cheap-looking apps don't fail because users can point to what's wrong. They fail because **something feels off**", with inconsistent spacing and cramped controls named as culprits. *Weakest-sourced principle here (SEO agency blogs), so treat as directional* — but it matches our audit findings exactly.
31. **Build in the real material, not in Figma.** Rauno: "If you aspire to be really good at making websites, the materials you need to master are HTML, CSS, and JavaScript, not design or vibe coding tools", because the details "come to life through actual implementation" ([interview](https://spaces.is/loversmagazine/interviews/rauno-freiberg)).

---

## Sources

**Primary, company and designer**
[Linear: how we redesigned the UI](https://linear.app/now/how-we-redesigned-the-linear-ui) · [Linear: behind the latest design refresh](https://linear.app/now/behind-the-latest-design-refresh) · [Linear: why is quality so rare](https://linear.app/now/why-is-quality-so-rare) · [Saarinen's 10 rules](https://www.figma.com/blog/karri-saarinens-10-rules-for-crafting-products-that-stand-out/) · [Raycast: a fresh look and feel](https://www.raycast.com/blog/a-fresh-look-and-feel) · [Vercel Geist](https://vercel.com/geist/introduction) · [Monzo design system](https://monzo.com/blog/reimagining-monzo-com-building-a-modular-high-fidelity-web-design-system-that-scales) · [Ragged Edge x Monzo](https://raggededge.com/partnerships/monzo) · [Oura app redesign](https://ouraring.com/blog/new-oura-app-experience/) · [Instrument: Oura](https://www.instrument.com/work/oura-app) · [Granola: a new look](https://www.granola.ai/blog/a-new-look-for-granola) · [Superhuman: flourishes into your font](https://blog.superhuman.com/how-to-hack-beautiful-flourishes-into-your-font/) · [Smith & Diction: branding Superhuman](https://medium.com/smith-diction/branding-superhuman-and-grammarly-and-coda-8c57f970bead) · [Halide](https://halide.cam/) · [Lux: introducing Kino](https://www.lux.camera/introducing-kino-pro-video-camera/) · [benji.org: Family values](https://benji.org/family-values) · [Bear ADA 2017](https://blog.bear.app/2017/06/thank-you-yes-you-for-our-2017-apple-design-award/) · [Cultured Code ADA](https://culturedcode.com/things/blog/2017/06/back-from-wwdc/)

**Primary, Apple**
[Behind the design: Halide](https://developer.apple.com/news/?id=x6bv1a36) · [ADA 2023](https://developer.apple.com/design/awards/2023/) · [ADA 2024](https://www.apple.com/newsroom/2024/06/apple-announces-winners-of-the-2024-apple-design-awards/) · [ADA 2025](https://www.apple.com/newsroom/2025/06/apple-unveils-winners-and-finalists-of-the-2025-apple-design-awards/) · [App Store Awards 2025 finalists](https://www.apple.com/newsroom/2025/11/apple-announces-finalists-for-the-2025-app-store-awards/) · [MacRumors: 2024 ADA finalists](https://www.macrumors.com/2024/05/28/2024-apple-design-award-finalists/)

**Named-principle references**
[Anthony Hobday: visual design rules](https://anthonyhobday.com/sideprojects/saferules/) · [Rauno Freiberg: Web Interface Guidelines](https://github.com/raunofreiberg/interfaces) · [Emil Kowalski: design engineering](https://github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md) · [Refactoring UI: 7 practical tips](https://medium.com/refactoring-ui/7-practical-tips-for-cheating-at-design-40c736799886) · [Erik Kennedy: 7 rules for gorgeous UI](https://www.learnui.design/blog/7-rules-for-creating-gorgeous-ui-part-1.html) · [Rauno Freiberg interview](https://spaces.is/loversmagazine/interviews/rauno-freiberg) · [Gavin Nelson interview](https://spaces.is/loversmagazine/interviews/gavin-nelson)

**Design press**
[Design Week: Granola rebrand](https://www.designweek.co.uk/ragged-edge-rejects-tech-slop-with-human-centric-granola-rebrand/) · [Creative Boom: Granola](https://www.creativeboom.com/inspiration/ragged-edge-rebrands-ai-notepad-granola-with-a-co-founders-handwriting-and-a-deliberately-imperfect-logo/) · [It's Nice That: Monzo](https://www.itsnicethat.com/news/ragged-edge-monzo-graphic-design-021122) · [MacObserver: ADA 2017](https://www.macobserver.com/news/apple-design-awards-2017-winners-bear-airmail/)

**Derived, reverse-engineered token dumps. Do not cite as fact.**
[awesome-design-md: linear.app](https://github.com/voltagent/awesome-design-md/blob/main/design-md/linear.app/DESIGN.md) · [925studios: Linear breakdown](https://www.925studios.co/blog/linear-design-breakdown-saas-ui-2026) · [925studios: Mercury breakdown](https://www.925studios.co/blog/mercury-design-breakdown) · [shadcn.io/design: Mercury](https://www.shadcn.io/design/mercury) · [shadcn.io/design: Vercel](https://www.shadcn.io/design/vercel) · [blakecrosley: Mercury](https://blakecrosley.com/guides/design/mercury) · [designsystems.one: Geist](https://www.designsystems.one/design-systems/vercel-geist) · [getdesign.md: Raycast](https://getdesign.md/raycast/design-md) · [Refero: Linear](https://styles.refero.design/style/90ce5883-bb24-4466-93f7-801cd617b0d1)

**Weak, directional only**
[efficient.app: Notion Calendar](https://efficient.app/apps/notion-calendar) · [Morff: CRED](https://medium.com/@morffdesign/cred-designing-a-minimalistic-and-intuitive-app-8d157b1861a7) · [Arthnova: CRED](https://arthnova.com/cred-built-india-exclusive-fintech-paying-users-bills/) · [Designing digital luxury](https://medium.com/design-bootcamp/designing-digital-luxury-how-to-design-interfaces-that-feel-expensive-f8c14a220b80)
