# Redesign spec

**Date:** 2026-07-24
**Depends on:** [`design-system-v2.md`](design-system-v2.md). Every token named here is defined there.
**Status:** awaiting decisions on the marked options. Nothing is coded yet.

Options are marked **⬦ DECIDE**. Each has a recommendation and the reason for it. Everything unmarked is settled by the rules.

---

## 0. Information architecture

Five tabs, which is exactly at the iOS cap of five and therefore needs no "More" fallback.

| Tab | Was | Job |
|---|---|---|
| **Your Day** | Home | The shape of today and what is pressing. One screen, no feed |
| **Feed** | *(new)* | Full-screen cards you swipe through and act on |
| **Later** | Later | What arrived and did not need you |
| **Activity** | Sources | Per-source numbers and what has been happening |
| **You** | You | Settings, notifications, connections |

**Sources → Activity ⬦ DECIDE.** The tab no longer offers connection management, so "Sources" names a thing it no longer does. It shows what each connected tool has been doing.

| Option | Reads as |
|---|---|
| **Activity (recommended)** | Plainly what it is: what has been happening in each tool. Matches that the listings open the tool itself |
| Signals | Fits the product's language, slightly abstract |
| Pulse | Most premium-sounding, least specific about content |

### Tab bar

Hand-built via the `tabBar` prop on `@react-navigation/bottom-tabs`. Not `NativeTabs`.

- **49pt bar + 34pt home-indicator inset = 83pt total.** Icons 25×25. Labels 11pt `label` role.
- Phosphor icons: `Sun` / `Cards` / `Clock` / `PulseIcon` / `User`, **`regular` unselected, `fill` selected**.
- Selected item: icon and label at `textHigh`, plus a **2pt accent bar at the top edge of the item**, 24pt wide. Colour is not the only signal.
- Content **flows underneath** with `expo-blur`, not blocked by an opaque slab. This is the one place platform glass is allowed.
- A count badge appears on **Feed only**, and only when urgent > 0. Filled dot with the number, alarm coloured.

---

## 1. The top bar ⬦ DECIDE

The current header is a centred 14pt title with a date beneath, on a hairline-bordered bar, on every screen. It carries almost no information and takes a fixed band on all five tabs.

### Option A: Dissolving header *(recommended)*

No bar at rest. The screen title is the first line of **content**, set in `display` (34pt Archivo 600), with a `label` eyebrow above it carrying the date. On scroll past 60pt it collapses into a 44pt bar holding the title at `heading` (17pt) plus the pressure gauge from Option B, over blur.

This is Apple's large-title behaviour and it does two things at once: it gives the maximum content area at rest, and it is where the **Instrument Serif greeting** lives on Your Day. A title that survives collapsing from 34pt to 17pt through weight alone is exactly the iOS hierarchy move.

### Option B: Instrument strip

A permanent 44pt bar: date in `label` caps left, a **live pressure gauge** centred, avatar right. The gauge is a 3-segment horizontal bar, 64×4pt, showing the urgent / by-you / can-wait proportion in alarm / accent / `border`. Always visible, always information.

Denser and more instrument-like. Costs 44pt on every screen and puts a permanent horizontal rule near the top of the app.

### Option C: Floating pill

Content bleeds to the top edge. A blurred pill floats over it holding the title and one action, detached from all edges. iOS 26 Liquid Glass register.

Most current-looking, least informative, and the pill occludes content it floats over.

**Recommendation: A, with B's pressure gauge as the collapsed state.** It gets the large-title moment, the serif greeting, and the gauge, without spending a permanent band. The current centred header is not among the options because a centred title is a web pattern; iOS titles are leading-aligned.

---

## 2. Your Day

The whole screen, no card feed. Removing the horizontal slider is the point: it moves to the Feed tab.

```
┌─────────────────────────────────┐
│  THU 24 JUL                     │  label, textLow
│  Good morning, Vicky            │  Instrument Serif 34: the one serif line
│                                 │
│         ╭───────────╮           │
│        ╱             ╲          │  THE DAY ARC: the hero object
│       │      7        │         │  SVG, gradient stroke alarm→accent
│       │   need you    │         │  hero 56 numeral, tabular
│        ╲             ╱          │  arc swept by proportion of day elapsed
│         ╰───────────╯           │  segment ticks mark meetings
│                                 │
│  ▌ 3 URGENT   ▌ 3 BY YOU   1 CAN WAIT │  the tier bar
│                                 │
│  ───────────────────────────    │  hairline
│  NEXT                           │  label
│  10:30  Design review    45m    │  mono time · body title · mono dur
│  14:00  1:1 with Sam     30m    │
│                                 │
│  ───────────────────────────    │
│  2h 15m free before 10:30       │  secondary, textMid
└─────────────────────────────────┘
```

**The day arc** is the one material object. An SVG ring, 180pt, 8pt stroke, gradient from alarm at the start to accent at the end, with the unfilled remainder at `hairline`. Meeting blocks are ticks on the ring. The centre holds the count in `hero` and a `label` beneath. Grain overlays the whole thing.

This is also **where the gamified layer lives**, and it needs no new colour: as items clear, the ring fills toward accent. Clearing the last urgent item is the single Lottie moment in the app, with `notificationAsync(Success)`.

**The tier bar** replaces the three equal outlined tiles. Those tiles are the audit's "nothing dominates" finding: three identical elements cannot establish a hierarchy, so the eye scans instead of landing, and the screen's actual job is to answer *what needs me now*.

The replacement is one horizontal row, not three boxes. Each tier is a **leading 3pt vertical bar + count + `label`**, and they are **weighted, not equal**: urgent gets `title` (22pt) for its count, by-you `heading` (17pt), can-wait `body` (15pt). Tapping one deep-links into the Feed filtered to that tier. Selection is an **outline**, never a filled dot.

**No boxes on this screen.** Sections are separated by hairlines and 32pt of space. The audit's box-in-box finding is fixed by simply not having containers: one hero object, then flat rows.

---

## 3. Feed

Full-screen cards, horizontally swiped, one card per screen. Instagram-like in navigation, not in content.

### Structure

Cards are ordered **Urgent → By you → Can wait → Later**, and group boundaries are marked by a full-screen **divider card**: a `display` group name, the count, and one `secondary` line ("3 things are blocking someone"). A divider is cheap, makes the grouping legible while swiping, and gives a natural rest point.

- **Vertical position** within a group is the ranked order; **horizontal swipe** moves through everything.
- A **progress rail** sits at the top edge under the safe area: one segment per card in the current group, filled up to the current index. Instagram's story rail, and it answers "how many left" without a count.
- **Later cards appear as the final group**, styled quietest of all, and remain tappable.

### Gestures

| Gesture | Result |
|---|---|
| Swipe left / right | Next / previous card, finger-tracked, reversible mid-flight |
| Swipe **up** | Primary action for the card type, with `impactAsync(Light)` at the threshold |
| Swipe **down** | Snooze to Later |
| Tap the body | Detail sheet, at `medium` detent with a grabber |
| Long-press | Full action menu |

**No gesture is the only path.** The two visible action buttons stay at the bottom of every card, thumb-anchored. The gestures are an accelerator for people who learn them.

### Card anatomy

```
┌─────────────────────────────────┐
│ ▓▓▓▓░░░░░░░░                    │  progress rail
│                                 │
│  ◤ source tint radial wash, 8%  │
│  ┌──┐                           │
│  │GH│  github · acme/api        │  brand mark 40pt + secondary
│  └──┘                           │
│                                 │
│  ▌ URGENT                       │  tier signal + solid tag
│                                 │
│  Fix the auth race in           │  title 22: up to 4 lines
│  the session refresh            │
│                                 │
│  Sam asked for changes 2h ago   │  body, textMid: the AI summary
│  and the deploy is blocked.     │
│                                 │
│  ─────────────────────────      │  hairline
│  BLOCKING · 2H AGO · #4821      │  label + mono
│                                 │
│         (96pt of space)         │  ← the empty space that makes it land
│                                 │
│  ┌───────────┐ ┌───────────┐    │
│  │  Approve  │ │  Comment  │    │  bottom-anchored, 48pt
│  └───────────┘ └───────────┘    │
└─────────────────────────────────┘
```

Everything above the rule is content; everything below is machine metadata in mono. The 96pt gap is deliberate and is the one place the spacing scale's top value is spent.

### Per-source variation

The chrome is identical. What changes is the **middle block** and the **actions**, taken from the existing matrix in [`mobile/src/lib/actions.ts`](../mobile/src/lib/actions.ts). Every action currently reachable stays reachable.

| Source | Middle block | Primary / secondary |
|---|---|---|
| **GitHub** | Repo · PR number · changed-files count. If `type_tag` is review: a 3-line diff stat in mono | Approve / Comment, or Comment / Snooze |
| **Slack** | Channel name with a `#`, sender avatar + handle, the message quoted in `body` with a leading accent rule | Reply / Mark read |
| **Gmail** | Sender name in `heading`, address in `secondary` mono, subject in `title`, first 3 lines of body | Open / Snooze |
| **Linear** | Issue ID in mono, current state as an outline chip, assignee, priority as a 4-bar glyph | Comment / Open |
| **Calendar** | Time in `hero` (the only other place it appears), duration, attendee count, conference badge | Accept / Open |
| **Google Docs** | Doc title in `title`, the comment thread quoted, commenter | Reply / Open |

### Tier variants ⬦ DECIDE

All three options change **form**, not only colour, because colour alone cannot carry state and must survive greyscale. Each is specified at both scales it has to work at: the full-screen Feed card, and the compact row on Your Day and Later.

#### Option 1: Edge light *(recommended)*

A luminous vertical bar on the leading edge.

| Tier | Card | Row |
|---|---|---|
| **Urgent** | 4pt alarm bar, full card height, **with a 40pt-wide alarm glow bleeding right at 10%**. Solid alarm tag | 3pt alarm bar, no glow |
| **By you** | 4pt accent bar, no glow. Outline accent tag | 3pt accent bar |
| **Can wait** | 1pt `hairline` bar. Ghost tag | No bar, hairline separator only |
| **Later** | No bar. Card at `canvas`, not `surface`. Ghost tag | Dimmed to `textLow` |

Form varies along two axes at once: **bar thickness** and **presence of glow**: so the three tiers stay distinct in greyscale. Degrades to rows cleanly by dropping the glow.

#### Option 2: Containment level

Tier is expressed by how contained the card is.

| Tier | Card |
|---|---|
| **Urgent** | `surfaceRaised` fill + alarm radial wash from the top-left + solid alarm tag, full-bleed across the card top |
| **By you** | `surface` fill, hairline border, outline accent tag |
| **Can wait** | No fill at all. Hairline rules top and bottom only |
| **Later** | No fill, no rules. Text only |

Conceptually the cleanest: importance *is* how much substance the thing has. Weakest at row scale, because a compact row has little containment to remove.

#### Option 3: Instrument frame

Corner brackets, like a camera focus reticle.

| Tier | Card |
|---|---|
| **Urgent** | Four 20pt alarm corner brackets, 2pt, with `URGENT` in Archivo Condensed set into a gap in the top bracket |
| **By you** | Top bracket only, accent, label sitting on it |
| **Can wait** | Label alone, no frame |

The most distinctive and the most on-brand for an instrument (Halide's register). Highest risk: brackets are a strong idiom that either lands or looks like a viewfinder gimmick, and they fight the card's own corner radius.

**Recommendation: Option 1.** It is the only one that survives the drop to row scale without redesign, and the glow is a real use of the material layer that costs one `expo-linear-gradient`. Option 3 is the most interesting and is worth prototyping on one card before it is ruled out.

---

## 4. Later

Keeps its job: what arrived and did not need you. Restyled, not redesigned.

- Grouped by **why it is here**: `Snoozed` / `No date set` / `Handled`: with `label` group headers on hairlines, no boxes.
- Rows at 72pt two-line: brand mark 20pt, title `body` one line, source and age in mono `secondary`.
- **Swipe right to promote back into the Feed**, swipe left to dismiss. `allowsFullSwipe` past the threshold, which is one of the cheapest premium signals available.
- Snoozed rows carry a mono countdown right-aligned ("in 4h"), tabular.
- The whole tab is one hue at most: neutral, with accent only on the promote action.

---

## 5. Activity *(was Sources)*

No Connect button anywhere on this tab. Connection lives in You.

Only connected sources appear. The current screen shows all six regardless, which was right when this tab owned connection and is wrong now.

### Tab root

Per source, one **card**, not a row: this is the one screen where cards earn their containment, because each is a self-contained summary of a different system:

```
┌─────────────────────────────────┐
│  ┌──┐                           │
│  │GH│  GitHub          ● live   │  mark 32 + heading + status
│  └──┘                           │
│                                 │
│   47          12         3      │  hero-ish: title 22, tabular
│   EVENTS      OPEN       YOURS  │  label, textLow
│                                 │
│  ▁▂▃▅▂▇▃▁▂▃▅▆                   │  30-day sparkline, accent, 24pt
└─────────────────────────────────┘
```

Radius `lg`, `surface` fill, source tint wash at 6% behind the mark, grain over it. Tapping opens the source detail.

**Status is a dot plus a word.** An outline dot when never connected, filled accent when live, filled alarm when expired. The word is required: the dot alone repeats the filled-dot-means-badge mistake.

### Source detail

The current screen is stat cards on top and a listing below, and it reads primitive because the numbers are the same size as everything else and the listing is a stack of bordered boxes.

**Numbers: Alpian's structure, which is the reference for exactly this:**

1. **One hero numeral**, `hero` 56, tabular, with a `label` beneath. This is the single number that matters for the source: open PRs, unread threads, upcoming events. Everything else is subordinate to it. This is the focal point the current screen lacks.
2. Beneath it, a **row of circular action glyphs**, 44pt, accent-stroked, `surfaceOverlay` fill: refresh, filter, open-in-app.
3. Then a **2-column grid of stat tiles** from `headline: StatLine[]`. Each tile: `label` caps, `title` 22 value tabular, `secondary` detail. Radius `md`, `surface`, 12 gap. Two columns, because the existing two-column fix was made for a real reason: labels wrapping their last letter.
4. `unavailable` fields are rendered as a single `secondary` line: *"Not available from this source: reactions, thread depth."* **Never a tile with a dash in it**: that fakes an empty state as a full one.

**Listings: Vyzer's shape**, which the research identified as the closest structural match to this product anywhere:

Dense hairline-separated rows, no boxes, 72pt two-line:

```
  ┌──┐  Fix auth race in session refresh      →
  │GH│  acme/api · opened 2d ago    ⟨OVERDUE⟩
  └──┘
  ─────────────────────────────────────────────
```

- Leading 20pt mark, title `body` truncated to one line, meta line in mono `secondary`.
- **Status as an outline chip**, right-aligned on the meta line.
- Trailing **external-link glyph**, not a chevron. These open the tool itself, and a chevron promises in-app navigation that does not happen. The distinction is the whole reason the affordance needs to differ.
- Numbers right-aligned in a tabular mono column so they form a real column.

---

## 6. You

Receives the connection flow. The notification block collapses.

```
  VICKY PANDEY                       label
  vicky@agentiwise.com               secondary

  ─────────────────────────────────
  NOTIFICATIONS                      label

  Notify me                  [ ●]    heading + Switch
  Urgent only · 3 sent today         secondary, textMid

    ┌─────────┬──────────┬────────┐  ← only when on
    │ Urgent  │ + Today  │  All   │  segmented, pill
    └─────────┴──────────┴────────┘

  ─────────────────────────────────
  AI SUMMARIES                       label

  Summarise and rank            [ ●]
  Message text goes to OpenRouter.
  Off means rules only, which is
  blunter but never leaves us.

  ─────────────────────────────────
  CONNECTIONS                    ②   label + alarm bubble

  ┌──┐ GitHub        live      [ ●]
  │GH│                              ← AI toggle per source
  └──┘
  ┌──┐ Slack     expired      Fix
  │SL│
  └──┘
  + Connect a source

  ─────────────────────────────────
  Sign out
```

**The notification block** is currently three full-width bordered option cards, each with a title, a detail line and a tick: a stack of boxes that reads like a web settings document. It becomes **one row with one toggle plus a subtext line**, and the level segmented control appears beneath only when the toggle is on. Three states become one control plus a progressive disclosure, and the block drops from roughly 200pt to about 60.

**The connections bubble** is a filled alarm circle with a count, and it counts only things that need action: expired and error, never "not connected yet". A permanent badge for optional integrations is a badge that gets ignored.

**Connect** is a row at the end of the list, not a button in a header. `+ Connect a source` opens a sheet listing unconnected sources. The footnote about the provider's own sign-in moves into that sheet, where it is relevant, rather than sitting at the bottom of a tab.

**AI summaries** keeps the disclosure verbatim in its current position and tone. Sending message text to a third party is the core privacy fact of this product and it belongs next to the switch that turns it off, not behind a policy link.

---

## 7. Build order

Tracer bullet: prove the token layer end-to-end on the smallest visible slice before rebuilding anything.

1. **Token layer + fonts.** `theme/` per §11 of the rules, both modes, Geist and Archivo embedded via the config plugin. Verify on a real iOS build that every weight actually loaded, because a font-name mismatch fails silently on iOS.
2. **Tab bar.** Phosphor icons, fill-on-select, blur, accent bar. This is the highest-leverage single fix and it validates the tokens on the most-seen surface in the product.
3. **One Feed card**, urgent, GitHub, with tier Option 1 and the source glow. Prove the material layer at real size on a real device.
4. **Your Day**, including the day arc.
5. The rest of the Feed, then Later, Activity, You.
6. Motion and haptics last, as a pass over finished screens.

**Stop after 3 and look at it.** Written descriptions have not matched what you saw twice in this project, and step 3 is the first point where there is something real to judge.

---

## 8. Open questions

**1. What "By you" actually means.** The Feed groups are Urgent / By you / Can wait, but the API tier is `today`, which is deadline-based. "By you" is ownership-based. These are different things and the code cannot tell me which is intended:

- **(a)** It is a relabel. `today` renders as "By you", and the group really means *due today*.
- **(b)** It is a new grouping derived from `type_tag ∈ {assigned, review, approve}`, which is a backend change and would cut across tiers.

I have specced **(a)** throughout because it needs no backend work and matches the existing wire contract. If (b) is what you meant, the Feed grouping and the tier bar both change shape.

**2. `noise` and Later.** `tierLabel.noise` is currently "No date set" and the other session recently changed Later to show everything that arrived and did not need you. Later's groups in §4 assume that shape holds. Worth confirming that session is done with it before Later is touched.

**3. The dark-mode migration of the source roundels.** `theme.ts` has six hardcoded pastel tint pairs that only work on cream. They are replaced by real brand marks plus the source tints in §1 of the rules, so `roundel` is deleted rather than ported. Flagging it because `BrandMark.tsx` also hardcodes `fontSize: 10` and will need rewriting rather than restyling.
