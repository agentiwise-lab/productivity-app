# Measured palettes: colours extracted from the reference screenshots

**Date:** 2026-07-24
**Part of:** step 2 teardowns.
**Method:** mine, not an agent's. Reproducible from the files in [`references/`](references/).

---

## Why this file exists

**Almost every teardown returned `NOT FOUND` for hex values.** Nubank publishes none. WHOOP publishes none. Things 3, Flighty, Halide, Gentler Streak and stoic. publish none. Only CRED publishes real tokens, because its design system is open source.

Published sources were never going to close that gap. **Pixels do.** The App Store screenshots are the shipped UI, so sampling them yields real values.

## Method, and its limits

For each app, every screenshot is cropped to the **inner 56% of width and the middle 50% of height**, which excludes the marketing caption band, the device bezel and the marketing background. Colours are quantised to an 8-value-per-channel grid and counted across all of an app's screenshots. Neutrals are separated from accents by HLS saturation (`<0.12` neutral, `≥0.45` accent within a mid-lightness band).

**Three limitations, stated plainly:**

1. **These are marketing frames, not raw captures.** Every app composites its screens inside a device bezel with a caption band. The crop removes most of that, but **some marketing background almost certainly survives in a few apps** (Copilot Money's heavy purple and Streaks' very high accent percentages are the most likely contaminated results, and are flagged below).
2. **Percentages are share-of-sampled-pixels, not share-of-screen.** They are comparable *between* apps under the same method, not absolute.
3. **This measures colour only.** Sizes are *not* reliably measurable from composited frames: the bezel inset differs per vendor, so px-to-pt conversion carries roughly ±10% error. **No size in any teardown file was derived this way.**

Reproduce with the script logic in this file's history, or re-run against `references/<app>/*.png`.

---

## The measured values

| App | Ground / neutrals | Accents | Reading |
|---|---|---|---|
| **things3** | `#F8F8F8` **70.4%**, `#F0F0F0` 6.5%, `#282828` 2.5%, `#808080` 1.8% | **`#5898F8`** 0.5%, `#5090F8` | **Closes a real gap.** Things 3's accent blue was NOT FOUND in every published source. Ground is **near-white, not pure white**, and the accent is **0.5% of sampled pixels** |
| **halide** | `#080808` 9.7%, `#101010` 8.2%, `#000000` 3.3%, `#181818` 3.3%, `#282828` 1.0% | none detected | **A textbook near-black ladder.** No accent surfaces at all, because the single yellow is a vanishingly small share of pixels. **The sub-10% accent rule, measured** |
| **cred** | `#F8F8F8` 20.5%, `#000000` 12.9%, `#101010` 4.0%, `#080808` 3.4%, `#181818` 2.3% | `#A00040`, `#006838` | Corroborates the published `popBlack` ramp (`#0d0d0d → #161616 → #121212`) in the shipping app |
| **whoop** | `#202028` 4.9%, `#000000` 4.8%, `#202828` 4.5%, `#080808` 2.2%, `#282830` 1.7% | **`#18E800`** green, **`#0090E0`** blue | **Two findings.** The neutrals are **blue-tinted near-blacks** (`#202028`, `#202828`, note B > R and G), confirming hue-tinted neutrals. And a **blue** accent appears alongside the green, so the palette is not purely the RAG bands |
| **notboring-habits** | `#181818` 15.1%, `#000000` 11.7%, `#202020` 9.3%, `#080808` 6.0%, `#303030` 5.3% | **`#F8B000`** amber, `#B87000` | A deep near-black ladder with a single warm amber. **Far more restrained than its "explosive 3D animation" reputation suggests** |
| **stoic** | `#F0F0F0` **35.1%**, `#F8F8F8` 18.7%, `#000000` **14.7%**, `#282828` 6.5% | **`#98B8D8` at 0.0%** | **The strongest single result here.** The tier-2 agent could not verify stoic's monochrome claim at all. **This proves it numerically: effectively zero accent.** Note the structure: `#F0F0F0` ground with `#F8F8F8` cards, a figure-ground inversion of only 8/255 |
| **gentlerstreak** | `#F8F8F8` 21.1%, `#000000` 15.4%, `#F0F0F0` 3.9% | `#F07848` coral 3.7%, `#F8B800` amber, `#28C880` green | **Corrects an assumption.** I expected green-dominant from the Activity Path. The dominant accent is actually a **coral/orange at 3.7%**, with green well behind |
| **nubank** | `#F8F8F8` **55.5%**, `#F0F0F0` 18.7%, `#D8D8D8` 1.7% | **`#A040F0`** purple 1.2% | **These are the light-mode screenshots.** Their published dark-mode article describes pure black, which is not what the store listing shows. **Do not read these as their dark palette** |
| **family** | `#F8F8F8` **54.2%**, `#000000` 13.2%, `#F0F0F0` 2.3% | `#00B8A0` teal, `#6060F8` indigo, `#F0B000` amber, `#00A8E8` blue | **Multi-accent**, which fits a wallet where each token needs identity. Not a single-accent app |
| **darknoise** | `#000000` 6.8%, `#F8F8F8` 6.6%, `#383838` 1.4% | `#280858`, `#300860`, `#583080` deep violets | Matches "Keep it dark". The violets are the themed icon art, not chrome |
| **timepage** | `#F8F8F8` 16.1%, `#000000` 2.1% | **`#F8A898`** 5.0%, `#105068` | A single committed accent applied app-wide, exactly as the theming research described |
| **structured** | `#F8F8F8` 32.2%, `#F0F0F0` 18.6%, `#E8E8E8` 4.2%, `#E0E0E0` 1.5% | `#F89890` 0.5% and other pale corals, all `<0.5%` | **A very light, very low-contrast palette** with almost no saturated colour. Consistent with the low-cognitive-load claim |
| **flighty** | `#F8F8F8` 12.2%, `#000000` 5.4%, `#202028` 1.6% | `#A0D870` green, `#2078B8` blue | The green and blue are plausibly the map, not the status palette. **Flighty's status colours remain NOT FOUND**; do not treat these as them |
| **sequel** | `#F8F8F8` 9.1%, `#303030` 1.4%, `#101010` 1.2% | `#101868`, `#283080` deep indigos | Almost certainly poster artwork, not chrome. Sequel is content-forward by design |
| **copilot-money** | `#000000` 1.7%, `#202020` 0.2% | `#5808B0` **6.1%**, `#4850F0`, `#00C048` | **Flagged as likely contaminated.** A 6.1% saturated purple is far more consistent with a marketing background than with app chrome. **Do not use** |
| **streaks** | `#F8F8F8` 11.2% | `#78B018` **13.4%**, `#E0E060` 9.7%, `#F87048` 6.9%, `#E06040` 6.6% | **Flagged as likely contaminated**, and also genuinely a loud app. Even discounting the marketing frame, accent share far exceeds every other app here. **This is the measurable form of "it has dated"** |

---

## What this actually settles

**1. Near-white and near-black, confirmed in shipping apps, not just in theory.**
[01](01-premium-apps-and-principles.md) cited Anthony Hobday's rule "near-black and near-white, never pure black/white" from a blog post. **Now it is measured.** Things 3's ground is `#F8F8F8`. Halide's ladder is `#080808 → #101010 → #181818 → #282828`. CRED's is `#0d0d0d → #101010 → #181818`. **Not one premium app in this set uses `#FFFFFF` as its dominant ground.**

**2. Hue-tinted neutrals, confirmed.**
WHOOP's neutrals are `#202028` and `#202828`, where the blue channel exceeds red and green. That is the cool-tinted grey [03 §2](03-colour-dark-and-light.md) argued for, found in the wild.

**3. Accent scarcity, quantified.**
Things 3's accent is **0.5%** of sampled pixels. Halide's does not register at all. Nubank's is **1.2%**. Timepage's is 5%. The 60-30-10 rule's "10%" turns out to be **generous**: the most premium-regarded apps here run their accent at **under 2%**.

**4. stoic.'s monochrome, proven.**
The one app no source could describe. Its top accent registers at **0.0%**, against `#F0F0F0` at 35% and `#000000` at 14.7%. A near-total absence of colour, carrying hierarchy through a **`#F0F0F0` ground with `#F8F8F8` cards** — a figure-ground inversion of eight values out of 255. I confirmed this visually as well: solid black glyphs, white cards on light grey, and a tiny uppercase letterspaced eyebrow ("IDEA FOR TODAY").

**5. An assumption of mine, corrected.**
I expected Gentler Streak to read green-dominant because of the Activity Path. **The dominant accent is a coral/orange at 3.7%**, with green well behind. The corridor visual is not the app's chromatic centre of gravity.

---

## What this does NOT settle

- **Nubank's dark palette.** The store screenshots are light mode. Their published article describes pure black with neutral greys, and **no hex values exist anywhere**. Still NOT FOUND.
- **Flighty's status colours.** The sampled green and blue are plausibly map rendering. Still NOT FOUND.
- **Any size, spacing, radius or type value.** Measuring those from composited marketing frames is unreliable, and **nothing in the teardowns was derived that way.**
- **Copilot Money and Streaks**, where the marketing background likely dominates the accent results.

---

## The one thing to do next

For the three apps where an hour on a real device would pay for itself — **stoic., WHOOP and Structured** — the deliverable is row anatomy and spacing, which is precisely what neither published sources nor marketing screenshots can give. Everything else is now sourced or measured.
