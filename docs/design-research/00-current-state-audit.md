# Current state audit: why the UI does not read as premium

**Date:** 2026-07-24
**Status:** Step 1 of 2. This is the diagnosis. The research findings sit alongside it; the redesign spec is step 2 and is not written yet.
**Scope:** read-only audit. No existing file was modified to produce this.

This document answers one question with evidence rather than opinion: *what, specifically, in the code and the mockups is producing the "nobody put effort into this" reaction?* Every claim below cites a file and a line so it can be checked and, later, fixed.

---

## 1. What was already decided, and when

Reconstructed from git history, so the redesign does not re-litigate settled ground or repeat a discarded direction.

| Commit | What it established |
|---|---|
| `bab18be` | 25 screen explorations. Breadth-first search of layouts. |
| `c80c738` | "Locked" design system + first mobile mockups. |
| `217054b` | Rebuilt on **Warm Sand**: 5 warm palettes explored, full screen set drawn. |
| `271578f` | **Sand & Slate** screen set; this is the palette that shipped. |
| `c24a356` | Four options for the "Your day" strip, numbers defined. |
| `a7ff94c` | Home = time ruler + swipeable card feed + grouped list. |
| `7cc348d` → `cd1c955` | Implementation and repeated *corrective* passes: card padding, one list-row shape everywhere, two-column tiles so labels stop wrapping. |

Two things stand out.

**The exploration was broad but shallow on craft.** 25 layout explorations and 5 palette explorations happened, but they were explorations of *arrangement and hue*. There is no commit in the history that establishes a type scale, a spacing scale, a radius ramp, or an icon system. Those are precisely the layers that carry perceived quality.

**The last five commits are all repair work.** "Card padding", "one list-row shape everywhere", "labels stop wrapping their last letter", "fix the visual breaks". Symptoms were being fixed one at a time at the component level. That is the signature of a missing system: without shared proportion rules, every component has to be corrected individually and the corrections never converge.

---

## 2. The specification and the implementation are two different designs

This is the single largest finding, and nothing else can be fixed cleanly until it is resolved.

[`docs/design-system.md`](../design-system.md) is labelled "locked" and declares itself "the contract for the mobile UI. Implement against them, do not invent new values." [`mobile/src/theme.ts`](../../mobile/src/theme.ts) implements something else entirely.

| | design-system.md (the "contract") | theme.ts (what actually ships) |
|---|---|---|
| App background | `#F6F7F9` light / `#0B0E12` dark | `#F4F1EC` — warm cream, **light only** |
| Accent | `#0E5C4B` / `#3FA98F` — deep green | `#2F4858` — slate blue |
| Urgency | `#B4530F` / `#E0913F` | `#B25B33` |
| Neutrals | "cool blue bias **on purpose**. Do not substitute" | warm beige/taupe — the opposite bias |
| Dark mode | full token set specified | **does not exist** |
| Separation | "1px hairlines, **never shadows**" | `shadowOffset` on cards and bars |
| Mono face | SF Mono / SFMono-Regular | `Menlo` |
| Radii | cards 10, buttons 9, chips 5–6, tiles 7 | eleven different radii (see §4) |

The dark mode point deserves emphasis on its own. The requirement is **dark by default, light as the alternate**. `theme.ts:18-29` exports a single flat `colors` object with no mode dimension at all. There is no dark theme to refine. Dark mode is not a tuning exercise here, it is net-new architecture, and the token layer has to be restructured to support two modes before any dark palette can be applied.

Practical consequence: `design-system.md` cannot be treated as the source of truth for the redesign. It describes a cool-grey, green-accented, dual-mode instrument panel. The app is a warm-cream, slate-accented, light-only one. One of them has to be retired deliberately.

---

## 3. There is no type scale — there is a scaled mockup

`theme.ts:11-16`:

```ts
const MOCKUP_WIDTH = 272;
const DEVICE_WIDTH = 375;
export const SCALE = DEVICE_WIDTH / MOCKUP_WIDTH; // 1.379
export const s = (mockupPx: number) => Math.round(mockupPx * SCALE * 10) / 10;
```

The intent is defensible and the comment argues it well: scale the mockup so proportions hold rather than re-guessing at device size. The result is not.

**Every size in the app is an arbitrary mockup measurement multiplied by 1.379.** Resolving the type roles in `theme.ts:43-98` gives the actual rendered sizes:

| Role | Source | Renders at |
|---|---|---|
| `tabLabel` | `s(7.5)` | 10.3pt |
| `tag` / `chipLabel` | `s(8)` | 11.0pt |
| `headerDate`, `divider`, `ago` | `s(8.5)` | 11.7pt |
| `cardMeta` | `s(9)` | 12.4pt |
| `rowSub`, `groupCount`, `small` | `s(10)` | 13.8pt |
| `why`, `button` | `s(10.5)` | 14.5pt |
| `cardTitle`, `groupLabel`, `body` | `s(11.5)` | 15.9pt |
| `headerTitle`, `rowTitle` | `s(12)` | 16.5pt |
| `cardHeading`, `h2` | `s(13)` | 17.9pt |
| `chipNumber` | `s(15)` | 20.7pt |

Ten steps between 10.3pt and 20.7pt. The gaps between adjacent steps are 0.7, 0.7, 0.7, 1.4, 0.7, 1.4, 0.6, 1.4, 2.8 points.

Two failures follow directly:

**Steps below ~1pt apart are not hierarchy, they are noise.** 15.9 vs 16.5 vs 17.9 are not read as three different levels of importance. They are read as one level rendered sloppily — which is exactly the "nobody put effort in" reaction. A reader cannot perceive a 0.6pt difference as intent; they perceive it as inconsistency.

**Nothing lands on a whole point.** 10.3, 11.7, 12.4, 14.5, 15.9, 16.5, 20.7. Sub-pixel text rendering at fractional sizes softens stem weights unevenly, which is a real (if subtle) contributor to text looking slightly mushy rather than crisp.

**Weight does no work.** Across the whole of `theme.ts` only two weights appear: `'600'` and the implicit regular. There is no light, no medium, no bold. Hierarchy is therefore being asked to come almost entirely from ten barely-distinguishable sizes, while the strongest available lever is untouched.

**The mono face is `Menlo`** (`theme.ts:41`), hardcoded, and it is doing a lot of visible work: every timestamp, count, label, tag, and section divider is set in it. Menlo is a terminal face from 2009. Whether mono is right here at all is a design question for step 2, but Menlo specifically reads as a developer default rather than a chosen typeface.

---

## 4. Proportion: the spacing and radius systems do not exist

`theme.ts:100-115` declares a spacing scale (`xs` through `xxl`) and a radius scale (`sm`, `md`, `lg`, `pill`). **The components almost entirely bypass both** and call `s()` with raw numbers instead.

Grepping the component layer for literal spacing and radius values returns calls to `s()` with these arguments:

> 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 24, 26

That is nearly every integer from 2 to 16. **There is no spacing scale — there is freehand.** After the 1.379 multiplier these become 2.8, 3.4, 4.1, 5.5, 6.9, 8.3, 9.7, 11.0, 12.4, 13.8, 15.2, 16.5, 17.9, 19.3, 20.7, 22.1, 27.6, 33.1, 35.9.

This is the precise mechanism behind the intuition that "we have the components but we don't have the proportionality". Alignment relationships that a viewer reads as *deliberate* — this gap is exactly twice that one, this padding matches that margin — cannot occur by accident across 19 unrelated values. The eye does not consciously measure, but it reliably detects the absence of repetition.

**Radii are worse, because radius is highly visible.** Distinct corner radii currently in use:

| Where | Radius | Renders at |
|---|---|---|
| `FeedCard` dot | `s(2.5)` | 3.4 |
| `DetailSheet` grabber | `s(2)` | 2.8 |
| `FeedCard` active dot | `s(3)` | 4.1 |
| `FeedCard` tag | `s(4)` | 5.5 |
| `Chrome` tab pill | `s(5)` | 6.9 |
| buttons (several) | `s(9)` | 12.4 |
| `DetailSheet` inner block | `s(11)` | 15.2 |
| `ListRow` card | `s(12)` | 16.5 |
| `states` card | `s(14)` | 19.3 |
| `FeedCard` | `s(15)` | 20.7 |
| pills | `999` | full |

**Eleven radii.** A premium system typically runs three or four plus a pill. Worse, the values are close enough to conflict: 15.2 / 16.5 / 19.3 / 20.7 all read as "roughly the same rounded corner", so they do not communicate a difference in elevation or importance — they just fail to match.

**Concentric radii are unmanaged.** A `FeedCard` at radius 20.7 with padding 16.5 contains a tag at radius 5.5. For nested corners to look intentional the inner radius should relate to the outer minus the padding; here the relationship is arbitrary, which is one of the most reliable tells of unrefined work.

**Chips have three different shapes across the app** — the specific complaint about "the aspect ratio of the chips, tags etc":

| Chip | Padding H / V | Radius | Font |
|---|---|---|---|
| `FeedCard` tag (`FeedCard.tsx:200-204`) | 6.9 / 2.8 | 5.5 | 11.0 mono |
| `DetailSheet` header chip (`DetailSheet.tsx:193-195`) | 11.0 / 4.1 | pill | — |
| `DetailSheet` overflow chip (`DetailSheet.tsx:274-276`) | 13.8 / 6.9 | pill | — |

Three chips, three paddings, two radius philosophies (small-rect vs. pill). The `FeedCard` tag computes to roughly 19pt tall — small, tight, and set in uppercase mono at 11pt, which leaves almost no optical breathing room inside the box. Meanwhile `design-system.md` says chips should be 5–6px radius and "not everything is pill-shaped", and half the chips are pills.

**Shadows are used despite being banned.** `FeedCard.tsx:194` and `Chrome.tsx:158` set `shadowOffset`, while the locked spec says separation is "1px hairlines, never shadows". Drop shadows on cards is one of the most commonly cited dated-looking patterns, and it also means the design has no working answer for dark mode, where shadows are close to invisible.

---

## 5. Iconography

Visible in the rendered mockup ([`docs/mockups/home.html`](../mockups/home.html)): **the bottom tab bar icons are empty squares and outlined circles.** They are placeholders that were never replaced. Four navigation items, four geometric primitives, no semantic content.

This is very likely the highest-leverage single fix in the entire app. The tab bar is persistent, it sits at the bottom of every screen, and its icons are the most-seen graphic elements in the product. Placeholder icons in a permanently-visible chrome element signal "unfinished" more loudly than any type or colour issue.

Elsewhere, source identity is carried by **two-letter monogram tiles** (`SL`, `GH`, `GD`, `LN`, `CA`) on low-chroma tinted backgrounds (`theme.ts:32-39`), e.g. Slack as `#E4DCCB` background with `#7A5A2E` text. Two problems: washed-out pastel tints on a cream field produce very low contrast and a muddy, faded look; and text-in-a-box is a fallback pattern, not an icon system. Real product marks would be both more legible and more credible.

`BrandMark.tsx:158` also hardcodes `fontSize: 10` — a raw value that ignores the type system entirely, so the monogram does not scale with anything.

---

## 6. Layout: box-in-box, and no focal point

From the rendered Home screen, above the fold, in order: a bordered "Your day" card containing a bordered ruler; a row of **three equally-weighted outlined count tiles** (`3 URGENT` / `3 TODAY` / `1 CAN WAIT`); a bordered feed card containing a chip, a heading, a body block, and two buttons; then a section label and a list of bordered rows.

Two structural issues:

**Everything is a box, and the boxes nest.** Card inside card inside screen. Each border is another line competing for attention. Premium data-dense interfaces typically use *one* level of containment and separate everything else with space and hairlines. Boxes are expensive; here they are spent freely.

**Nothing dominates.** The three count tiles are the clearest example: identical size, identical border, identical treatment, differing only in a small colour cue on the first. Three equal elements cannot establish a hierarchy — the eye has no entry point, so it scans instead of landing. The screen's actual job is to answer "what needs me now", and the design gives that answer the same visual weight as "what can wait".

This is also where the requested gamified layer has no home. There is currently no progress, streak, or completion device in the UI at all, so it will need to be designed in — and it has to arrive without adding a fourth competing box.

---

## 7. Diagnosis, ranked by impact on perceived quality

1. **Placeholder tab-bar icons.** Persistent, universally visible, unmistakably unfinished.
2. **No type scale.** Ten steps, several under 1pt apart, all on fractional sizes, only two weights. Hierarchy is unreadable, so nothing looks intentional.
3. **No spacing or radius system.** ~19 ad-hoc spacing values and 11 radii, applied freehand, with unmanaged concentric corners. This is the direct cause of the "proportions are off" feeling.
4. **Spec/implementation divergence, and no dark mode.** The locked design system describes a different product than the one that ships, and the requested default mode does not exist in the token layer.
5. **Inconsistent chips.** Three shapes, three paddings, two radius philosophies.
6. **Muddy low-chroma palette.** Cream + taupe + slate with washed pastel tiles; monogram fallbacks instead of an icon system.
7. **Box-in-box layout with no focal point.** Three equal-weight tiles where one answer should dominate.

**The unifying cause:** the project has components but no *system*. Sizes, spaces, and radii were each chosen locally, at the moment each component was written, by scaling a drawing. Perceived quality comes almost entirely from the repetition and restraint that a system enforces — a small set of sizes, a small set of spaces, a small set of radii, used consistently. That constraint layer has never existed here, which is why the last five commits are all corrections and why the result reads as effortless despite real effort having gone in.

The encouraging read: nothing here is an architectural problem. The information design, the layout logic, and the component inventory are sound. What is missing is a constraint layer, and that is a bounded piece of work.

---

## 8. What this audit does not decide

Deliberately left open, because the research is meant to inform them rather than the reverse:

- Which palette direction to take, and the specific dark and light values.
- Whether the mono-for-data signature survives, and which typefaces replace SF/Menlo.
- The type scale ratio and the number of steps.
- The icon set.
- How the gamified layer is expressed without breaking restraint.

These are answered in step 2, after the shortlist is approved.
