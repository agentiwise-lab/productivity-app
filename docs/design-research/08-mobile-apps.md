# Mobile app catalog: phone apps only

**Date:** 2026-07-24
**Part of:** step 1 research, mobile-only pass. Replaces the contaminated catalog in [01-premium-apps-and-principles.md](01-premium-apps-and-principles.md).

**Inclusion rule:** every app here is a phone app, analysed on its phone UI. Any app whose design reputation rests on a web or desktop canvas is excluded, and the exclusions are listed with reasons at the end. Awards are stated precisely, because winner-vs-finalist is misreported constantly.

**Two sections:** finance, health and lifestyle first (below), then productivity and tools.

---

# Part 1: finance, health and lifestyle

## 1. CRED (iOS + Android, India)

**Awards:** none found. Its reputation rests on open-sourcing its own design system, not on a platform award.

**Why it is the most useful reference in this list:** NeoPOP ships as first-party libraries for **all four platforms**, including [neopop-android](https://github.com/CRED-CLUB/neopop-android) and [neopop-ios](https://github.com/CRED-CLUB/neopop-ios). The web README even states its components are "optimized for mobile views." So unlike almost every other design system we could study, **this one is mobile-native and the source is readable.**

**Mobile-specific techniques:**
- **Depth via painted surfaces, not shadows.** Buttons render as **five surfaces** (top, left, right, bottom, centre). The Android `PopFrameLayout` computes the bottom and right surface colours from the centre colour for "elevated", and the top and left from the **parent and grandparent view colours** for "flat". This costs no blur, renders identically on both platforms, and works in dark mode where shadows fail.
- **Adjacent-button awareness.** `neopop_button_on_right` / `neopop_button_on_bottom` flags let tiled buttons share edges rather than double them up.
- **Zero border radius, system-wide.** An independent teardown notes "no curves anywhere, right angles only" ([UX Planet](https://uxplanet.org/thoughts-on-creds-ui-revamp-apr-2022-6d2b4dcfcfc6)).
- **A serif display face against a sans body**, which is unusual in fintech and a large part of why it does not read like every other finance app.

### CRED / NeoPOP actual token values

Extracted verbatim from `raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/*`. **These are real published values, not a reverse-engineered guess.**

**Base colours** ([colors.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/colors.ts))
```
black #0d0d0d   white #ffffff   red #EE4D37
yellow #F08D32  blue #144CC7    green #06C270
```

**Neutral ramps. Note that black is never `#000`:**
```
popBlack   100 #8A8A8A · 200 #3D3D3D · 300 #161616 · 400 #121212 · 500 #0d0d0d
popWhite   100 #D2D2D2 · 200 #E0E0E0 · 300 #EFEFEF · 400 #FBFBFB · 500 #ffffff
```

**Accent ramps.** Every accent is an 8-step 100 to 800 scale with 500 as the brand step:
```
poliPurple     100 #E8DFFF … 500 #6A35FF … 800 #20104D
orangeSunshine 100 #FFEFE6 … 500 #FF8744 … 800 #4D2914
parkGreen      100 #DDFFF1 … 500 #3BFFAD … 800 #124D34
pinkPong       100 #FFE1E9 … 500 #FF426F … 800 #4D1421
mannna         100 #FFF8E5 … 500 #FFCB45 … 800 #4D3D15
neoPaccha      100 #FBFFE6 … 500 #E5FE40 … 800 #454C13
yoyo           100 #F4E5FF … 500 #AA3FFF … 800 #33134D
```

**Semantic colours, only 5 steps:**
```
error   100 #FCE2DD … 500 #EE4D37
warning 100 #FBDDC2 … 500 #F08D32
info    100 #C2D0F2 … 500 #144CC7
success 100 #E6F9F1 … 500 #06C270
```

**Text opacity tokens** ([opacity.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/opacity.ts)) — **the single most portable trick in the whole system:**
```
HEADING 0.9 · SUB_HEADING 0.7 · BODY_TEXT 0.5 · BODY_TEXT_LIGHTER 0.3
```
One ink colour, four opacities. It survives theme switching for free and is trivial in React Native.

> **Note the tension with our own typography research.** [02 §8](02-typography.md) argues against alpha-derived text because it fools contrast checkers and can ship inaccessible text. CRED does exactly this and it looks superb. The resolution: **author with alpha, then resolve to solid hex per theme and measure the result.** Get the ergonomics of the ramp and the honesty of measured contrast.

**Type scale** ([typography.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/typography.ts))
Sizes: `44, 36, 34, 32, 28, 24, 22, 20, 18, 16, 15, 14, 13, 12, 11, 10, 8`
Weights: Regular, Medium, SemiBold, Bold, ExtraBold
Four families: Heading, Body, Caps, **Serif Heading** (Cirka)
Naming convention `t<type><size><weight>`, e.g. `th44eb`, `tb16m`, `tc10b`.
**No line-height or letter-spacing values exist in the file.**

**Button tokens** ([buttons.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/buttons.ts))
```
Big:    height 50px, padding 0 30px, icon 20px
Medium: height 40px, padding 0 20px, icon 16px
Small:  height 30px, padding 0 25px, icon 14px
```
The variant key encodes seven axes: base / dark-light / primary-secondary / size / kind (elevated or flat) / arrow. **Elevated buttons set the top and left edges to `transparent`.** No radii appear anywhere in the file, consistent with the no-curves rule.

**For our React Native build:** there is **no official React Native NeoPOP package**. The Android, iOS, Flutter and Web libraries exist. Reimplementing the five-surface button in RN is straightforward: four absolutely-positioned parallelogram `View`s around a centre `View`, with bottom and right derived from the centre colour for elevated, top and left from the parent background for flat. Interactive tokens at [playground.cred.club](https://playground.cred.club).

---

## 2. Copilot Money (iPhone + Mac, iOS-first)

**Awards:** **Apple Design Award FINALIST, 2024, Innovation.** Not a winner (winners were Procreate Dreams and Lost in Play). Confirmed at [developer.apple.com/design/awards/2024](https://developer.apple.com/design/awards/2024/). Also App Store Editor's Choice.

**Evidence:** Apple's own [How Copilot Money developed an interest in Swift Charts](https://developer.apple.com/articles/copilot-money/).

**Mobile-specific techniques:**
- **UIKit core components "heavily tweaked" to get a unique look**, not stock. This is the important one: the premium feel comes from customising native components, not from rebuilding them.
- Founder Andrés Ugarte: "having a native app makes a difference the moment you start interacting with it."
- **All data stored locally**, with no cloud round-trip, specifically to keep interaction responsive. Perceived speed as a design decision.
- Their first SwiftUI surface used **stock Swift Charts** rather than a custom chart engine. **An ADA finalist with a heavily customised shell still chose the platform's chart primitive.** The differentiation was in the surrounding craft.

---

## 3. Family (iOS only, Ethereum wallet)

**Awards:** **none.** It does not appear in the 2024, 2025 or 2026 ADA lists. Its reputation is peer and design-community, not award. (Correcting my own earlier framing.)

**Evidence:** the designer's published manifesto, [Family Values by Benji Taylor](https://benji.org/family-values). **The richest mobile-motion source found anywhere in this research.**

**Mobile-specific techniques:**
- **Dynamic tray system.** Expandable contextual bottom overlays that **overlay rather than displace**, so the user never loses context. **Tray height difference is used semantically** to signal progression through a flow. This is a genuinely mobile idea with no web equivalent.
- **Text morphing.** "Continue" to "Confirm" animates the shared letters. Number separators slide to new positions as you type an amount.
- **Direction-matched transitions.** Swipe left, content animates left. Navigation is movement through space, never teleportation. Chevrons rotate to reinforce.
- **Context-adaptive theming.** A tray inside a dark flow adopts a darker scheme.
- **The delight budget**, and this is the most transferable principle in the entire mobile pass: **high-frequency features get subtle touches, low-frequency features get high-intensity delight.** Confetti on backup completion, sound on wallet-trash. Explicitly to avoid diminishing returns.

> **Direct application to us:** the feed row and the swipe are touched dozens of times a day, so they get near-zero animation. The daily-cleared moment happens once, so it can carry everything.

---

## 4. WHOOP (iOS + Android)

**Awards:** none found.

**Evidence:** [925 Studios teardown](https://www.925studios.co/blog/whoop-design-breakdown), [WHOOP's own home-screen post](https://www.whoop.com/us/en/thelocker/the-all-new-whoop-home-screen/).

**Mobile-specific techniques:**
- **Hero Recovery score at roughly 72pt equivalent**, explicitly sized to be readable **at arm's length**, not at reading distance. This is the only hard hero-numeral size found with a stated rationale.
- **Near-total black justified functionally, not stylistically:** high-contrast data points, low eye strain at 5am and 11pm, and it makes coloured coaching elements read as **content rather than decoration**.
- **A strict three-colour semantic palette** (green at 67%+ recovery, yellow, red below 33%). No arbitrary accents. Every hue carries meaning.
- **Three-tier progressive disclosure:** overview tile with a single score, then trends with colour-banded zones, then raw biometrics.
- Information design by **Martin Oberhaeuser** (previously BMW, Airbnb, Facebook).

**Caveat:** no hex values or typeface disclosed. And see [05 §6](05-gamification-that-stays-premium.md) for the user evidence that WHOOP's red band actively changes how people feel about their day, which is the argument against copying the RAG palette.

---

## 5. Gentler Streak (iPhone, iPad, Apple Watch)

**Awards:** **Apple Design Award WINNER, 2024, Social Impact.** Confirmed at [developer.apple.com/design/awards/2024](https://developer.apple.com/design/awards/2024/).

**Evidence:** Apple's [Behind the Design](https://developer.apple.com/news/?id=3m0ht22s), and a [designer interview at Sketch](https://www.sketch.com/blog/gentler-streak/).

**Mobile-specific techniques:**
- **Built largely in UIKit for stability.** Worth noting: an ADA winner that is not on SwiftUI.
- **Data-viz is deliberately plain** (a line graph, simple monthly bars) with the craft spent on the **interpretation copy around the number** rather than on the chart itself.
- An abstract mascot ("Yorhart") as the humanising device **instead of an accent colour**.
- On Apple Watch, a **readiness bar**: a green stripe with an orange heart showing live headroom, the whole watch UI collapsed to one glanceable object.
- Monthly Summary compares you to **your own history**, never to other users.
- Ships iOS 18 tinted icons and widgets.

---

## 6. Nubank (iOS + Android, Brazil)

**Awards:** none found. **But this is the best-documented dark-mode-at-scale case in the entire research.**

**Evidence:** [The birth of the Dark Mode](https://building.nubank.com/the-birth-of-the-dark-mode-a-journey-into-nubanks-app-evolution/), [Designing a multi-product experience](https://building.nubank.com/designing-a-multi-product-experience/).

**Mobile-specific techniques, and this is effectively our dark-mode checklist:**
- **Pure black background**, chosen to match native iOS and Android and to save OLED power. (Note this contradicts the near-black consensus in [03 §1](03-colour-dark-and-light.md); both positions are defensible and the difference is whether you rely on elevated surfaces sitting on top.)
- **Neutral greys only**, no warm or cool tint, to keep a blank canvas.
- **Three anti-patterns they fixed, all from naive inversion:**
  1. Inverting made the brand purple too light and unreadable, so they **darkened it and reduced saturation while keeping white text on it**.
  2. They **lightened text off pure white** to avoid exaggerated contrast.
  3. They **desaturated accents** so nothing "shines too much in the dark context."
- Shipped across **3,000+ screens via a token fallback strategy** rather than migrating every screen first. Directly relevant to how we would roll dark mode into an existing app.

---

## 7. Oura (iOS + Android)

**Awards:** none found.

**Evidence:** [Introducing the New Oura App Design](https://ouraring.com/blog/new-oura-app-experience/).

**Mobile-specific techniques:**
- **Collapsed five tabs into three.** Home, Readiness, Sleep, Activity and Resilience became Today, Vitals and My Health. A real, citable tab-bar simplification.
- The Today tab is built around **"one big thing"**: a single surfaced score or insight rather than a grid.
- Moved from discrete metric boxes to an integrated flow over **serene natural-landscape backgrounds**, a notably different premium register from WHOOP's black.

**Counter-evidence, already logged in [05 §6](05-gamification-that-stays-premium.md):** DC Rainmaker found the redesign "dilutes the information too much."

---

## 8. Robinhood (iOS + Android)

**Awards:** won an Apple Design Award in 2015, which predates the current category structure.

**Evidence:** [Robinhood newsroom](https://newsroom.aboutrobinhood.com/a-visual-identity-that-better-reflects-our-vision/), [COLLINS case study](https://the-brandidentity.com/project/collins-robinhood-combine-make-investing-accessible-affordable-engaging).

**Mobile-specific technique, and it is the clearest type case in this list:** a **custom typeface "Capsule Sans"** commissioned from Milieu Grotesque, based on an archived cut of Maison Neue, with letterforms **specifically refined to hold up at small mobile sizes**. Paired with "Nib", a whimsical serif, for personality. This is the clearest documented case of a fintech commissioning type **for the phone rather than the billboard**.

---

## 9. Cash App (iOS + Android) — an instructive negative result

**Awards:** none found.

**The finding is a negative one and it matters for us.** Cash App commissioned a full custom typeface (**Cash Sans**, 2025) and a comprehensive brand system, **but the fonts appear only in marketing. The app itself renders in SF Pro on iOS and Roboto on Android.** Block chose system fonts for readability and native feel ([brand standards](https://standards.site/examples/cash-app/), [font analysis](https://www.designyourway.net/blog/what-font-does-cash-app-use/)).

The brand carries via colour, motion and layout, not letterforms. **Directly relevant to whether we ship a custom face in React Native at all.**

---

## 10. Monzo (iOS + Android) — phone app posts only

**Awards:** none verified for the app.

**Evidence:** [How we built the new Home screen](https://monzo.com/blog/how-we-built-the-new-home-screen), [Introducing Trends](https://monzo.com/us/blog/monzo-us-blog/trends). **Monzo's design-system fame is web; only the phone-app posts are cited here.**

**Mobile-specific techniques:**
- **Server-driven UI** for the Home screen, so layout and ordering can change without a release while still allowing "delightful interactions like spotlights."
- A user-controllable Home screen composition.
- A dedicated fifth **Trends** tab aggregating external connected accounts.
- They put a **"snooze"** on the redesign rollout because forcing it mid-task created friction.
- Their thesis: "simplicity isn't the absence of things, it's bringing order to complexity."

---

## 11. Strava (iOS + Android + watchOS)

**Awards:** **App Store Award WINNER 2025, Apple Watch App of the Year.** Confirmed at [developer.apple.com/app-store/app-store-awards-2025](https://developer.apple.com/app-store/app-store-awards-2025/).

**Mobile-specific techniques:**
- **A two-typeface split: Inter for the UI, Boathouse (custom, Grilli Type) for brand.** Inter was adopted specifically for pace, distance, elevation and small text because it proved **more stable and legible at those sizes**.
- Icon library rebuilt from scratch: **360 concepts across 4 optical sizes = 1,440 final assets** ([Griff Designs](https://griffdesigns.com/strava)). A concrete measure of what a real multi-size mobile icon system costs.

> **The rule this implies, and it is repeated by Cash App and inverted by Robinhood: the hero number gets the neutral, stable face. The brand face never touches the number.**

---

## 12. Monarch Money (iOS + Android + web) — the density counterweight

**Evidence:** [brand refresh post](https://www.monarch.com/blog/monarch-brand-refresh).

**The refresh went denser, not airier.** They **reduced transaction row heights and tightened whitespace "to pack in more information"**, and redesigned mobile dashboard cards for density. Also rebuilt dark mode properly, retiring their old "Navy Mode" for true dark aligned with the OS, and shipped **user-selectable alternate app icons**.

**Useful correction to the assumption that premium equals more whitespace.** For a triage feed, this is the more relevant precedent.

---

## 13. Headspace and Calm

**Headspace** ([Behind the Design](https://developer.apple.com/news/?id=fkfnhq8u)) made **the same tab-collapse move as Oura**: it killed the category tabs (Meditation, Focus, Movement, Sleep) in favour of a **Today tab keyed to time of day** plus an Explore tab holding the library. Warm illustration framed explicitly as "demystification". Stated goal: "simplicity at the surface, incredible depth of content underneath."

**Calm** was **App Store App of the Year 2017** ([Slate](https://slate.com/technology/2017/12/apple-app-store-calm-app-of-the-year-is-a-fitting-choice-for-2017.html)), and is the ancestor of Oura's full-screen landscape direction.

---

## 14. Streaks, Athlytic, The Outsiders, Harvee, Opal

- **Streaks** — **Apple Design Award WINNER, 2016** ([Macworld](https://www.macworld.com/article/228196/these-are-the-apple-design-award-winners-of-wwdc-2016.html)). Bold orange on black, very large simple targets, a **six-task hard limit as a design constraint**. Old, but the canonical "one accent + black + oversized numerals" habit UI.
- **The Outsiders: Athlete Tracker** — **ADA FINALIST, 2026, Interaction** (winner was Moonlitt). Same studio as Gentler Streak. Hero is a **Training Readiness Score presented alongside its inputs**, the "one composite number plus its provenance" pattern.
- **Harvee** — **ADA FINALIST, 2026, Social Impact** (winner was Primary: News in Depth).
- **Opal** — **ADA FINALIST, 2025, Social Impact** (winner was Watch Duty). **Award-level evidence only; no credible teardown found.** Treat as a reference to go screenshot, not a cited-technique source.
- **Athlytic** — no Apple award, but **MacStories Selects Best Watch App**. Single-purpose recovery score readable "in under 10 seconds", no account, local-first.

---

## The hero-numeral pattern

Because this is the specific detail that separates CRED's screen from the "cartoonishly big and bold" one that got roasted in [06 §1](06-social-sentiment.md).

**Size, evidenced.** WHOOP's hero at **~72pt equivalent**, with the rationale that it must be readable **at arm's length, not reading distance**. That reframes the brief: **the hero numeral is a glance target and everything else on the screen is reading-distance.** Oura states the same idea as "one big thing."

**Tabular figures, evidenced and non-negotiable.** Apple's HIG states SF Pro "uses the OpenType tabular lining feature to support the display of monospaced numbers and currencies" ([HIG](https://developers.apple.com/design/human-interface-guidelines/foundations/typography/)). Proportional digits make a live-updating number **jitter**, and make a column ragged: $1,111.00 must occupy the same width as $8,888.00 ([Use Your Loaf](https://useyourloaf.com/blog/monospace-digits/)). RN: `fontVariant: ['tabular-nums']`. **Highest-confidence finding in this file.**

**Weight, the honest answer.** **No primary source states a specific weight for a hero numeral in any of these apps.** WHOOP's teardown gives the size and explicitly declines to name typeface or weight. The premium-versus-cartoonish distinction is real and observable, but the evidence is indirect:
- Revolut's display setting reportedly uses **Aeonik Pro at weight 500 (medium, not bold)** up to 136px, per [getdesign.md](https://getdesign.md/design-md/revolut/preview). **Secondary, machine-generated, and web-derived. Treat as weak corroboration only.**
- Strava's is the strongest *cited* decision: numerals moved to Inter because it was more stable at those sizes, keeping the expressive face for brand only.
- The cartoonish register is where heavy weight and playful faces sit.

**Tracking: no primary evidence found. Do not fabricate a value; derive it optically.**

**Practical synthesis for React Native:** one hero numeral per screen at roughly 64 to 80pt, in the system face at **Medium to Semibold rather than Black**, `fontVariant: ['tabular-nums']`, slight negative tracking to close the gaps large tabular digits open, a small unit glyph at a fraction of the numeral size and baseline-aligned, everything else at reading-distance sizes.

---

## Excluded, and why

Stated honestly rather than padded.

- **Mercury, Stripe, Linear, Raycast, Vercel** — web or desktop reputation. Excluded per the mobile-only rule.
- **Revolut** — **excluded as a primary source.** Everything findable (getdesign.md, shadcn.io, various `DESIGN.md` repos) is machine-generated analysis of Revolut's **marketing website**, not the phone app, and the tokens quoted are web-scale.
- **N26, Emma, Snoop, Plum** — no design press, agency case study or award. Only competitor listicles.
- **Bezel** — no evidence it exists in a design-award or design-press context. Not in ADA 2024, 2025 or 2026. **I listed it as a candidate earlier; that was unfounded.**
- **Bevel** — exists on the App Store, but **no Apple Design Award or App Store Award found**. Do not cite it as award-winning.
- **one sec** — no ADA or App Store Award found. Opal, its competitor, is a verified 2025 finalist.
- **Rainbow, Phantom, Zerion** — no awards or credible teardowns. Zerion shipped a full mobile redesign but published no technique detail. **Family is the only crypto wallet in this set with a real cited design source.**
- **Peloton, Nike Run Club, Apple Fitness, Zero, Rise, AutoSleep, Cardiogram, Flo, Balance** — no award or cited commentary surfaced within budget. Excluded rather than padded.
- **Finch** — **an App Store Award for Finch could not be verified.** Treat that claim as unconfirmed wherever it appears.

**One genuinely interesting finding in the exclusions:** the App Store's 2025 Cultural Impact winner, **Focus Friend**, is "an adorable cartoon character" ([App Store Awards 2025](https://developer.apple.com/app-store/app-store-awards-2025/)). **The cartoon register wins awards too. It just wins different ones, in Cultural and Social Impact, never in Visuals and Graphics.** That is the cleanest available statement of why cute is a legitimate strategy but not *our* strategy.

---

## Mobile-specific principles from this section

1. **Collapse the tab bar and add a "Today".** Oura went 5 to 3; Headspace killed four category tabs for a time-of-day Today plus Explore. Both cite user research. **The premium move is fewer tabs with one opinionated entry point.**
2. **One hero numeral, sized for arm's length, in tabular figures.** Neutral face, moderate weight. Everything else reading-distance.
3. **Single-accent, semantic-colour discipline.** WHOOP's three colours each carry fixed meaning, with no decorative accents.
4. **Set text hierarchy with alpha, not grey values.** CRED: 0.9 / 0.7 / 0.5 / 0.3 on one ink. Portable to RN, survives theme switching. (Resolve to solid hex and measure, per [02 §8](02-typography.md).)
5. **Dark mode is not inversion.** Nubank's three fixes are the checklist: darken *and desaturate* the brand colour, pull body text off pure white, desaturate accents. Ship with token fallbacks, not a big-bang migration.
6. **Bottom sheets overlay, never displace, and height is semantic.** Family's dynamic tray.
7. **Motion must be directional.** Swipe left, animate left. "Avoid static transitions."
8. **Budget delight by frequency.** High-frequency gets subtle craft; rare gets the confetti. **Inverting this is what makes an app feel cheap by week two.**
9. **Depth via painted surfaces, not shadows.** CRED's five faces. No blur cost, works in dark mode.
10. **Brand type and UI numerals are different jobs.** Strava and Cash App both prove it; Robinhood is the exception that paid to have type re-cut for small sizes.
11. **Dense can be premium.** Monarch deliberately shortened rows to raise density. **Airiness is not the same as quality.**
12. **Use the platform's chart primitives.** Copilot, an ADA finalist, chose stock Swift Charts.
13. **Icon systems are expensive and multi-size.** Strava: 1,440 assets across 4 optical sizes. Budget accordingly.
14. **Widgets, tinted icons and alternate app icons are cheap premium signals** unique to mobile.
15. **Customise native components rather than rebuilding them.** Copilot's "heavily tweaked" UIKit is the model.

---

# Part 2: productivity, tools and utilities

## 15. Things 3 (iOS, iPadOS, macOS, watchOS; no Android)

**Awards: Apple Design Award WINNER, 2017.**

**The densest mobile-craft source in this catalog**, MacStories' review ([link](https://www.macstories.net/reviews/things-3-beauty-and-delight-in-a-task-manager/)):
- "The app is dominated by white space, but it uses bold fonts, lovely icons, and thoughtful splashes of color to create a welcoming, easy-to-use environment."
- On haptics: **"in many ways the app feels like it was built with haptic feedback in mind"**, making "every interaction with the app feel that much more real."
- The Magic Plus Button: "Tap and drag the button into your list of projects to create a new project. Drop it into a list of tasks in Today to create a new task in that exact spot."
- Gestures, quoted directly: "You can long-press a task to make it pop out of the list so you can drag it elsewhere"; "swipe right on a task to quickly reschedule it, or swipe left on a task to select it."

**Mobile-specific techniques:**
- **A draggable FAB that doubles as an insertion-point picker.** The creation affordance and the ordering affordance are the same gesture.
- **Two-direction row swipe with different semantics:** right reschedules, left multi-selects. **Left is deliberately not delete**, a considered deviation from the iOS default.
- Long-press "pop out of the list" lift before drag, with a haptic on lift.
- Whitespace-dominant rows, bold weight for the title, colour used only as **small accent glyphs** (project dots), never as backgrounds.
- **Haptics as a first-class layer rather than a garnish.**

> **The most directly stealable app in this list**, because it is a task list with rows, swipes and tiers, which is structurally our app.

---

## 16. Structured (iOS, iPadOS, macOS, watchOS)

**Awards: Apple Design Award 2026 FINALIST, Inclusivity. Not the winner** (Inclusivity winners were Pine Hearts and Guitar Wiz). Apple's [newsroom](https://www.apple.com/newsroom/2026/06/apple-reveals-winners-of-the-2026-apple-design-awards/) is canonical here; the `developer.apple.com` landing page reads ambiguously and is easy to misquote.

Apple's citation: members of the neurodivergent community praise **"its simple layout"**; built with SwiftUI; "excels not just at optimizing open slots on your calendar, but also at helping you find time to take breaks."

**Mobile-specific techniques:**
- **A single vertical day timeline as the primary screen.** One scrollable column, no tab-bar mode switching for the core view.
- Per-task colour plus glyph as the row's entire identity. **Text weight stays uniform and colour carries the scanning load.**
- **Deliberately low information density per row** so the day reads at a glance. That is the trait the neurodivergent audience is quoted praising.

> Relevant to us because our "Your day" ruler is attempting the same job with a lot more chrome.

---

## 17. Flighty (iOS, iPadOS, watchOS, macOS)

**Awards: Apple Design Award WINNER, 2023, Interaction.**

Apple's [Behind the Design](https://developer.apple.com/news/?id=970ncww4) is unusually specific, and this app matters to us more than its category suggests:
- Ryan Jones: **"We want Flighty to work so well that it feels almost boringly obvious."**
- The visual language is lifted from physical airport signage: **"Those airport boards have one line per flight, and that's a good guiding light, they've had 50 years of figuring out what's important."**
- Dynamic Island: "the Dynamic Island switches over to flight progress bars and counters, displaying minimal presentation in a simple circular chart that tracks a flight's duration."
- Offline-first premise: "Whenever [someone] takes off, we have to assume that we won't see them again until they land."
- Process: **20 concepts per problem, because "it's what fits on a sheet of paper."**

**Mobile-specific techniques:**
- **One line per flight as the row spec**, borrowed from departure boards. A literal, citable row-density rule.
- **Dynamic Island presentations designed as a different information design**, not a shrunken card.
- Widgets treated as first-class surfaces.
- **"Shine when things go awry":** the delay and diversion states get the design investment, not the happy path.

> **Two ideas we should take directly.** "One line per item, borrowed from a mature physical information design" is exactly the instrument-panel instinct already in `design-system.md`. And **design the urgent state, not the calm one** is precisely our product's job.

---

## 18. Crouton (iOS, iPadOS, macOS, watchOS)

**Awards: Apple Design Award WINNER, 2024, Interaction.**

Devin Davies on subtraction ([Apple](https://developer.apple.com/news/?id=9x75y43e)): **"I spent a lot of time figuring out what to leave out rather than bring in."**
- Cook Mode "displays only the current step, ingredients, and measurements... no swiping around between apps to figure out how many fl oz are in a cup; no setting a timer in a different app."
- The governing metric: "How quickly can I get you back to preparing the meal, rather than reading?"
- Apple's citation: "lets users keep their focus on the counter rather than the screen."

**Mobile-specific techniques:** a **dedicated modal "do the thing" mode** that strips chrome to one step, turning the phone into a single-purpose appliance; and **inlining every side-errand** so the user never leaves the mode. Davies explicitly "leaned on platform conventions" for navigation.

---

## 19. Halide Mark II (iOS, iPadOS)

**Awards: Apple Design Award WINNER, 2022, Visuals and Graphics.** Apple's citation: "focuses on the essentials."

From [Behind the Design](https://developer.apple.com/news/?id=x6bv1a36):
- **"A camera is an extension of your body, and it works best when it creates muscle memory. We need to have consistent gestures. We need to be flexible without changing buttons around all the time."**
- **"Color, too, is used carefully and deliberately in Halide, with a single yellow highlight color used to indicate active state for a feature."**
- The anti-pattern they rejected: "Other camera apps looked like **flight simulators with lots of dials**, which was intimidating."
- **A documented failure worth learning from:** colour-alone state was unreadable. A real-world test where a user could not tell if RAW mode was on "helped the team update the feature's button design to better reflect each individual mode when selected."

**Mobile-specific techniques:** exactly one accent colour reserved for active state; **gesture axes permanently assigned to parameters** (up/down exposure, left/right focus) so muscle memory holds; controls in the lower third near the thumb.

---

## 20. (Not Boring) Habits (iOS)

**Awards: Apple Design Award WINNER, 2022, Delight and Fun**, *and* a **finalist** in Visuals and Graphics the same year.

From [Behind the Design](https://developer.apple.com/news/?id=9ab1g4r3):
- "The app's checkbox is **no mere tappable square**, it's an interactive event replete with explosive 3D animations, custom sounds, and playful haptics."
- Built in **SceneKit** tied together with UIKit and SwiftUI views. Models in Blender.
- On deliberately slow gestures: "you have to intentionally press on the screen for longer than you might think... it's a very big, gross interaction", and **"we needed feedback that told you you needed to keep holding."**
- **"Thousands of iterations"** on the single checkbox.

**The transferable pattern, and it is the important one:** **one hero interaction gets 90% of the craft budget and everything else stays stock UIKit/SwiftUI.** Also: press-and-hold with escalating feedback instead of tap, and sound plus haptic plus particle fired as one synchronised event.

---

## 21. Sequel (iOS, iPadOS) — the current-idiom reference

**Awards: MacStories Selects 2025, Best Design WINNER.**

**The best documented example of the Liquid Glass era iPhone navigation idiom** ([MacStories](https://www.macstories.net/stories/macstories-selects-2025-recognizing-the-best-apps-of-the-year/)):
- Credited for "its sophisticated implementation of Liquid Glass on iPhone, which enabled a complete navigation rethink."
- **Universal search as a third navigation button that "expands upon being pressed into a search bar"**, searchable from anywhere.
- **iPhone navigation reduced to two primary tabs (Saved / Collections) plus search.**
- "A gorgeous new media detail view with **header images that morph seamlessly into blurred backgrounds as you scroll**."
- "Let your content and artwork take center stage."

**MacStories makes the distinction explicitly: Liquid Glass used for usability gains, not decoration.** See the note in [09 §2](09-mobile-design-principles.md) about why that does not contradict the anti-glassmorphism finding.

---

## 22. Dark Noise (iOS, iPadOS, watchOS)

No award, but the developer publishes his reasoning, which makes it unusually useful.

Charlie Chapman's [own post](https://charliemchapman.com/posts/2019/9/2/designing-dark-noise/):
- He made **"a looping animation for each of the static noise icons"**, which **solved the playing-state indicator problem** while adding personality. **An animation that is functional, not decorative.**
- "the main swiping gesture for minimizing the player" existed from the earliest design.
- The guiding constraint: **"Keep it dark"**, designed for people "possibly without their glasses on or half asleep."

**Mobile-specific techniques:** **animation as state** (the icon's loop *is* the now-playing indicator, with no separate badge); swipe-down-to-minimise as the primary navigation gesture; **designing against a specific physical context** rather than against "clean design".

---

## 23. iA Writer, Bear, Agenda, Reeder, Timepage, Streaks, Shareshot, Play

- **iA Writer** — **ADA 2025 Interaction FINALIST, not the winner** (Taobao won). Apple's citation names mobile-specific craft: **a customizable keyboard**, selective text highlighting, **intuitive swipe gestures**. Its custom duospaced face is the app's identity.
- **Bear** — **ADA WINNER 2017**, cited for "a flexible, elegant writing tool... consistently fast." Themed typography as a paid feature; inline markdown rendering removes a mode from a small screen; tag-based navigation collapses depth on iPhone.
- **Agenda** — **ADA WINNER 2018**, cited for "minimalistic design... elegant typography, powerful search and navigation." A continuous past-present-future timeline as the spine, so **scrolling is time navigation**.
- **Reeder (2024 rebuild)** — **MacStories Selects 2024, Best Design runner-up.** One chronological timeline replacing folder hierarchy, which collapses navigation depth to near-zero on a phone. Its sibling **Mela** was an **ADA 2025 Interaction FINALIST**.
- **Timepage (Moleskine)** — no ADA. **Heat Map:** "days on the calendar have deeper colors when more events are planned for them", so **colour saturation encodes density with no numbers and no badges**. **Horizontal paging between whole view-modes** instead of a tab bar. Pull-down-to-create as the single creation gesture, no FAB.
- **Streaks** — **ADA WINNER 2016.** A hard cap of **12 tasks** in a fixed grid of large circular tiles, a constraint that guarantees one screen, no scroll, thumb-sized targets.
- **Shareshot** — **MacStories Selects 2024, Best Design WINNER.** "The entire editing process happens in a single view is a testament to the amount of thought and care." **Zero-navigation design:** one view, no push, no modal.
- **Play** — **ADA WINNER 2025, Innovation.** The one genuine mobile-native *developer* tool here: prototyping **on the device itself**, so the design surface and the preview surface are the same phone.

---

## Excluded from Part 2, and why

| App | Why |
|---|---|
| **Craft** | Its award is **Mac App of the Year 2021**, a desktop award. Not an ADA winner. No phone-specific teardown found. |
| **Ulysses, Tot** | Mac-first reputation; all substantive design commentary concerns the desktop product. |
| **Superhuman** | **Design reputation is entirely the desktop and web client.** No credible mobile-specific coverage. **This retires it from the shortlist**, where I had it in Tier 1. |
| **Notion, Linear, Raycast, Vercel, Stripe** | Web and desktop by definition. Linear's mobile app is a companion, not the artefact people cite. |
| **NotePlan, Sorted, Amie, Due, Session, Castro, Spark, Parcel, Literal, MacroFactor, Cosmos, Dime, Endel, Arc Search** | **Not excluded on platform grounds, excluded for lack of citable evidence.** Two award facts worth keeping: **Arc Search was an ADA 2024 Interaction FINALIST**, and **Endel won Apple Watch App of the Year 2020** (an App Store Award, not an ADA). |

---

## Additional mobile principles from Part 2

16. **Borrow a row spec from a mature physical information design.** Flighty's departure board: one line per item, 50 years of refinement behind it.
17. **The premium goal is invisibility, not expressiveness.** "We want Flighty to work so well that it feels almost boringly obvious."
18. **Design for the failure state, not the happy path.** "We really have to shine when things go awry."
19. **Subtraction is the interaction skill.** "I spent a lot of time figuring out what to leave out rather than bring in."
20. **Concentrate craft in one hero interaction; keep the rest stock.** (Not Boring) Habits' checkbox took thousands of iterations while the surrounding app is plain UIKit.
21. **Long-press needs continuous feedback telling the user to keep holding.**
22. **Haptics designed in from the start, not added.** MacStories on Things 3.
23. **Make the creation gesture also express placement.** Things' Magic Plus.
24. **Animation should carry state, not decorate it.** Dark Noise's looping icons.
25. **Design against a specific physical context**, not against an abstraction. "Without their glasses on or half asleep."
26. **Fewer tabs; promote search out of the tab set.** Sequel won Best Design 2025 for exactly this.
27. **Scroll-linked continuous transforms beat crossfades.**
28. **Single-view editing is a design achievement.** Shareshot.
29. **Know the host OS's conventions before deviating.**
30. **Copy is a design material with a tone spec.** Gentler Streak: "supportive but not cheesy, motivating but not fake-hyped", validated with 15 to 20 beta testers **per language**.
31. **Expressive is not the same as premium.** John Gruber on Tiimo, the reigning iPhone App of the Year: the emoji-heavy look is **"distracting and childish"** rather than clarifying ([Daring Fireball](https://daringfireball.net/2025/12/2025_app_store_award_winners)). **Independent confirmation of our own ban on emoji as section markers.**

**Published numeric values (iOS 26 baseline)** from [learnui.design](https://www.learnui.design/blog/ios-design-guidelines-templates.html): Large Title 34pt bold; small title 17pt semibold; body and list rows 17pt regular; secondary 15pt; tertiary 13pt; tab bar labels 11pt; **tab bar inset 21pt from left, right and bottom**; home indicator reserves a 21pt-tall box; minimum tap target 44x44pt; **primary working canvas 390x844pt**.

---

## An important gap, stated plainly

**No app in this entire catalog publishes its own type scale, spacing tokens or hex palette**, with the single exception of CRED. The Sketch interview with Gentler Streak explicitly discloses no hex values, no spacing units and no font families.

**Concrete numbers exist only at the platform level (Apple HIG, Material 3) and in CRED's open-source repo.** Everything else has to be measured from screenshots, which is exactly what step 2's teardowns are for.

---

## Award corrections to carry forward

All four of these are commonly misreported, and we should not repeat them:
- **Structured** is a **2026 ADA finalist**, not a winner.
- **Copilot Money** is a **2024 ADA finalist (Innovation)**, not a winner, and not an App Store Award winner.
- **iA Writer** is a **2025 ADA finalist (Interaction)**, not a winner. Apple's own awards page reads as if it won; the newsroom release is canonical and says Taobao won.
- **Tiimo** is a **2024 ADA finalist** *and* a **2025 App Store Award winner**. Two different programmes, frequently conflated.
- **Family** has **no Apple Design Award at all.** Its reputation is peer and design-community.

---

## Sources, Part 2

[MacStories on Things 3](https://www.macstories.net/reviews/things-3-beauty-and-delight-in-a-task-manager/) · [Apple newsroom ADA 2026](https://www.apple.com/newsroom/2026/06/apple-reveals-winners-of-the-2026-apple-design-awards/) · [ADA 2025 newsroom](https://www.apple.com/newsroom/2025/06/apple-unveils-winners-and-finalists-of-the-2025-apple-design-awards/) · [ADA 2023 newsroom](https://www.apple.com/newsroom/2023/06/apple-announces-winners-of-the-2023-apple-design-awards/) · [ADA 2022 newsroom](https://www.apple.com/newsroom/2022/06/apple-announces-winners-of-the-2022-apple-design-awards/) · [ADA 2018 newsroom](https://www.apple.com/newsroom/2018/06/apple-design-awards-highlight-excellence-in-app-and-game-design/) · [Behind the Design: Flighty](https://developer.apple.com/news/?id=970ncww4) · [Crouton / Devin Davies](https://developer.apple.com/news/?id=9x75y43e) · [Behind the Design: Halide Mark II](https://developer.apple.com/news/?id=x6bv1a36) · [Behind the Design: (Not Boring) Habits](https://developer.apple.com/news/?id=9ab1g4r3) · [Charlie Chapman on designing Dark Noise](https://charliemchapman.com/posts/2019/9/2/designing-dark-noise/) · [MacStories Selects 2025](https://www.macstories.net/stories/macstories-selects-2025-recognizing-the-best-apps-of-the-year/) · [MacStories Selects 2024](https://www.macstories.net/stories/macstories-selects-2024-recognizing-the-best-apps-of-the-year/) · [MacStories on Timepage](https://www.macstories.net/reviews/timepage-a-beautiful-and-clever-calendar-app/) · [MacStories on Agenda for iOS](https://www.macstories.net/reviews/agenda-for-ios-review/) · [MacStories ADA 2017](https://www.macstories.net/news/apple-design-awards-2017-winners-announced/) · [Bear ADA post](https://blog.bear.app/2017/06/thank-you-yes-you-for-our-2017-apple-design-award/) · [Crunchy Bagel ADA 2016](https://crunchybagel.com/apple-design-awards-2016/) · [Daring Fireball on the 2025 App Store Awards](https://daringfireball.net/2025/12/2025_app_store_award_winners) · [MacRumors, 2025 App Store Awards](https://www.macrumors.com/2025/12/04/apple-announces-2025-app-store-award-winners/) · [Kino, iPhone App of the Year](https://www.lux.camera/kino-is-iphone-app-of-the-year/) · [App Store Best of 2020](https://www.apple.com/newsroom/2020/12/apple-presents-app-store-best-of-2020-winners/) · [Craft, Mac App of the Year](https://www.businesswire.com/news/home/20211202005370/en/) · [learnui.design iOS guidelines](https://www.learnui.design/blog/ios-design-guidelines-templates.html) · [WWDC25 284](https://developer.apple.com/videos/play/wwdc2025/284/)

---

## Sources, Part 1

[NeoPOP colors.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/colors.ts) · [typography.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/typography.ts) · [buttons.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/buttons.ts) · [opacity.ts](https://raw.githubusercontent.com/CRED-CLUB/neopop-web/main/src/primitives/opacity.ts) · [neopop-android](https://github.com/CRED-CLUB/neopop-android) · [neopop-ios](https://github.com/CRED-CLUB/neopop-ios) · [playground.cred.club](https://playground.cred.club) · [Homegrown on CRED](https://homegrown.co.in/article/806427/cred-s-new-design-philosophy-channels-the-unbridled-creative-spirit-of-the-neo-pop-art-movemen) · [UX Planet on CRED's revamp](https://uxplanet.org/thoughts-on-creds-ui-revamp-apr-2022-6d2b4dcfcfc6) · [ADA 2024](https://developer.apple.com/design/awards/2024/) · [ADA 2025](https://developer.apple.com/design/awards/2025/) · [ADA 2026](https://developer.apple.com/design/awards/) · [App Store Awards 2025](https://developer.apple.com/app-store/app-store-awards-2025/) · [Copilot Money and Swift Charts](https://developer.apple.com/articles/copilot-money/) · [Behind the Design: Gentler Streak](https://developer.apple.com/news/?id=3m0ht22s) · [Behind the Design: Headspace](https://developer.apple.com/news/?id=fkfnhq8u) · [Developer Spotlight: Streaks](https://developer.apple.com/news/?id=67dti69d) · [Sketch on Gentler Streak](https://www.sketch.com/blog/gentler-streak/) · [9to5Mac, 2026 ADA finalists](https://9to5mac.com/2026/05/18/apple-unveils-30-apple-design-award-app-finalists/) · [925 Studios, WHOOP breakdown](https://www.925studios.co/blog/whoop-design-breakdown) · [WHOOP home screen](https://www.whoop.com/us/en/thelocker/the-all-new-whoop-home-screen/) · [Benji Taylor, Family Values](https://benji.org/family-values) · [Oura app redesign](https://ouraring.com/blog/new-oura-app-experience/) · [Monzo home screen](https://monzo.com/blog/how-we-built-the-new-home-screen) · [Monzo Trends](https://monzo.com/us/blog/monzo-us-blog/trends) · [Nubank dark mode](https://building.nubank.com/the-birth-of-the-dark-mode-a-journey-into-nubanks-app-evolution/) · [Nubank multi-product](https://building.nubank.com/designing-a-multi-product-experience/) · [Robinhood identity](https://newsroom.aboutrobinhood.com/a-visual-identity-that-better-reflects-our-vision/) · [COLLINS x Robinhood](https://the-brandidentity.com/project/collins-robinhood-combine-make-investing-accessible-affordable-engaging) · [Cash App standards](https://standards.site/examples/cash-app/) · [Cash App fonts](https://www.designyourway.net/blog/what-font-does-cash-app-use/) · [Strava fonts](https://sensatype.com/what-font-does-strava-use-in-2026) · [Griff Designs, Strava icons](https://griffdesigns.com/strava) · [Monarch brand refresh](https://www.monarch.com/blog/monarch-brand-refresh) · [Opal ADA finalist](https://opalapp.com/blog/apple-design-award-finalist) · [Athlytic news](https://www.athlyticapp.com/news) · [Macworld, ADA 2016](https://www.macworld.com/article/228196/these-are-the-apple-design-award-winners-of-wwdc-2016.html) · [Crunchy Bagel, ADA 2016](https://crunchybagel.com/apple-design-awards-2016/) · [Slate on Calm](https://slate.com/technology/2017/12/apple-app-store-calm-app-of-the-year-is-a-fitting-choice-for-2017.html) · [Apple HIG Typography](https://developers.apple.com/design/human-interface-guidelines/foundations/typography/) · [SwiftUI monospacedDigit](https://developer.apple.com/documentation/swiftui/font/monospaceddigit()) · [Use Your Loaf, monospace digits](https://useyourloaf.com/blog/monospace-digits/)
