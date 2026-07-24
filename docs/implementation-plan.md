# Implementation plan

**Date:** 2026-07-24
**Specification:** [`mockups/v4-screens.html`](mockups/v4-screens.html). Drawn at 393&times;852 with **1 CSS pixel = 1 iOS point**, so every number in it is the number that ships.
**Rules:** [`design-system-v2.md`](design-system-v2.md), amended by §2 of this document where they disagree.

Three phases. **Phase 0 is a live bug and goes first.** Phase 1 is the UI. Phase 2 is the backend work the redesign surfaced, and it is **in scope**, not deferred.

---

## 0. A live bug, which outranks everything below

`ActionBody.action` defaults to `"comment"` ([`backend/main.py:87`](../backend/main.py)) and the client never sends an action name:

```ts
// mobile/src/api/client.ts
act(itemId: string, body: string) {
  return this.request<FeedRow>(`/feed/${itemId}/actions`, {
    method: 'POST',
    body: JSON.stringify({ body }),   // no `action` field
  });
}
```

**Every action routed through `api.act()` is performed as `comment`.** Tapping **Approve** posts a comment instead of submitting a review, which is exactly the failure `_approve`'s own docstring exists to prevent:

> "Submitting a review, not posting a comment. A comment reading 'approved' leaves the pull request just as blocked as before."

Worse: the card calls `onAction(row, action.id)` with no body, so the request carries `body: ""`, `_send` rejects empty text with `ActionFailed("an empty reply is not a reply")`, and the user sees a 409 and *"That didn't go through"*. **Approve is broken end to end.**

**Read from code, not reproduced against a server.** Write the failing integration test first, then:

```ts
act(itemId: string, action: string, body = '') {
  return this.request<FeedRow>(`/feed/${itemId}/actions`, {
    method: 'POST', body: JSON.stringify({ action, body }),
  });
}
```

and drop the default on `ActionBody.action` so a missing action is a 422 rather than a silent comment.

---

## 1. The fidelity contract

**The mockup is the specification, not an illustration of one.** It is drawn at true device size specifically so that implementation is transcription rather than interpretation.

1. **Every value is transcribed, never re-derived.** Padding, gap, radius, height, font size, line height, tracking, opacity, gradient stop. If a number appears in `v4-screens.html`, that exact number ships. If a number is needed that is not there, the mockup is wrong and gets fixed first.
2. **`SCALE` and `s()` are deleted.** Every size in the app today is a 272pt mockup measurement times 1.379, which is why nothing lands on a whole point. There is no multiplier in v4 and there must be none in the code.
3. **No component invents a colour.** Six hues, two exemptions, and the neutral ladder. §2.
4. **The verification script ships as a test.** The checks that ran against the mockup run against the built app: spacing on the scale, radii on the ramp, type on the seven roles, no non-inset shadow, no content past the fold or under a fixed footer, no control under 28pt, no colour off the palette.
5. **Compare on device, not in a simulator screenshot.** Side by side with the mockup at the same physical size, in both modes.

The only values permitted off the spacing scale are the two OS insets, **54pt** for the status bar and **34pt** for the home indicator.

---

## 2. Tokens

### Colour: six hues, each naming a category

| Token | Dark | Light | Means |
|---|---|---|---|
| `urgent` | `#FF6B5F` | `#CC4432` | Someone is blocked on you |
| `byEod` | `#63E4C2` | `#0D8167` | Due before tonight |
| `canWait` | `#AB7FF8` | `#7144CC` | Neither |
| `later` | `#F2B366` | `#96631F` | Arrived, did not need you |
| `none` | `#7FA6D9` | `#3E6EA8` | A row with no category at all |
| `summary` | `#C9B79A` | `#6E5A40` | A card that totals rather than lists |

**Colour is the category and never the source.** A source is already named by its brand mark beside the text, so a source hue says nothing new and spends the one thing hue is good for.

The last two exist because plenty of rows have no category: a meeting, a repository, a connected account. **Neither ever shares a screen with a tier hue**, so neither can be misread as one.

### Neutral ladder

| Token | Dark | Light (sage teal) |
|---|---|---|
| `canvas` | `#0C0B0A` | `#DCE6E5` |
| `surface` | `#151311` | `#EAF1F0` |
| `raised` | `#1D1A17` | `#F2F7F6` |
| `overlay` | `#26221E` | `#CBDAD9` |
| `hairline` | `#2E2A26` | `#BFD0CF` |
| `border` | `#3B352F` | `#A8BEBD` |
| `faint` | `#57504A` | `#86A09F` |
| `low` | `#888179` | `#566E6D` |
| `mid` | `#A79F97` | `#3E5453` |
| `high` | `#F5F1EC` | `#12201F` |
| `onSolid` | `#0C0B0A` | `#FFFDF9` |

Dark runs warm, R above G above B at every step. Light is the **sage teal from `ad_analytics`**, whose own tokens name it *weathered copper*: `--accent-spend: #6B9B9A`, hue 179 at 19% saturation. That mutedness is the character.

**Contrast, measured, all clearing AA.** Chip text on the six fills: dark 6.7 to 12.6, light 4.7 to 6.5. Body text on `surface`: dark 4.8 to 16.5, light 4.8 to 14.6.

Writing this plan is what caught the last failure: dark `low` was `#7A736C` and measured **4.0:1** on `surface`, under the floor, so it is now `#888179` at 4.8. **Every text and fill pair is measured, not assumed, and both floors sit at 4.8, so re-measure before changing any of them.**

### Two exemptions, and only two

- **Brand marks keep their own colours.** Tried monochrome and rejected. A mark is identity, not category, and never occupies a position where a category signal lives. **Do not desaturate source icons anywhere**: not in the Feed, Later, Activity, You, or a sheet.
- **Data visualisation may use `byEod`.** Activity sparklines were neutral by the letter of the rule and looked dead.

### Rejected, recorded so it is not retried

- **Colouring untiered rows by source.** Later filters to one source at a time, so every row came out identical and nothing was differentiated.
- **Grouping Later by day.** Structure papering over a colour problem, and it put a header between every two rows.
- **Monochrome brand marks.** Lost identity for a rule that marks were never breaking.

### Type: seven roles

| Role | Size / line / tracking | Weight | Face |
|---|---|---|---|
| `hero` | 56 / 56 / &minus;1.4 | 600 | Archivo |
| `display` | 34 / 40 / &minus;0.7 | 600 | Archivo |
| `title` | 22 / 28 / &minus;0.4 | 600 | Geist |
| `heading` | 17 / 24 / &minus;0.1 | 600 | Geist |
| `body` | 15 / 20 / 0 | 400 | Geist |
| `secondary` | 13 / 20 / +0.1 | 400 | Geist |
| `label` | 11 / 16 / +0.8, uppercase | 600 | Archivo, `font-stretch: 88%` |

Tracking is **dp, not em**: RN's `letterSpacing` is density-independent pixels, and these are already converted. `Geist Mono` with `tabular-nums` for machine values only: counts, times, ages, IDs, refs.

**Dynamic Type:** `body`, `secondary`, `heading`, `title` scale fully; `hero`, `display`, `label` clamp at 1.3&times;. `allowFontScaling={false}` is banned except on `hero`.

### Spacing, radii

```
spacing   4  8  12  16  24  32  48  96      (+ OS insets 54, 34)
radii     4  8  12  16  pill                 nested: inner = outer − padding
```

---

## 3. Components, with exact geometry

Transcribed from the mockup. These are the numbers.

| Component | Spec |
|---|---|
| **Tab bar** | 49 + 34 = 83 tall. Icon 25&times;25, Phosphor, `regular` unselected / `fill` selected. Label `label` role, 12 line height. Selected: 24&times;2 bar at top centre in `high`, radius 0 0 2 2. Background `canvas` at 74% with `blur(24) saturate(160%)`, `.5` top hairline. **No count badge.** |
| **Row** (`lrow`) | Margin `0 16 8`. Padding 12. Radius 12. `surface`. Min height 64. Gap 12. Leading category bar 3 wide, full height, z 2. Category wash 120 wide from the left at 16%, z 0. Trailing meta column right-aligned, gap 2. |
| **Section label** | Padding `0 16`, margin `32 0 8`. `label` role in `low`. Tight variant margin-top 24. |
| **Chip** | Height 28, padding `0 12`, radius 8, gap 8, `label` role. Solid: category fill, `onSolid` text. Outline: `border` stroke, `mid` text. Ghost: no stroke or fill, `low` text. **28 is the only chip height**; never scale one down. |
| **Segmented** | Height 32, radius pill, `overlay`, padding 2. Selected: `raised` + inset 1 `border`. |
| **Toggle** | 51&times;31, radius pill, padding 2, knob 27. Off: `overlay` + inset 1 `hairline`, knob `faint`. On: `high`, knob `canvas`. |
| **Brand mark** | 16/4, 20/4, 24/8, 32/8, 44/12 (size / radius). `overlay` tile, 1px specular top edge at 20% white. Glyph 11/12/14/18/24. |
| **Tier cell** | Flex 1, padding 12, radius 12, 1px transparent border. Bar 3 wide, inset 12 top and bottom. Selected: `surface` fill, `border`, bar runs full height, label to `high`. Glyph 20, top row spread with the count. |
| **Day arc** | Wrap 252 tall, margin-top 16. SVG 192. Outer r 88 stroke 5, inner r 66 stroke 16, 0.008 gap between tier arcs. Window 08:00 to 20:00 clockwise. Now marker r 5 in `high`. Glow 260 circle, radial `urgent` 14% to 0 at 62%. |
| **Feed card** | Full bleed including under the status bar. Body padding `70 16 0` (54 inset + 16). |
| **Bloom** | 340 tall from the bottom. Two layers: `radial-gradient(150% 74% at 50% 110%, hue .50, hue .16 at 42%, transparent 74%)` plus `linear-gradient(0deg, hue .16, transparent 58%)`. Per category: urgent .50/.16, byEod .42/.13, later .40/.13, canWait .34/.11. Light halves every stop. |
| **Action rail** | Absolute right 16, bottom 16, column, gap 12. Item 64 wide, gap 4. Glyph box 48. **No ring, border or fill.** Primary glyph 30 stroke 2 in `high`; others 26 stroke 1.7 in `mid`. Caption `label`, primary `high` others `mid`. |
| **Sheet** | Radius `16 16 0 0`, `raised`, padding `0 16 34`. Grabber 36&times;5 pill in `border`, margin `8 auto 16`. Category wash 220 tall at the top, 20% to 0. Detents medium and large. |
| **Big button** | Height 48, radius 12. Primary `high` fill with `canvas` text. Secondary 1px `border`, `high` text. |
| **Composer** | 1px `border`, radius 12, padding 12, `surface`. Send button 44 circle in `high`. |
| **Summary card** | Radius 12, padding 12, `surface`, `summary` tint at 16% on a 135&deg; gradient. Grid 2 columns, gap 8. |
| **Source card** | Margin `0 16 12`, padding 16, radius 16, 1px `hairline`, `summary` tint 220&times;130 from the top-left. |
| **Circular action** | 44 circle, `overlay`, 1px `border`, glyph 20 stroke 1.7 in `high`. |
| **Grain** | Tiled 140px `feTurbulence` at `baseFrequency .85`, 3 octaves, **5.5% opacity, `overlay` blend**, over the whole screen at z 30. |
| **Separator** | `StyleSheet.hairlineWidth` in `hairline`. Inset to the text origin, never full width, wherever rows are not cards. |

---

## 4. Screens, complete inventory

Every screen and state drawn in the mockup. **Nothing here is optional**; anything cut should be cut deliberately and recorded.

### Chrome
- **No title bar on any screen.** The large line is content and collapses to 17pt in a 44pt blurred bar on scroll. A source board keeps its collapsed bar because it needs a back affordance.

| Screen | Eyebrow | Large line |
|---|---|---|
| Your day | the date | `Good morning, Vicky`, by hour |
| Feed | none | none, the card is the screen |
| Later | `Last 30 days` | `137 did not need you` |
| Activity | `Last 30 days` | `3 sources connected` |
| You | the email | the user's name |

- **Status bar**: real signal, wifi and battery glyphs. Sits at z 24, above every sheet, as on iOS.

### Your day
Dual ring, tier selector, list. **Outer ring is time and monochrome** on a four-step grey ladder; **inner ring is work and the only place a tier hue appears**, matching the selector below it in colour, order and proportion, which is why the ring needs no legend.

Tier selector: three symmetric cells, each with its **category glyph**, count and label. Selecting swaps the list beneath from meetings to that tier's items and puts the count in the section header. Selecting again clears it. Four selection signals: fill, border, full-height bar, lifted label, so it survives greyscale.

States: resting, urgent selected, by-EOD selected, can-wait selected with the honest "nothing else is waiting" line.

### Feed
Full-screen cards, horizontal swipe, grouped Urgent, By EOD, Can wait, **Later**. **No divider cards, no progress rail, no tab badge.** Gestures track the finger 1:1 and reverse mid-flight.

Seven cards drawn, one per source and category: GitHub review, Slack mention, Gmail, Linear, Calendar, Google Docs can-wait, Slack later. Each differs only in **middle block** and **three rail actions**.

Sheets, each carrying the category wash and the regions `DetailSheet` already defines: Gmail open, Slack reply with composer, GitHub approve, Snooze picker.

### Later
**Structure preserved exactly.** Source strip, icon-only inactive and icon-plus-label active, selector in the `later` hue. One stream opened once, switching as a filter over rows in hand. Batches appended as they land with a running total. `sender: title`, `summary` beneath, `ago` right, external-link glyph. Footnote that it is read live and never stored.

States: loaded, still streaming with the spinner and running count, empty with the current copy and "Home" updated to "Your day".

### Activity
Root: one card per **connected** source only, with three counts, a sparkline and a chevron. Board: 34pt hero with its label inline, two circular actions, `headline` as a 2-column summary grid keeping `label`, `value_label ?? value` and `detail`, then `breakdown` under its own `breakdown_title`.

**A breakdown row links only when it has a `url`**, the semantic already encoded by withholding the chevron. External-link glyph, not a chevron, since these leave the app. `unavailable` renders as one honest sentence, never a tile with a dash in it.

Two boards drawn: GitHub, and Calendar as the case whose rows do not link.

### You
Notifications: one row, one toggle, one subtext, segmented `Urgent` / `+ By EOD` / `All` appearing only when on. **Appearance**: segmented `Dark` / `Light` / `System`, dark default. Connections: every source with state, `Add` in the section header, Connect sheet. **No AI section. No "Fix" button.**

### States that must not be faked
Empty Feed with the completed ring and where the other items went. Loading skeletons that resolve into something. **Never a placeholder row.**

---

## 5. Phase 1: sequence

Ordered so the riskiest assumption is tested first.

1. **Tokens.** `mobile/src/theme.ts` becomes `mobile/src/theme/`: `primitives`, `semantic`, `type`, `space`, `motion`, `haptics`. Components import semantic tokens only. Mode from `useColorScheme()`, dark default, override in `AsyncStorage`. Add `react-native-reanimated`, `react-native-gesture-handler`, `expo-haptics`, `expo-linear-gradient`, `expo-blur`, `expo-font`, `phosphor-react-native`, `lottie-react-native`. Fonts via the `expo-font` config plugin, **each weight its own family**, verified on a real iOS build because a name mismatch fails silently on iOS.
2. **Tab bar and icons.** Highest-leverage visible change: the current icons are empty squares and circles.
3. **One Feed card, end to end.** The tracer bullet. **Stop and compare against the mockup on a device before building anything else.**
4. **Feed tab**, remaining cards and sheets.
5. **Row component**, before the screens that use it.
6. **Your day**, including the dual ring and the selector interaction.
7. **Later**, restyle only.
8. **Activity**, root and board.
9. **You**, including Appearance.
10. **Motion and haptics**, as a pass over finished screens. Springs via Reanimated, never duration plus bezier. Haptics mark a change of state, never motion; `prepare()` ahead; never `Heavy`.

### Files

| File | Change |
|---|---|
| `theme.ts` | Deleted, replaced by `theme/` |
| `Chrome.tsx` | Header becomes the dissolving header; `TabIcon` becomes Phosphor |
| `FeedCard.tsx` | Rewritten as the full-screen card |
| `ListRow.tsx` | Rewritten as the row card |
| `YourDayCard.tsx` | Rewritten as ring plus selector |
| `BrandMark.tsx` | Real marks, own colours, five sizes |
| `DetailSheet.tsx` | Regions kept, detents and grabber added |
| `states.tsx` | Honest empty and loading states |
| `HomeScreen.tsx` | Becomes Your day, feed slider removed |
| `FeedScreen.tsx` | **New** |
| `LaterScreen.tsx` | Restyled, structure untouched |
| `SourcesScreen.tsx` | Becomes Activity root, connected only |
| `SourceDetailScreen.tsx` | Compacted board |
| `YouScreen.tsx` | AI section out, Appearance in |
| `App.tsx` | Five tabs, custom `tabBar`, `act()` signature fix |

---

## 6. Phase 2: backend, in scope

### 6.1 Six actions offered and rejected

`actionsFor` and `overflowFor` promise six actions `perform()` raises `UnknownAction` on. **Implement them.** Until each lands, its button does not render, because a button that fails is worse than a button that is absent.

| Action | Where | Work |
|---|---|---|
| `request_changes` | GitHub review | **Cheapest.** `_approve` already submits a review; this is the same call with `event="REQUEST_CHANGES"` and a required body |
| `assign_to_me` | GitHub assigned | Issues API `POST /issues/{n}/assignees` with the authenticated login |
| `comment` on Linear | Linear | `commentCreate` mutation. `_send` gains a Linear branch, and `source_ref` must carry the issue id |
| `accept` / `decline` | Calendar | Google Calendar `events.patch` on the self attendee's `responseStatus`. Two actions, one call shape |
| `reply` on Google Docs | Docs | Drive comments API `replies.create`. Needs the comment id in `source_ref` |
| `reply` on Gmail | Gmail | **Its own project.** Send scope, threading, quoting, signature. Do not fold it in here |

Each lands the same way: extend `_send` or add a sibling, map the failure to `ActionFailed`, respect any upstream "do not retry" signal, and write the test at the contract boundary with a `Fake*` implementation before the code.

### 6.2 Snooze has no picker

`act()` hardcodes three hours ([`App.tsx:195`](../mobile/App.tsx)). The endpoint already takes an arbitrary `until`, so the picker is **client-only** and can land in Phase 1: this evening, tomorrow morning, next week, pick a time.

### 6.3 Notifications have no "All" level

[`notifications.py:32`](../backend/services/notifications.py) defines exactly three:

```python
class NotifyLevel(str, Enum):
    URGENT = "urgent"
    URGENT_TODAY = "urgent_today"
    OFF = "off"

_ALLOWED = {
    NotifyLevel.URGENT:       {Tier.URGENT},
    NotifyLevel.URGENT_TODAY: {Tier.URGENT, Tier.TODAY},
    NotifyLevel.OFF:          set(),
}
```

`Urgent` maps to `URGENT` and `+ By EOD` to `URGENT_TODAY`, unchanged. **`All` has no member.** Add:

```python
ALL = "all"
_ALLOWED[NotifyLevel.ALL] = {Tier.URGENT, Tier.TODAY, Tier.CAN_WAIT}
```

The UI expresses `OFF` as the toggle, so the enum gains a value while the control still shows three. **`Tier.NOISE` stays out deliberately**: Later is by definition what did not need you, and notifying on it would undo the product. `urgent_today` keeps its wire value; renaming a persisted enum for a label change is a migration for nothing.

### 6.4 The board has no designated hero

`SourceDashboard.headline` is an unordered `StatLine[]` but the board wants one number at 34pt above the rest. Either add `hero: StatLine | null`, or fix the convention that `headline[0]` is the hero and document it on the model. **Convention is cheaper and reversible.**

### 6.5 Deliberately not proposed

**Diff stats on GitHub cards.** `FeedRow` has no file list or line counts. The v3 mockup invented them, the card works without them, and adding a field to feed one card is the wrong trade.

---

## 7. Verification

The script that ran against the mockup becomes a test. It currently passes on all 31 phones with zero findings, after catching, among others: a class-name collision putting 64px of margin on every secondary button; a bloom bright enough to make its own caption unreadable; three chips with hardcoded text colour that inverted in light mode; two fills below AA; a sparkline rounded into beads; and the last stray hex from a retired palette.

- Spacing on `4 8 12 16 24 32 48 96`, plus OS insets 54 and 34
- Radii on `4 8 12 16 pill`, nested as `inner = outer − padding`
- Type on the seven roles, nothing else
- **No colour outside the neutral ladder and the six hues**, excepting brand marks and sparklines
- Chip and body text at or above 4.5:1, both modes
- No non-inset shadow
- Nothing past the fold or under a fixed footer
- No control under 28pt, 44pt touch target via `hitSlop`
- Every row carries its category as a leading bar **and** a wash

---

## 8. Open questions

1. **Sequencing against the other session.** `mobile/` and `backend/` are both being edited on this branch. Phase 1 rewrites `theme.ts` and every screen, so it needs a clean handoff or its own branch.
2. **`Tier.TODAY` is labelled "By EOD" everywhere.** The wire value stays `today`. Worth confirming nothing else reads that string as a display label.
3. **Gmail reply** is the one Phase 2 item large enough to want its own plan.
