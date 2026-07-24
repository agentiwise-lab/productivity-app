# What "visually rich" actually means: the formula, derived by looking

**Date:** 2026-07-24
**Status:** this supersedes the selection logic in [07b-shortlist-mobile.md](07b-shortlist-mobile.md). The teardowns in 11 to 15 remain valid as *technique* research; the *app selection* behind them was wrong.

---

## The mistake, stated plainly

Round one and round two selected references on **evidence**: Apple Design Awards, MacStories, published design blogs, agency case studies. That produced a defensible list and a wrong one.

**Apple Design Awards reward craft, accessibility, inclusivity and restraint. That is a genuinely different axis from looking expensive.** Optimising for citations produced Things 3, Structured, Timepage, Streaks, stoic., Dark Noise and Family: apps that are light, flat, friendly and utilitarian. Put side by side in [`references/_contact-sheets/round1-award-selected.jpg`](references/_contact-sheets/round1-award-selected.jpg), the problem is obvious in two seconds in a way that no amount of reading revealed.

**The method is now: look first, verify second.** Build a large pool, pull real screenshots, judge on sight, then research only what survives.

**Looking has overturned a text source five times this session:**
- The design press describes Rivian as cel-shaded and cinematic. **The phone app is a plain white list of control rows.** The famous renders are the in-car screen.
- Watch press hypes Bezel as the premium watch app. **It is light, white and minimal.**
- App Store name-search returned OneCard for "Jupiter Money" (byte-identical files), Crypto.com for "Backpack", a guitar tuner for "Tonal", and Lucid Software for "Lucid Motors".

---

## The formula

Derived by examining roughly 110 apps and rating them on sight. **Every app that rated 5/5 does the same five things**, and it is tighter than expected.

### 1. The canvas is near-black, never mid-grey

Slash, Oura, Ultrahuman, WHOOP, Eight Sleep, Halide, Flighty and GOAT all sit at essentially `#000` to `#0A0A0A`. **Mid-grey dark mode instantly reads cheaper** — Tonal and Trust Wallet are the control group.

The black is what makes a single gradient or a single metal render feel like an event rather than decoration.

> Independently confirmed by pixel measurement in [15](15-measured-palettes.md): Halide's ladder is `#080808 → #101010 → #181818`, CRED's is `#0d0d0d → #101010 → #181818`.

### 2. Exactly one material object per screen, rendered in 3D with real light

Slash's gold ingot monogram. UGLYCASH's holographic card. Oura's aurora orb. Flighty's chromed aircraft. Lucid's car. Halide's brushed-metal icon. Ultrahuman's titanium ring. OneCard's metal Visa.

**Not decoration everywhere: one hero object with a specular highlight and a cast shadow, and flat UI around it.**

### 3. A display serif, or a heavily condensed grotesk, doing the emotional work

Slash sets banking copy in an engraved Didone with italics. Atlys uses italic serif over photography. Dorsia and Oura both use serif. Halide, GOAT, END. and Not Boring go the other way with condensed letterspaced caps.

**What none of them use is the default system sans at default weight.** That is precisely why Things 3, Structured and Streaks read as unfinished, and it is the cheapest single fix available to us.

> This also settles the typeface debate from [02 §4](02-typography.md). The counter-argument was "Linear uses Inter, so the face doesn't matter." That holds for a *restrained* target. It does not hold for a *rich* one.

### 4. Colour arrives as a gradient wash tied to meaning, not as a palette

Ultrahuman gives each metric its own gradient field: teal for sleep, green for recovery, amber for movement. Kraken washes indigo. Plata runs orange-to-magenta on a single headline. Othership pairs plum with one chartreuse hairline.

**One or two hues per screen, applied as atmosphere behind the data, never as five equal-weight accent chips.**

### 5. Density is a feature, not a problem

WHOOP, Ultrahuman, Kraken, Copilot, Public, Crypto.com and Plata all put **a lot of numbers on screen at once**, in small sizes, with hairline rules and tiny small-caps labels.

**The expensive feeling comes from confidence that the user can handle information.** Every rejected app shares the opposite instinct: one large friendly number and a lot of whitespace, which reads as a demo rather than an instrument.

> This is the most important finding for us, and it contradicts the round-one conclusion. [06](06-social-sentiment.md) reported "space, at 2 to 3x what feels necessary" as the number-two premium signal. **That was measured on websites and light apps.** For a dark, data-dense instrument, density is what reads premium and airiness reads unfinished. Monarch's deliberate move to *shorter* rows ([08 §12](08-mobile-apps.md)) points the same way.

### The secondary move worth stealing separately

**Photography treated as a material, not as an illustration.** Oura puts a mountain *inside* a score card. Othership puts mist inside a session card. Dorsia puts a restaurant interior behind the member tier. Atlys and Lucid use a photographic environment as the whole canvas with glass panels floating over it.

**None of them use spot illustration. That is the single strongest visual dividing line between the 5/5 set and the 2/5 set.**

---

## The apps that actually rate 5/5

Judged on sight, not on citations. Several of these appear in no design-press roundup anywhere.

| App | What it actually looks like |
|---|---|
| **Slash Banking** | Near-black bleeding into warm amber/gold. Embossed 3D metallic "S" lit like a gold ingot. Engraved Didone serif with italics. **The closest thing to CRED found anywhere** |
| **UGLYCASH** | Black, iridescent chrome wordmark warping across a physical Visa render, brutalist condensed caps, grey concrete texture with "SEND" spray-stencilled. Ugly-luxury, and genuinely rich |
| **CRED** | The reference. Near-black, NeoPOP extruded cards, Cirka serif over Gilroy and Overpass Mono |
| **Oura** | Pure black, aurora-gradient orb as the data object, mountain photography *inside* score cards, small-caps eyebrows |
| **Ultrahuman** | Pure black, per-metric gradient washes behind dense bar columns, hairline mono labels |
| **WHOOP** | Black-to-navy panels, huge thin-stroke gauge rings in electric green and ice blue |
| **Eight Sleep** | Near-black with indigo wash, low-key bedroom photography, thin-stroke gauge |
| **Copilot Money** | Deep navy, glassy translucent category pills floating in 3D, card gradient renders |
| **Halide Mark III** | Brushed-anodised-metal icon, warm graphite gradient, condensed caps, art-directed photography |
| **Flighty** | Near-black with a violet topographic globe, chromed aircraft render tracing luminous great-circle routes |
| **Dorsia** | Aubergine gradient, letterspaced small-caps wordmark, restaurant interiors, script over overhead table shots |
| **Othership** | Plum canvas with **chartreuse hairline borders**, misty desaturated photographic plates with serif titles |
| **Lucid Motors** | Desert-dusk photography as the backdrop, near-black glass panels layered over it, italic serif |
| **Plata Card** | Near-black, orange-to-magenta gradient headline, card thumbnails as gradient chips, big white numerals |
| **Kino / Plexamp / Roon / Endel** | Black plus one luminous element: gold light streak, gold waveform scrubber, editorial portrait, generative rings |

**Rejected on sight despite strong reputations:** Toss (near-white, and light-mode-only by policy), Jupiter, KakaoBank (cartoon mascot), Vipps, Ather, smallcase, stoic., Trust Wallet, Tonal, Athlytic, plus the whole Wise / Wealthfront / Bunq / Klarna / Trade Republic cohort, which ships flat-colour marketing panels rather than rich UI.

---

## The split that needs a decision

The research surfaced **two different kinds of premium**, and CRED is unusual in doing both.

**Type A: dark, dense, luminous.** WHOOP, Ultrahuman, Kraken, Public, Crypto.com, Plata.
Achievable in React Native with **tokens, type and gradients alone.** No asset pipeline. This is weeks of work.

**Type B: material and tactile.** CRED's extruded NeoPOP edges, djay's photoreal turntables with visible groove texture, (Not Boring) Camera's metal dials and swappable skins, Slash's gold ingot.
Needs **3D assets, Lottie, or heavy custom rendering.** This is a real production investment with ongoing asset cost.

**Almost nothing does both.** The decision determines the whole shape of step 3, and it is a resourcing call rather than a research one.

**A middle path exists and is worth naming:** the **one material object per screen** rule (formula point 2) is Type B applied *once*, not everywhere. One well-rendered hero object against a Type A field gets most of the effect for a fraction of the cost. That is what Oura, Flighty and Slash actually do.

---

## The mechanic to steal regardless

**Per-context palette tinting**, which the rich apps keep independently reinventing:

- **Rainbow** ships four palette modes (`light` / `lightTinted` / `dark` / `darkTinted`), where the tinted modes **recolour the entire chrome to the active wallet**, so no two users see the same screen
- **Oura** shifts surfaces with your biometrics
- **Tide Guide** matches the actual colour of the sky
- **Arc Search** tints to the site
- **Ultrahuman** gives each metric its own gradient field

**It buys "bespoke and alive" for the cost of a token layer, with no 3D pipeline.** For a triage feed the obvious application is **tinting to the source you are currently triaging** — GitHub, Slack, Linear, Gmail — which is information *and* atmosphere at once.

---

## What the galleries were actually worth

Recorded so nobody repeats the search.

| Source | Verdict |
|---|---|
| **App Store product pages** | **The best surface by far.** Real shipped apps, publisher-controlled art direction, four screens per shot. Most 5/5s came from here |
| **Mobbin explore** | The only source showing **real in-app screens**. Caps at ~50 apps logged-out and the set is deterministic |
| **60fps.design `/apps`** | **The best candidate *list* on the internet** — 467 real iOS apps, filterable by Apple Design Award. Shots are PRO-gated, so it is a naming source, not a looking source |
| **Screensdesign** | Accessible, but 2,600 apps of overwhelmingly indie subscription utilities. Low yield |
| **Mobbin Awards** | Unusable logged-out. Scroll-driven animation with no extractable text |
| **Godly** | Redirected to recent.design; its app section is concepts, not shipped apps. Dead end |
| **Behance / Dribbble** | **Confirmed worthless for this.** "Fintech app case study" returns Finora, Quantra, FastPay: invented brands on 3D phone bodies. Concept work rendered on floating phone bodies rewards the *render*, not the interface |
| **21st.dev** | Investigated twice. No tab bar, bottom sheet or gesture category at all. A React registry for marketing sites |

**The methodological lesson: judge components at real size, in real apps. Every gallery that shows concept work on 3D phone renders is measuring the mockup, not the design.**
