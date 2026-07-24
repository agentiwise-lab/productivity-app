# Research: colour for a premium UI, dark and light

**Date:** 2026-07-24
**Part of:** step 1 research. Companion to [00-current-state-audit.md](00-current-state-audit.md).
**Status:** findings only. No palette is chosen here; the recommendation at the end is a starting ramp for step 2, not a decision.

> ### ⚠ Medium caveat: least affected of the contaminated files
>
> Colour theory is largely medium-independent, and the two most important sections here are **more** relevant on mobile than on web: the OLED and near-black analysis (§1) is a phone-hardware argument that barely applies to desktop, and the CRED teardown (§9) is a mobile app.
>
> **Web-derived, and to be treated as reference rather than as values to copy:** the Linear, Vercel/Geist and GitHub Primer palettes. Apple's iOS system colours and Material 3 are mobile-native and stand.
>
> Mobile-specific dark-mode handling (`useColorScheme`, elevation without shadows on a small screen, why mobile dark mode matters more than web) is covered in [09-mobile-design-principles.md §10](09-mobile-design-principles.md).

---

## 1. Dark mode surfaces: near-black, not pure black

**The case against `#000` for app chrome.** Pure black maximises contrast against any foreground, which causes "blooming": bright text appears to glow and edges vibrate, producing fatigue over long reading sessions ([Bootcamp](https://medium.com/design-bootcamp/dark-mode-mastery-why-you-should-almost-never-use-pure-black-000000-c97861d576bc)). The comfortable band is roughly 8 to 12% lightness ([ColorArchive](https://colorarchive.org/guides/dark-mode-palette-guide/)). Google's research landed on `#121212`, a dark grey, as Material's surface baseline rather than black ([Uxcel](https://uxcel.com/blog/mastering-elevation-for-dark-ui-a-comprehensive-guide-342)).

**The OLED counter-argument, measured.** On OLED a black pixel is off and draws no power, so the battery case is real but small. Purdue's study across popular Android apps found **up to 9% reduction at a typical 30 to 50% brightness**, only rising materially at full brightness ([PhoneArena](https://www.phonearena.com/news/dark-mode-oled-display-battery-life-test_id134036)). Decisively: moving from `#000` to a very dark grey around RGB 10,10,10 **gives up only 5 to 10% of that saving** ([Tech in Deep](https://www.techindeep.com/how-to-save-battery-on-oled-screens-74455), corroborated by [XDA](https://www.xda-developers.com/amoled-black-vs-gray-dark-mode/)). Pure black additionally causes **black smear** on OLED while scrolling, as pixels ramp up from fully off. The battery argument does not pay for the visual cost.

**Values actually published by premium systems:**

| System | Dark base | Notes |
|---|---|---|
| **Linear** | `#08090a` ("Linear Black") | Ladder: `#08090a` → `#0f1011` → `#161718` → `#23252a` ([Refero](https://styles.refero.design/style/90ce5883-bb24-4466-93f7-801cd617b0d1)) |
| **GitHub Primer** | `#0d1117` | 14-step neutral scale, finer than the usual 8 to 10 ([Primer](https://primer.style/primitives/colors/)) |
| **Material 3** | `#121212` base, surface ≈ `#141218` | Five `surface-container` levels ([M3](https://m3.material.io/styles/color/roles)) |
| **Apple iOS** | `#000000`, then `#1C1C1E`, `#2C2C2E` | ([Sarunw](https://sarunw.com/posts/dark-color-cheat-sheet/)) |

Apple is the outlier in using true black at the base. That works because iOS leans on grouped, elevated surfaces sitting on top of it. For a full-bleed app canvas like ours, Linear and GitHub are the better models.

**Elevation by lightness, not shadow.** In light mode a shadow reads because a dark shadow on a light surface is high contrast. In dark mode the surface is already near the darkest renderable value, so a shadow has nowhere to go and the contrast is too low to perceive ([Uxcel](https://uxcel.com/blog/mastering-elevation-for-dark-ui-a-comprehensive-guide-342)). The replacement rule: **each layer up adds roughly 4 to 8% lightness** ([ColorArchive](https://colorarchive.org/guides/dark-mode-palette-guide/)). Material 3 formalised this as tone-based surfaces, expressing elevation as tonal overlay rather than shadow ([M3](https://m3.material.io/blog/tone-based-surface-color-m3)).

> **Direct hit on our audit.** `FeedCard.tsx:194` and `Chrome.tsx:158` use `shadowOffset` for card separation. That approach has no dark-mode equivalent, which is part of why dark mode was never viable in the current token layer. Four surface levels are the minimum: canvas, card, nested/hover, overlay.

---

## 2. Hue-tinted neutrals: tint, but barely

Radix states the rule plainly: **"choose the gray scale which is saturated with the hue closest to your accent hue"**, which produces a more harmonious result than pure grey ([Radix](https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette)). Their tinted greys pair to accent families: Mauve to purple/pink, **Slate to blue/cyan**, Sage to green, Olive to lime, **Sand to yellow/orange/brown**.

Temperature is set by hue at low saturation: roughly **200 to 240° reads cool, 40 to 60° reads warm** ([ColorArchive](https://colorarchive.org/guides/neutral-color-palettes/)). Cool blue-greys read as precise and systematic, the register of developer tools and financial software. Warm greys read approachable and human.

> **Direct hit on our audit.** Our current palette is `Sand` territory (`#F4F1EC` cream, taupe tiles) while `docs/design-system.md` specifies a cool blue bias "on purpose". These are opposite decisions, and for a GitHub/Linear/Slack triage tool the cool direction is the better-evidenced fit.

**The important counterpoint.** Radix warns that saturated greys, *especially in dark mode*, can clash with colourful components, and that pure grey works with any palette. Linear made exactly this call in its 2024 refresh: they raised contrast by **limiting how much chroma entered the calculation**, explicitly to reach a "neutral and timeless appearance" ([Linear](https://linear.app/now/how-we-redesigned-the-linear-ui)). Practical read: tint, but stay under about `0.015` chroma in OKLCH. Above that it stops reading as a premium grey and starts reading as "a blue theme".

---

## 3. Accent discipline: one accent, under 10% of the screen

The stated rule of thumb is **60-30-10**: 60% dominant neutral, 30% secondary, 10% accent ([LogRocket](https://blog.logrocket.com/ux-design/60-30-10-rule/), [Hype4](https://hype4.academy/articles/design/60-30-10-rule-in-ui)). Applied to premium UI: most of a good interface is simply white or dark grey with contrasting type, plus **a single vibrant accent**.

The mechanism is **contrast through scarcity**: "when your blue only appears on primary buttons and active states, users immediately recognize it as 'this is where I act'", and "restraint creates recognition: when Stripe purple appears, you notice it precisely because it's not everywhere" ([sixtythirtyten](https://www.sixtythirtyten.co/blog/60-30-10-rule-complete-guide)). Luxury branding literature converges from the other direction: premium palettes rarely exceed four or five active colours ([Zoviz](https://zoviz.com/blog/luxury-brand-colors-meanings)).

**Target for our app:** accent under 10% of pixel area on any screen. One accent hue for primary CTA, active nav, focus ring, selection, and the single most important number. Everything else neutral. Status colours (red/amber/green) are **not** accents and should be desaturated relative to the accent so they do not compete.

> This is already half-right in our locked spec, which reserves `signal` for urgency only and refuses to colour-code action types. That instinct is well supported and should survive the redesign.

---

## 4. Which hues read premium, and which read cheap

**Reads premium.** Black is the colour most associated with luxury worldwide, anchoring Chanel, Saint Laurent, Prada, Balenciaga and Tom Ford at around `#0A0A0A`. Deep green signals permanence rather than trend-chasing (Harrods for over a century, Rolex's most recognisable family). Gold or amber works only as a thin accent, never a flood: the separator between luxury gold and gaudy gold is restraint. Three combinations that consistently read premium: black + gold + ivory; navy + platinum + cream; forest green + gold + black ([Zoviz](https://zoviz.com/blog/luxury-brand-colors-meanings), [MyDreamEngine](https://www.mydreamengine.com/the-luxury-color-code-blend-hues-to-boost-your-brand-power/)).

**Reads cheap, and specifically reads AI-generated.** The named fingerprint is **Inter + an indigo-to-purple gradient + three rounded cards in a row + a centred hero** ([925 Studios](https://www.925studios.co/blog/ai-slop-design-tells), [SmoothUI](https://smoothui.dev/blog/ai-design-slop)).

The causal story is worth knowing because it explains why this is so pervasive: **Tailwind shipped `bg-indigo-500` as its component-library demo default**, that propagated through thousands of copied tutorials, and LLMs trained on the result learned "modern web design = purple buttons" ([prg.sh](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website)). There is a compounding loop: a striking purple-gradient site gets attention, enters the next training round, and the model treats it as more normal still, so "a pattern that looked original in early 2025 was a cliche by mid-2026" ([GradientDeck](https://gradientdeck.com/blog/anti-slop-design-with-gradientdeck)).

**Glassmorphism** is a qualified avoid. Overused it becomes noise, and semi-transparent blurred backgrounds create genuine contrast failures for visually impaired users ([IxDF](https://ixdf.org/literature/topics/glassmorphism), [Neel Networks](https://www.neelnetworks.com/blog/glassmorphism-web-design-guide-2026/)). It survives as a precise selective tool, not a global surface treatment.

> **This independently validates the "explicitly banned" list in `docs/design-system.md`.** Lavender/violet accents, purple-to-blue gradients, glassmorphism and glowing borders were banned there on instinct; the sourcing above is the argument for keeping that ban.

---

## 5. Perceptual colour space: author in OKLCH

**Why HSL ramps look uneven.** HSL forces every hue into an identical 0 to 100% saturation range even though perception and displays have different maximum saturations per hue ([Evil Martians](https://evilmartians.com/chronicles/oklch-in-css-why-quit-rgb-hsl)). Two concrete failures they name: adding 10% lightness produces different perceived results for blue vs. purple (why Sass's `darken()` was unpredictable), and changing hue silently changes lightness, so deriving an error-red from a brand accent can drop text below readable contrast.

**Why OKLCH fixes it.** Oklab was built by Björn Ottosson to hold perceptual uniformity across lightness, chroma and hue at once, and to blend without the purple hue-shift CIELAB introduces ([Ottosson](https://bottosson.github.io/posts/oklab/)). `L` is perceptually consistent across all hues, so changing hue preserves contrast:

```css
.button           { background: oklch(0.7  0.1 250); }  /* blue */
.button:hover     { background: oklch(0.75 0.1 250); }  /* same C, lighter */
.button.is-delete { background: oklch(0.7  0.1 20);  }  /* red, identical L and C */
```

**Adoption.** Linear rebuilt theme generation on LCH rather than HSL precisely because "a red and a yellow color with lightness 50 will appear roughly equally light to the human eye", and this reduced theming from **98 variables to three: base colour, accent colour, contrast** ([Linear](https://linear.app/now/how-we-redesigned-the-linear-ui)). Tailwind v4 converted its whole default palette to `oklch` for wider-gamut P3 vividness ([Tailwind](https://tailwindcss.com/blog/tailwindcss-v4)).

**Recommendation:** author every token in OKLCH. Build ramps by holding hue constant and stepping `L` evenly, tapering `C` at both ends since near-black and near-white cannot hold chroma. Linear's three-variable model is the most elegant target to aim at.

---

## 6. Semantic scale: the Radix 12-step contract

The most directly implementable artefact found. Role mapping from [Radix](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale):

| Step | Role |
|---|---|
| 1 | App background |
| 2 | Subtle background (cards, sidebars) |
| 3 | UI element background, default |
| 4 | Hovered UI element background |
| 5 | Active / selected UI element background |
| 6 | Subtle borders and separators, non-interactive |
| 7 | UI element border and focus ring |
| 8 | Hovered UI element border |
| 9 | Solid background, highest chroma step, primary buttons |
| 10 | Hovered solid background |
| 11 | Low-contrast text, **guaranteed Lc 60 APCA** |
| 12 | High-contrast text, **guaranteed Lc 90 APCA** |

Steps 11 and 12 carry contrast guarantees baked into the scale definition, which is why the system holds in both modes without per-token auditing.

**Geist (Vercel) is the same idea at 10 steps** ([Geist](https://vercel.com/geist/colors)): 100/200/300 component background default/hover/active, 400/500/600 border default/hover/active, 700/800 high-contrast background, 900 secondary text, 1000 primary text, plus `background-100`/`200` for page surfaces.

**Recommendation:** adopt the Radix step roles as our token *names* even if we generate the values ourselves in OKLCH. Components then reference step numbers and never raw values. This is the single change that would have prevented the 11-radii, 19-spacing-value freehand problem from recurring in colour.

---

## 7. Dark and light parity without a washed-out inversion

**Structural rule:** components reference **semantic tokens only** and never know which mode is active ([DEV](https://dev.to/hasansarwer/how-to-structure-design-tokens-for-light-and-dark-mode-11b2)). Primer implements three layers, base → functional → component, each referencing the one below, which is what lets one component set serve light, dark, dimmed, high-contrast and colour-vision-deficiency themes with no per-component work ([GitHub](https://github.blog/2023-05-11-unlocking-inclusive-design-how-primers-color-system-is-making-github-com-more-inclusive/)).

**Why straight inversion fails:** "Dark is not a variant of light. It is a first-class design system context with its own visual logic, its own elevation language, and its own token architecture" ([Muzli](https://muz.li/blog/dark-mode-design-systems-a-complete-guide-to-patterns-tokens-and-hierarchy/)).

What premium systems actually do differently between modes:

- **The elevation channel flips.** Dark: lightness steps carry hierarchy, shadows are useless. Light: borders and shadows carry it, because a white card on white has no headroom to go lighter. In practice light mode leans on step 6, dark mode leans on the step 2 to 3 surface lift.
- **The surface ramp direction reverses.** In dark, elevated means lighter. In light, elevated is usually white on an off-white canvas, so the canvas is step 2 and cards are step 1.
- **Accent lightness is re-tuned, not inverted.** An accent readable as solid-on-dark at `L 0.62` needs roughly `L 0.55` in light to hold text contrast. Radix gives each scale independent light and dark values that preserve step *role*, not step *value*.
- **Chroma is reduced in dark mode.** Apple's guidance is to desaturate in dark; saturated hues vibrate against near-black.

**Recommendation:** one token name set, two value sets. Add an explicit `--border-subtle` token that is prominent in light and near-invisible in dark, and an `--elevation-lift` token that is a lightness delta in dark and a shadow in light. That pair absorbs most of the divergence.

---

## 8. Contrast: design to APCA, ship WCAG as the floor

**WCAG 2.x is unreliable for dark mode.** It overstates contrast for dark colours to the point that a nominal 4.5:1 can be functionally unreadable when one colour is near black ([APCA](https://git.apcacontrast.com/documentation/WhyAPCA.html)). APCA is perceptual: **Lc 60 means the same perceived readability regardless of how light or dark the pair is**, and it models polarity separately because light-on-dark and dark-on-light do not read equivalently at the same ratio ([APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html)).

| Text role | APCA target |
|---|---|
| Body / column text | **Lc 90** |
| Practical floor where readability matters | **Lc 75** |
| Secondary, non-body content | **Lc 60** |
| Tertiary, captions, disabled | Lc 45 to 60, non-essential only |

A dark-mode-specific consequence: reaching a comfortable Lc 75 in dark may need a **thinner** weight than in light, because bright text on dark bloats optically and the same weight reads heavier ([66colorful](https://66colorful.com/blog/apca-contrast/)).

**The single most important practical note:** the "muddy secondary text" failure comes from picking secondary as a fixed opacity such as `rgba(255,255,255,0.6)` instead of a measured Lc target. **Opacity-derived text is the most common cause of dark UIs that look cheap.** Use solid token values at a measured Lc, not alpha.

---

## 9. CRED, the reference you gave

**One correction to the brief.** CRED did **not** commission a custom typeface. Their headline face is **Cirka**, a retail serif by **Nick Losacco**, sold by Pangram Pangram ([Pangram Pangram](https://pangrampangram.com/products/cirka), [Fonts In Use](https://fontsinuse.com/typefaces/99680/cirka)). Cirka draws on an "Italian Wedge" language, the geometry of vintage supercars, pairing classic vertical-axis construction with pointed, flamboyant serifs. CRED pairs it with **Gilroy** (geometric sans, Radomir Tinkov) for body and **Overpass Mono** for numerals. There is an unrelated retail font literally named "Cred Typeface" by Tugcu Design Co.: do not confuse them.

**The design language is NeoPOP**, CRED's fourth-generation system, launched April 2022 and **open-sourced**. Named for the Neo-Pop art movement of the 1980s and 90s; the stated idea is taking everyday objects and elevating them to art ([Analytics India Mag](https://analyticsindiamag.com/ai-news-updates/cred-open-sources-its-ui-design-system-neopop/), [Homegrown](https://homegrown.co.in/homegrown-voices/cred-s-new-design-philosophy-channels-the-unbridled-creative-spirit-of-the-neo-pop-art-movemen)).

**Palette:** dark throughout. Base is whites and greys, with a small set of saturated highlights (green, yellow, pink) reserved for icons and specific elements ([UX Planet](https://uxplanet.org/thoughts-on-creds-ui-revamp-apr-2022-6d2b4dcfcfc6)). Textbook accent discipline: desaturated near-black field, high-chroma colour only at points of action.

**The one thing to be careful about copying.** NeoPOP's signature is a hard-edged, offset "pop" shadow, a solid coloured block behind a button rather than a soft blur, giving a tactile physical-object feel. It is deliberately not the soft-shadow or glass idiom, and it is a legitimate premium move because it reads as chosen rather than default. But it is loud, and it is CRED's signature rather than a neutral pattern. Worth understanding what makes it work (the accent discipline and the dark field), and worth being deliberate before adopting the pop shadow itself.

**Implementation references:** open-source components at [CRED-CLUB/neopop-web](https://github.com/CRED-CLUB/neopop-web), live tokens at [playground.cred.club](https://playground.cred.club/?path=/docs/foundation-colors--page). Exact hex tokens could not be retrieved by fetch because the playground is a JS-rendered Storybook; pull them from the repo's token files in step 2.

---

## 10. A starting ramp for step 2

Not a decision. A defensible starting point synthesising the above: OKLCH, Radix step roles, cool-tinted neutral, one accent.

```css
/* neutral: hue 250, chroma tapering at both extremes */
--n1:  oklch(0.16 0.006 250);  /* app background        */
--n2:  oklch(0.20 0.006 250);  /* subtle bg / card      */
--n3:  oklch(0.24 0.007 250);  /* UI element bg         */
--n4:  oklch(0.28 0.008 250);  /* hovered               */
--n5:  oklch(0.32 0.008 250);  /* active / selected     */
--n6:  oklch(0.37 0.009 250);  /* subtle border         */
--n7:  oklch(0.43 0.010 250);  /* UI border, focus ring */
--n8:  oklch(0.52 0.011 250);  /* hovered border        */
--n9:  oklch(0.62 0.010 250);  /* solid                 */
--n10: oklch(0.68 0.009 250);  /* solid hover           */
--n11: oklch(0.77 0.007 250);  /* secondary text, ~Lc 60 */
--n12: oklch(0.96 0.004 250);  /* primary text,   ~Lc 90 */

--accent-9:  oklch(0.62 0.17 250);   /* electric blue, or 155 for deep green */
--accent-10: oklch(0.67 0.17 250);
--accent-11: oklch(0.78 0.13 250);   /* accent text on dark */
```

Light mode keeps the same eleven names, reverses the `L` ramp, and swaps the elevation channel from lightness-lift to border plus shadow. Every text pairing must be verified against an APCA calculator ([apcacontrast.com](https://apcacontrast.com/)) rather than trusted from the numbers above.

**The open question for you in step 2:** deep green vs. electric blue as the single accent. Both are well evidenced. Green reads calm and permanent and matches the "quiet instrument" positioning in the product brief; blue reads precise and technical and matches the developer wedge. This is a brand call, not a research call.

---

## Sources

- [Radix Colors, Understanding the scale](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale) / [Composing a palette](https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette)
- [Linear, How we redesigned the Linear UI](https://linear.app/now/how-we-redesigned-the-linear-ui) / [Linear tokens on Refero](https://styles.refero.design/style/90ce5883-bb24-4466-93f7-801cd617b0d1)
- [Vercel Geist Colors](https://vercel.com/geist/colors)
- [GitHub Primer colour system](https://github.blog/2023-05-11-unlocking-inclusive-design-how-primers-color-system-is-making-github-com-more-inclusive/) / [Primer Primitives](https://primer.style/primitives/colors/)
- [Material 3 colour roles](https://m3.material.io/styles/color/roles) / [Tone-based surface colour](https://m3.material.io/blog/tone-based-surface-color-m3)
- [Sarunw, iOS dark colour cheat sheet](https://sarunw.com/posts/dark-color-cheat-sheet/)
- [Björn Ottosson, Oklab](https://bottosson.github.io/posts/oklab/)
- [Evil Martians, OKLCH in CSS](https://evilmartians.com/chronicles/oklch-in-css-why-quit-rgb-hsl) / [OK, OKLCH picker](https://evilmartians.com/chronicles/oklch-a-color-picker-made-to-help-think-perceptively)
- [Tailwind CSS v4](https://tailwindcss.com/blog/tailwindcss-v4)
- [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html) / [Why APCA](https://git.apcacontrast.com/documentation/WhyAPCA.html) / [Calculator](https://apcacontrast.com/) / [66colorful, APCA vs WCAG 2](https://66colorful.com/blog/apca-contrast/)
- [Uxcel, elevation for dark UI](https://uxcel.com/blog/mastering-elevation-for-dark-ui-a-comprehensive-guide-342)
- [ColorArchive, dark mode palettes](https://colorarchive.org/guides/dark-mode-palette-guide/) / [neutral palettes](https://colorarchive.org/guides/neutral-color-palettes/)
- [Bootcamp, why not pure black](https://medium.com/design-bootcamp/dark-mode-mastery-why-you-should-almost-never-use-pure-black-000000-c97861d576bc)
- [Muzli, dark mode design systems](https://muz.li/blog/dark-mode-design-systems-a-complete-guide-to-patterns-tokens-and-hierarchy/)
- [DEV, structuring tokens for light and dark](https://dev.to/hasansarwer/how-to-structure-design-tokens-for-light-and-dark-mode-11b2)
- [PhoneArena, OLED dark mode battery test](https://www.phonearena.com/news/dark-mode-oled-display-battery-life-test_id134036) / [XDA](https://www.xda-developers.com/amoled-black-vs-gray-dark-mode/) / [Tech in Deep](https://www.techindeep.com/how-to-save-battery-on-oled-screens-74455)
- [LogRocket, 60-30-10](https://blog.logrocket.com/ux-design/60-30-10-rule/) / [Hype4](https://hype4.academy/articles/design/60-30-10-rule-in-ui) / [sixtythirtyten](https://www.sixtythirtyten.co/blog/60-30-10-rule-complete-guide)
- [Zoviz, luxury colour palettes](https://zoviz.com/blog/luxury-brand-colors-meanings) / [MyDreamEngine](https://www.mydreamengine.com/the-luxury-color-code-blend-hues-to-boost-your-brand-power/)
- [prg.sh, why AI keeps building the purple gradient site](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website) / [925 Studios, AI slop tells](https://www.925studios.co/blog/ai-slop-design-tells) / [SmoothUI](https://smoothui.dev/blog/ai-design-slop) / [GradientDeck](https://gradientdeck.com/blog/anti-slop-design-with-gradientdeck)
- [IxDF, glassmorphism](https://ixdf.org/literature/topics/glassmorphism) / [Neel Networks](https://www.neelnetworks.com/blog/glassmorphism-web-design-guide-2026/)
- [Pangram Pangram, Cirka](https://pangrampangram.com/products/cirka) / [Fonts In Use, Cirka](https://fontsinuse.com/typefaces/99680/cirka) / [MyFonts, Gilroy](https://www.myfonts.com/collections/gilroy-font-radomir-tinkov/)
- [Analytics India Mag, CRED open-sources NeoPOP](https://analyticsindiamag.com/ai-news-updates/cred-open-sources-its-ui-design-system-neopop/) / [Homegrown](https://homegrown.co.in/homegrown-voices/cred-s-new-design-philosophy-channels-the-unbridled-creative-spirit-of-the-neo-pop-art-movemen) / [UX Planet, CRED UI revamp](https://uxplanet.org/thoughts-on-creds-ui-revamp-apr-2022-6d2b4dcfcfc6) / [CRED-CLUB/neopop-web](https://github.com/CRED-CLUB/neopop-web) / [NeoPOP playground](https://playground.cred.club/?path=/docs/foundation-colors--page) / [Unofficial Figma kit](https://www.figma.com/community/file/1118043778634755120/creds-neopop-ui-kit-unofficial)
