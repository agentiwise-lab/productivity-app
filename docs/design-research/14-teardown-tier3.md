# Teardown: Dark Noise, Timepage, Streaks, and the anti-reference

**Date:** 2026-07-24
**Part of:** step 2 teardowns. Tier 3 of the [mobile shortlist](07b-shortlist-mobile.md).

**Evidence tags used throughout:** `[published]` a real value or quote from a primary source · `[observed]` described from a screenshot or video actually viewed · `[inferred]` reasoning, not evidence.

**Verification note.** Every substantive claim below was checked before it was written down. Three were corrected, two could not be confirmed and are marked as such, and one App Store figure was verified independently against the live listing. Details in the audit at the end.

---

## 1. Dark Noise: does the animation carry state, or decorate it?

**It carries state, and the reason is specific.** Chapman built animated icons because **the app can be playing while silent** (muted speaker, low volume), so the user needs "an indication that sound *should* be coming out" independently of hearing it `[published]` ([Designing Dark Noise](https://charliemchapman.com/posts/2019/9/2/designing-dark-noise/)).

That is the whole lesson. The animation is not personality applied to an icon. It is the answer to a state-communication problem that a badge would answer worse.

**The icon system**
- **38 sounds**, each with a custom icon, grouped into noise colours, Water, Appliances, Nature, Fire, Urban, Human `[published]` ([MacStories](https://www.macstories.net/reviews/dark-noise-review-ambient-noise-never-looked-so-good/)).
- Pipeline: designed in **Adobe Illustrator**, animated in **After Effects**, shipped via **Lottie** `[published]` ([Indie Dev Monday](https://indiedevmonday.com/issue-36)). **Directly reusable: `lottie-react-native` is mature.**
- Screens were designed **outside code**, in XD then Figma: "I like doing this outside of code because I think it frees you from the constraints of how hard it'll be to implement" `[published]`.
- Who drew the 38 icons is **NOT FOUND** as an explicit credit. Both sources attribute design and animation to Chapman; neither says it outright. `[inferred]`

**Architecture**
- On iPhone **the player is the root screen** and the sound browser is hidden below it. The rationale is to optimise for the dominant case: start a sound fast `[published]`.
- **The affordance move worth stealing:** the unconventional gesture got an **animated down arrow with a "breathing" animation, a "gentle bounce and opacity change"**, borrowed from MacBook Pro design language `[published]`. **A persistent, near-zero-cost animated hint instead of a first-run coach-mark overlay.**
- iPad merges list and playback into one interface rather than porting the modal `[published]`.

**"Keep it dark"** is a context constraint, not a palette preference: "Most users will probably be using this in a dark environment, possibly without their glasses on or half asleep." It drove **button sizing and legibility**, not just colour `[published]`.

**iOS 17 widgets** were "rebuilt from the ground up": **8 widget options across 12 themes**, with small widgets optimised for **StandBy** as a bedside case `[published]` ([Dark Noise 3.2](https://charliemchapman.com/posts/2023/9/18/dark-noise-3_2-iOS-17)). Note the pattern: the widget was re-architected around a **new physical context** (a phone charging sideways at night), not recompiled.

**Theming:** 8 colour themes, 20+ alternate app icons, with icons designed to hold up across every theme `[published]`.

**Typography and colour values: NOT FOUND.** No source publishes them. Not invented here.

---

## 2. Timepage: encoding density without numbers

**The Heat Map** is the cleanest published example of density-as-saturation: "days on the calendar have deeper colors when more events are planned for them", reflecting both event frequency and duration, with **no count rendered** `[published]` ([MacStories](https://www.macstories.net/reviews/timepage-a-beautiful-and-clever-calendar-app/)). You can slide through calendars to re-render the heat map per calendar `[published]`.

**Day view row anatomy** `[published]`: title, with **time and duration below it**; weather symbol and temperature pinned at the bottom of the day. Version 3.0 turned rows into **colour-assigned cards**, colour inherited from the calendar, user-overridable, or **disableable entirely**. Tapping expands to a map of the location, attendees, reminders, notes and transport options.

**Weather is progressive disclosure, not a column.** Tap-and-hold a day in week view gives highs, lows and precipitation chance. The same gesture in day view gives a graph you can **scrub along the timeline** to preview a specific hour `[published]`.

**Verified gesture inventory** `[published]`: tap day to open day view · tap-and-hold day for weather · drag on the weather graph to scrub time · tap event to expand · **pull-down to create** · **swipe on the time or day field to move an event forward or back** · landscape rotation on iPhone for Month View.

**Theming:** **60 hand-made themes**, a single accent applied app-wide including the icon `[published]` ([Bonobo](https://bonobolabs.com/timepage/)). The earlier MacStories review said "over fifteen", so the count grew; both are correct at their date.

### Two corrections to what I previously wrote

**Timepage does have a floating add button.** Version 3.0 added "a floating add button that can be picked up and dropped on a specific day to create a new event on that day" `[published]` ([Timepage 3.0](https://www.macstories.net/reviews/timepage-30-key-refinements-for-a-mature-calendar-app/)). My earlier "pull-down as the single creation gesture, no FAB" is **accurate only for the early version.**

And the corrected version is the more interesting idea: **the FAB carries a payload.** Dragging it onto a day collapses a two-step interaction (choose action, then choose target) into one gesture. That is the same insight as Things 3's Magic Plus button, arrived at independently.

**"Horizontal paging between whole view-modes" is NOT VERIFIED.** The only concrete spatial statements published are that Year View "lives to the left of the Heat Map", and that on iPad the full calendar "lives a swipe to the left of the smaller calendar picker". That is *consistent* with horizontal paging, but no source describes it as a navigation model replacing a tab bar. Downgraded to `[inferred]`.

**Actions (same studio):** Bonobo ships Timepage, Actions, Flow and Overlap as a bundle with data flowing between them `[published]`. **Whether they share a design system in any concrete way is NOT FOUND.** Shared identity is `[inferred]` from shared studio and marketing language only.

---

## 3. Streaks: constraint as design

**The task-cap disagreement is resolved. All three numbers are correct at different times** `[published]`:

| Version | Cap | How capacity was added |
|---|---|---|
| v1 to v2 | **6** | "up to six circles with icons in the center" |
| v3 (2017) | **12** | "turning Streaks' single view into a card and putting the additional goals on the back" |
| Current | **24** | verified below |

**Independently verified:** the live App Store listing for Streaks **version 11.3.6** states "Track up to 24 tasks you want to complete each day", and carries "Apple Design Award winner" in the developer's own copy.

**This is the most useful finding in tier 3.** Capacity was added **on a new axis** (a second card face) rather than by shrinking tiles or introducing scroll. The one-screen, thumb-target invariant was treated as non-negotiable and the card flip was the pressure valve. Each side gets its own colour theme, so **the flip doubles as categorisation** (fitness side, work side).

**Tile anatomy:** a circle with a centred glyph, and **completion is a long-press, not a tap** `[published]`, deliberate friction against accidental completion on a large target.

**Watch:** complications mirror the card's completion indicators so you can see what is done without opening anything. 45 alternate app icons `[published]`.

**Honest dating assessment** `[inferred]`. The 2016 award was judged against iOS 9 and 10 visual language. Bold-accent-on-black with flat circular tiles has aged **better than most 2016 work**, because it was near-typographic rather than skeuomorphic or gradient-heavy. What has dated: the flat solid-fill circle reads as pre-iOS-26 to a current eye, there is no depth or material vocabulary, and the card-flip is a skeuomorphic metaphor a modern system would express as a segmented paging control.

**The structural idea transfers completely. The surface treatment does not. Do not copy the visual language.**

---

## 4. The anti-reference, and a sourcing reconciliation

**The tier-3 agent could not reach the Exoplan thread.** `old.reddit.com`, `www.reddit.com` and the `.json` endpoint are all blocked to WebFetch, and the in-app browser blocks the domain by policy. It correctly refused to paraphrase comments it had not read.

**However, that thread was read directly during the earlier mobile-sentiment pass**, through the logged-in Chrome session, and quoted there. So the Exoplan critique recorded in [10-mobile-sentiment.md §2](10-mobile-sentiment.md) **is sourced**, not asserted. It carries a single-pass confidence rather than a double-verified one, and it is marked accordingly below.

---

## The amateur-tell checklist

The consolidated, actionable list. Provenance is stated per row rather than blurred.

| Tell | Evidence |
|---|---|
| **Empty state faked as a full state** (a score rendering 100 for every day with no data connected) | Exoplan thread, single-pass via Chrome. **Highest severity: it destroys trust in every other number in the app.** |
| **Filled dot used for selection** — reads as an unread badge. Use an **outline** for "you are here" and reserve fill for "something happened" | Exoplan thread, single-pass |
| Primary navigation at the **top** rather than the bottom on iOS | Exoplan thread, single-pass |
| Ambiguous or undifferentiated menu icon | Exoplan thread, single-pass |
| Interactive elements below **44x44pt** | Widely corroborated ([72Technologies](https://www.72technologies.com/blog/tap-targets-thumb-zones-mobile-ux), [LogRocket](https://blog.logrocket.com/ux-design/all-accessible-touch-target-sizes/)). **Apple's own HIG page is JS-rendered and could not be fetched in this session**, so this is second-hand, not sourced to Apple directly. It is a very well-established number, but flagged honestly. |
| Body text below ~11pt at typical viewing distance | `[published]` ([72Technologies](https://www.72technologies.com/blog/tap-targets-thumb-zones-mobile-ux)) |
| UI that reads as **ported from another platform** — non-native controls, wrong transitions, Material shadows on iOS | `[published]` ([BrightDigit](https://brightdigit.com/articles/4-mistakes-design-ios-app-ui/)) |
| Unfinished or default loading screen | Exoplan thread, single-pass |

### The rule underneath all of it

**Almost every amateur tell in that critique was a semantic collision:** a shape that already means something in the iOS vocabulary being reused to mean something else (a filled dot means "badge", reused to mean "selected"), or a state rendered in the vocabulary of a different state (empty rendered as full).

**Not one of them was "ugly."** Reviewers called the app tactile and beautiful *and* amateur in the same breath.

> **This is the precise risk for our app.** An empty inbox rendered as a scored, complete inbox. A "read" row indistinguishable from a "dismissed" one. And concretely: **`ListRow.tsx:78` uses a filled `pip` for tier.** A filled dot in a list row is the exact collision named above. Our own [audit](00-current-state-audit.md) also notes the "You're clear for today" screen shows a checkmark and a count, which needs checking against the faked-empty-state failure.

---

## What transfers to a triage feed

1. **Make motion the state indicator, not decoration.** Dark Noise's animated icons exist because the audio channel can be silent. A triage feed has the identical problem: "is this live, syncing, stale, actioned?" is a state that badges express poorly and motion expresses instantly.
2. **Encode volume as intensity, not as a count.** Timepage's heat map. For us: source rows or day groups darken with load, and numerals are reserved for drill-down. **This also converges with the GitHub-style contribution grid already proposed in [05](05-gamification-that-stays-premium.md).**
3. **Progressive disclosure behind long-press, not extra chrome.** Timepage hides a full weather graph behind tap-and-hold; Streaks hides commit behind long-press. Our rows could hide full metadata behind hold and stay two lines.
4. **Cap the surface; add capacity on a new axis.** Streaks went 6 to 12 to 24 without ever sacrificing one-screen or thumb targets. If our "Needs you now" zone has a cap, page or flip for overflow rather than shrinking rows.
5. **Make the primary screen the primary action.** Dark Noise made the player the root, not a destination. If triage is the job, triage is the root and everything else lives behind a gesture.
6. **Every unconventional gesture needs a persistent animated affordance.** The breathing arrow costs almost no space and beats a coach-mark. Directly buildable with a Reanimated loop on an edge hint, and **we need exactly this for our swipe-to-act gesture.**
7. **Give the FAB a payload.** Timepage 3.0's draggable add button, and Things 3's Magic Plus, are the same idea reached independently: **the creation gesture also expresses placement.**
8. **Commit to one accent app-wide, including the app icon.** Both Timepage (60 themes, one active) and Streaks (accent on black) do this.

---

## Confidence audit

**Corrected during verification**
- **Timepage does have a FAB** as of 3.0, and it is draggable with a date payload. My earlier "no FAB" framing was wrong for current versions.
- **Timepage's horizontal view-mode paging is unverified**, downgraded from a stated fact to `[inferred]`.
- **Streaks' task cap is 24**, not 12. Verified against the live App Store listing (v11.3.6).

**Could not verify**
- The Exoplan thread from this agent's toolset. Reconciled above: it was read in the earlier Chrome pass, so it holds at single-pass confidence.
- Dark Noise typography and colour values. Not published anywhere.
- Whether Bonobo's Actions shares Timepage's design system concretely.
- **Apple's own wording on the 44pt minimum.** The HIG is JS-rendered; both an agent and I failed to fetch it. Corroborated by multiple secondary sources but not sourced to Apple in this session.
- Dark Noise's player gesture direction: Chapman describes swipe-down-to-reveal-browser, MacStories describes a pull-up playback screen. Probably the same modal described from opposite states, but unresolved.

**Where the source count is thin**
The general "amateur tells" research returned mostly listicles, including a 2009 Smashing Magazine piece that is too old to lean on. The agent said so rather than padding, which is the right call. **The genuinely load-bearing material here is the Exoplan critique and the semantic-collision rule drawn from it**, not the generic listicles.
