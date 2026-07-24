# Mobile shortlist: 17 phone apps

**Date:** 2026-07-24
**Status: awaiting your approval. This is the decision point between step 1 and step 2.**
**Replaces:** [07-shortlist.md](07-shortlist.md), which was web and desktop contaminated.

**Every app here is a phone app**, analysed on its phone UI. Nothing on this list earned its place on a browser canvas.

---

## Validation gates

Each app states which it passed:

- **P: primary design evidence.** Apple's own award citation or Behind the Design article, the company's design blog, the designer's own published writing, or an open-source design system.
- **U: user or practitioner sentiment.** Named on Reddit, Mobbin Awards, YouTube or Dribbble with visible engagement. See [10-mobile-sentiment.md](10-mobile-sentiment.md).
- **R: relevance.** Dense, list-based, data-carrying, dark-capable, and structurally like a triage feed.

**Awards are stated precisely.** Winner-vs-finalist is misreported constantly, and four such errors are corrected in [08](08-mobile-apps.md).

---

## Tier 1: the seven I recommend

### 1. Things 3 — P, R. Apple Design Award **winner**, 2017
**Structurally the closest app to ours in existence:** a task list with rows, swipes, tiers and a completion device.
**Extract:** the two-direction row swipe with different semantics (right reschedules, left multi-selects, and **left is deliberately not delete**); the long-press "pop out of the list" lift with a haptic; row rhythm and whitespace ratios; colour used only as **small accent glyphs, never as backgrounds**; and the filling-pie completion device. MacStories: **"in many ways the app feels like it was built with haptic feedback in mind."**

### 2. CRED — P (design system is open-source), U, R
**The only app in the entire catalog that publishes real token values**, and they are mobile-native with first-party Android and iOS libraries.
**Extract:** the actual tokens already pulled in [08 §1](08-mobile-apps.md); **the alpha-based text hierarchy (0.9 / 0.7 / 0.5 / 0.3 on one ink)**, which is the single most portable trick found; the big-but-**light** hero numeral; borderless circular icon buttons; **depth via five painted surfaces instead of shadows**, which works in dark mode where shadows fail.
**Caveat:** the hard-edged pop shadow is CRED's signature, not a neutral pattern. There is **no official React Native package**; the five-surface button is four absolutely-positioned Views around a centre View.

### 3. Flighty — P, U, R. Apple Design Award **winner**, 2023, Interaction
**Punches far above its category for us**, because it solved our exact information-design problem.
**Extract:** **"one line per flight"**, a row spec borrowed from departure boards with "50 years of figuring out what's important" behind it; **"we want Flighty to work so well that it feels almost boringly obvious"** as the premium target; Dynamic Island treated as **a different information design, not a shrunken card**; and above all **"we really have to shine when things go awry"** — design the urgent state, not the calm one. That is literally our product's job.

### 4. Halide — P, U. Apple Design Award **winner**, 2022, Visuals and Graphics
The best single source on accent discipline, with a documented failure.
**Extract:** **"a single yellow highlight color used to indicate active state"**; gesture axes permanently assigned so muscle memory holds; controls in the lower third near the thumb; the anti-**"flight simulator with lots of dials"** stance; and the failure worth learning from, that **colour alone was insufficient to signal state and the button form had to change too.** That directly affects how we mark urgency.

### 5. Sequel — U. **MacStories Selects 2025, Best Design winner**
**The current-idiom reference**, and the one that answers "how should tabs look in 2026".
**Extract:** **iPhone navigation reduced to two tabs plus search**, with search **promoted out of the tab set into a button that expands into a search bar**; header images that **morph into blurred backgrounds on scroll** as one continuous transform; and Liquid Glass used for **usability, not gloss** (MacStories makes the distinction explicitly).

### 6. Gentler Streak — P, R partial. Apple Design Award **winner**, 2024, Social Impact
The answer to gamified-but-classy, and it is already clean of web contamination.
**Extract:** comparing the user to **their own history, never to a target or to others**; **demoting the number and promoting the interpretation** ("statistics are just numbers"); copy as a design material with a tone spec, "supportive but not cheesy, motivating but not fake-hyped"; and the fact that an ADA winner shipped on **UIKit, not SwiftUI**.

### 7. Nubank — P, R
**The best-documented dark-mode-at-scale case found**, and dark is our default.
**Extract:** the three documented anti-patterns from naive inversion — **darken *and* desaturate the brand colour** so it survives behind white text, **pull body text off pure white** to kill exaggerated contrast, and **desaturate accents** so nothing glares; plus the **token fallback strategy** that let them ship across 3,000+ screens without a big-bang migration. That last one is exactly how we would roll dark mode into an existing app.

---

## Tier 2: strong, narrower extraction

**8. (Not Boring) Habits** — ADA **winner** 2022, Delight and Fun. **The single most important structural lesson in the list: one hero interaction gets 90% of the craft budget while everything else stays stock UIKit.** Their checkbox took "thousands of iterations". Also: press-and-hold with escalating feedback, and **"we needed feedback that told you you needed to keep holding."**

**9. Structured** — ADA **2026 finalist** (not winner), Inclusivity. A **single vertical day timeline** as the primary screen; per-task colour plus glyph as the row's whole identity with **uniform text weight**; deliberately low density per row. Directly relevant to our "Your day" strip.

**10. Family** — **no award**, peer reputation only. The richest mobile-motion source anywhere: **dynamic trays that overlay rather than displace, with tray height used semantically**; direction-matched transitions; and **the delight budget** — high-frequency features get subtle touches, low-frequency get the confetti.

**11. WHOOP** — no award. **The only hard hero-numeral number found: ~72pt, sized to read at arm's length.** Near-black justified functionally. A strict three-colour semantic palette. **But see [05 §6](05-gamification-that-stays-premium.md) for the user evidence against copying its RAG bands.**

**12. Copilot Money** — ADA **2024 finalist** (not winner), Innovation. **UIKit components "heavily tweaked" rather than rebuilt**; local-first data for perceived speed; and an ADA finalist still choosing **stock Swift Charts**.

**13. stoic.** — Mobbin trending, U only. **Near-monochrome, all hierarchy from weight and space**, outlined pill buttons rather than filled, tiny uppercase letterspaced eyebrows. Proof that our restraint instinct can read premium without a second accent.

---

## Tier 3: one specific lesson each

**14. Dark Noise** — **animation as state**: a looping icon *is* the now-playing indicator, no separate badge. Plus designing against a specific physical context ("without their glasses on or half asleep").

**15. Timepage** — **colour saturation encodes density with no numbers and no badges**; horizontal paging between whole view-modes instead of a tab bar; pull-down-to-create as the only creation gesture.

**16. Streaks** — ADA **winner** 2016. A **hard cap of 12 tasks** as a design constraint that guarantees one screen, no scroll, thumb-sized targets.

**17. The Exoplan teardown** (r/iosapps, 498 points) — **deliberately included as the anti-reference.** A working designer's list of what still reads amateur on a much-loved app, and **four of the five apply to us**: filled dots reading as notification badges rather than selection, ambiguous nav icons, icons too small for HIG minimums, and **an empty state faked as a full state**. See [10 §2](10-mobile-sentiment.md).

---

## Excluded, and why

- **Superhuman.** **Retired from Tier 1**, where I wrongly placed it. Its design reputation is entirely the desktop client; no credible mobile-specific coverage exists.
- **Linear, Raycast, Vercel, Mercury, Monzo's design system, Notion, Stripe.** Web and desktop reputation. Monzo's *phone-app* posts are cited in [08 §10](08-mobile-apps.md), but its design-system fame is web. **Notion is the sharpest case: designers praise it as a product then attack it specifically on mobile** ("Notion's Android Mobile app is so glitchy", and on iOS "neither, from a designer's pov"). **Web reputation does not transfer to phone.**
- **Craft.** Its award is **Mac App of the Year 2021**, a desktop award. Not an ADA winner.
- **Bezel.** No evidence it exists in any design-award or design-press context. **I listed it as a candidate in round one; that was unfounded.**
- **Bevel, one sec, N26, Emma, Snoop, Plum, Rainbow, Phantom, Zerion, Peloton, Nike Run Club, Apple Fitness, Rise, Flo, Balance.** No award or citable design commentary found. **Excluded rather than padded.**
- **Revolut.** Everything findable is machine-generated analysis of its **marketing website** at web scale, not the phone app.
- **21st.dev.** Investigated twice, as you asked. **It has no Tab Bar, Bottom Sheet, App Bar, Segmented Control or gesture category at all**, and its "mobile" tag mostly means "is a picture of an iPhone." It is a registry for marketing sites. **Mobbin is the correct substitute.** Full numbers in [10 §5](10-mobile-sentiment.md).

---

## The three questions I need answered

**1. Which apps do you want torn down?** My seven, or a different cut. Seven is the realistic number for measured teardowns.

**2. Deep green or electric blue as the single accent?** Both are well evidenced. Green reads calm and permanent and matches the "quiet instrument" positioning in the product brief; blue reads precise and technical and matches the developer wedge. **A brand call, not a research call.**

**3. Does the mono-for-data signature survive?** Our locked spec sets *all* labels, chips and channel names in mono. The research says mono reads premium on a narrow slice (numbers, timestamps, refs, IDs) and reads costume-y when it becomes the vibe. **My recommendation: keep it, narrow it to those four uses, and replace Menlo with Geist Mono.** Confirm or overrule.

---

## What changed because of the mobile-only redo

Worth stating plainly, since the redo was your call and it materially changed the output.

**Six of my seven original Tier 1 picks are gone.** Only CRED, Things 3 and Halide survived. Linear, Vercel, Superhuman and Oura's tier all moved or dropped.

**Three round-one recommendations are now retired outright, not merely caveated:**
- **The motion tokens.** Duration plus cubic-bezier is a web model. iOS uses springs, and the reason is mechanical: **springs accept an initial velocity so a gesture can hand off its release velocity seamlessly, while a cubic-bezier always starts from rest.** That is why interrupted web-style animations look broken.
- **"Hide some icons behind hover."** There is no hover. Swipe, long-press or a sheet.
- **Linear's absolute padding values.** Web-derived. The ratios hold; the numbers do not.

**And three genuinely new things surfaced that the web pass could never have found:**
- **The tab bar** is the highest-leverage component in the product, it is OS-owned furniture with a fixed 49pt height and a hard 5-item cap, and **the 2026 premium idiom is a floating pill detached from the screen edge.** Our four placeholder squares sit in exactly that space.
- **Haptics** are an entire perceptual dimension with no web equivalent, cheap via `expo-haptics`, and repeatedly named as the thing that makes an app feel expensive.
- **Density works backwards from web.** A web row can be 32px; a mobile row is 44pt because **the row is the touch target**. You do not get density by shrinking rows, you get it by removing content from rows and **pushing actions into swipe**. Our feed card's two visible buttons should be swipe actions.

---

## What step 2 produces, once you approve

1. **A measured teardown per approved app:** row heights, chip padding ratios, type sizes and weights, radii, icon sizes and stroke weights, tab bar treatment, accent surface area, gesture and haptic inventory.
2. **A new design system spec**, dark by default and light as the alternate, in OKLCH on Radix step roles: 6 type sizes that survive Dynamic Type, 3 weights, 8 spacing values, 4 radii plus a pill, one accent, one icon family, spring-based motion, and a haptic map.
3. **A resolution of the `design-system.md` versus `theme.ts` conflict.** One of the two has to be retired deliberately.
4. **A redlined redesign of the Home screen and the tab bar**, the two worst offenders, before anything is generalised.
5. **Only then, code.**

**One honest note on evidence:** apart from CRED, **no app in this catalog publishes its type scale, spacing tokens or palette.** Concrete numbers exist only at the platform level and in CRED's repo. Everything else has to be measured from screenshots, which is precisely what the teardowns are for. A Mobbin subscription would make that materially faster.
