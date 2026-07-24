# Implementation plan

**Date:** 2026-07-24
**Design source of truth:** [`mockups/v4-screens.html`](mockups/v4-screens.html), drawn at true device size.
**Rules:** [`design-system-v2.md`](design-system-v2.md), amended by §1 below.

Two phases, deliberately separated. **Phase 1 changes only the UI and touches no backend contract.** Phase 2 extends the backend for things the redesign surfaced that do not exist yet. Phase 1 is shippable on its own.

---

## 0. A bug found while writing this, which outranks everything below

`ActionBody.action` defaults to `"comment"` ([`backend/main.py:87`](../backend/main.py)), and the client never sends an action name:

```ts
// mobile/src/api/client.ts
act(itemId: string, body: string) {
  return this.request<FeedRow>(`/feed/${itemId}/actions`, {
    method: 'POST',
    body: JSON.stringify({ body }),   // no `action` field
  });
}
```

**So every action routed through `api.act()` is performed as `comment`.** Tapping **Approve** posts a comment instead of submitting a review, which is exactly the failure `_approve`'s own docstring was written to prevent:

> "Submitting a review, not posting a comment. A comment reading 'approved' leaves the pull request just as blocked as before."

It is worse than that. The card calls `onAction(row, action.id)` with no body, so the request carries `body: ""`, and `_send` rejects empty text with `ActionFailed("an empty reply is not a reply")`. That surfaces as a 409 and the app restores the row with *"That didn't go through"*.

**Read from the code, not reproduced against a running server.** Confirm with one integration test before fixing, then fix by sending the action name:

```ts
act(itemId: string, action: string, body = '') {
  return this.request<FeedRow>(`/feed/${itemId}/actions`, {
    method: 'POST',
    body: JSON.stringify({ action, body }),
  });
}
```

and drop the `action` default on `ActionBody` so a missing action is a 422 rather than a silent comment.

This is a one-line client fix plus a contract tightening, it is independent of the redesign, and **it should go first.**

---

## 1. Colour, amended

[`design-system-v2.md` §1](design-system-v2.md) specified one accent and one alarm. **That is now three hues, and they mean tier and nothing else.**

| Token | Dark | Light | Means |
|---|---|---|---|
| `urgent` | `#FF6B5F` | `#CC4432` | Someone is blocked on you |
| `byEod` | `#63E4C2` | `#0D8167` | Due before tonight |
| `canWait` | `#AB7FF8` | `#7144CC` | Neither |

All three sit in one band so they read as a family rather than as three unrelated signals. They were tuned twice: first lightened, because the violet arrived deep and saturated beside a light mint and looked like a different class of signal; then **brought 75% of the way back toward the original saturation**, because the pastel that resulted was harmonious and lifeless. This is the midpoint that keeps the family and keeps the punch.

Contrast of the near-black chip text: **7.0:1, 12.6:1 and 6.7:1** in dark, **4.7:1, 4.7:1 and 6.1:1** in light. All clear AA. The two light values sit close to the floor, so **re-measure before changing any light-mode fill.**

**The rule that makes this work: everything that is not a tier is neutral.** Buttons, toggles, status dots, selection bars, tab chrome and brand marks all use the grey ladder. The old design had mint doing double duty as "By EOD" *and* as the primary button, which is what made the palette feel arbitrary.

**Two exemptions, and only two: brand marks, above, and data visualisation.** The Activity sparklines are neutral by the letter of the rule and looked dead for it. A sparkline encodes a quantity over time, not a priority, so it cannot be misread as a tier. Nothing else gets this exemption.

Consequences, all applied in v4:

- **Brand marks keep their own colours.** This was tried monochrome and rejected. A mark is identity, not priority, and it never occupies a position where a tier signal lives, so it cannot be misread as one. **Do not desaturate the source icons during implementation**, in the Feed, in Later, in Activity, in You, or in an action sheet. Use the official marks: GitHub is monochrome by its own brand, Slack is four-colour, Gmail red, Linear indigo, Google blue.
- **Source tints are gone.** Card washes, sheet washes and row washes are tier-coloured now, so the colour at the top of a sheet answers "how urgent" rather than "which tool".
- **All three tier chips are solid** with near-black text. Previously only Urgent was solid and the other two were outline and ghost, which read as three different components.
- The tab bar's selected indicator, the "live" status dot and the toggle "on" state moved to neutral.

A verification pass over all 30 phones reports zero colours outside the neutral ladder, these three hues, and the two exemptions.

---

## 2. Phase 1: UI only

No API change, no new fields, no new endpoints. Ordered so the riskiest assumption is tested first.

### 1.1 Token layer

Replace `mobile/src/theme.ts` with `mobile/src/theme/`, per [`design-system-v2.md` §11](design-system-v2.md).

**Delete `SCALE` and `s()`.** Every size in the app is currently a mockup measurement times 1.379, which is why nothing lands on a whole point. v4 is drawn at 1 pixel to 1 point, so its numbers transfer directly.

Add: `react-native-reanimated`, `react-native-gesture-handler`, `expo-haptics`, `expo-linear-gradient`, `expo-blur`, `expo-font`, `phosphor-react-native`.

Fonts: Geist, Geist Mono, Archivo, Instrument Serif, all OFL, embedded via the `expo-font` config plugin. **Register each weight as its own family** and verify on a real iOS build, because a font-name mismatch fails silently on iOS while working on Android.

### 1.2 Tab bar and icons

Five tabs: Day, Feed, Later, Activity, You. Hand-built via the `tabBar` prop on `@react-navigation/bottom-tabs`, which the app already uses, so Expo's alpha `NativeTabs` never enters the picture.

Phosphor icons, `regular` unselected and `fill` selected, 25×25, 49pt bar plus 34pt inset. **The current icons are empty squares and circles**, so this is the single highest-leverage visible change in the app.

### 1.3 One Feed card, end to end

The tracer bullet. Build the GitHub urgent card: monochrome mark, solid tier chip, 34pt title, `summary` body, the `reason` block, the bloom from beneath, and the bare-icon vertical rail. **Stop here and look at it on a device before building anything else.**

### 1.4 Feed tab

New screen. Full-screen cards, horizontal swipe, grouped Urgent, By EOD, Can wait, Later. Gestures track the finger 1:1 and are reversible mid-flight. Actions open source sheets rather than committing blind. No divider cards and no progress rail.

### 1.5 Headers, on every screen

**No screen has a title bar, and no large title repeats its own tab name.** The tab bar already says where you are, so spending 68pt to say it again is the redundancy the dissolving header was meant to remove.

| Screen | Eyebrow, 11pt | Large line, 34pt |
|---|---|---|
| Your day | the date | **`Good morning, Vicky`**, varying by hour |
| Activity | `Last 30 days` | `3 sources connected` |
| You | the email | the user's name |
| Later | `Last 30 days` | `Later` |

Later keeps its name because "Later" states what the list *means* rather than which tab it is: everything that arrived and did not need you. If that reads as inconsistent in use, it should go the same way as the others.

The line collapses to 17pt in a 44pt blurred bar on scroll, and a source board keeps its collapsed bar permanently because it needs a back affordance.

### 1.6 Your day

`HomeScreen` becomes Your day. Remove the horizontal card feed; it lives in the Feed tab now.

- Dual ring. **Outer is time and monochrome; inner is work and is the only place a tier hue appears.** The tier selector directly below it is the inner ring's legend.
- The tier row becomes a real selector: selecting swaps the list beneath it from meetings to that tier's items. Selection shows as fill, border, a full-height bar and a lifted label, so it survives greyscale.

### 1.7 Rows, everywhere

One `Row` component, used by Your day, Later, Activity and You. Discrete cards on `surface` at radius 12 with 8pt between them, a 3pt tier bar on the leading edge where a tier exists, and a tier wash from the left.

**A hairline separates two rows by one pixel, which is why the old lists read as a single undifferentiated block however good the type was.** This is the change that fixes "the listing UI looks primitive" and it is worth doing before the screens that use it.

### 1.8 Later

**Structure preserved exactly.** Source strip with icon-only inactive and icon-plus-label active; one stream opened once with switching as a filter over rows already in hand; batches appended as they land with a running total; `sender: title` with `summary` beneath and `ago` right; the footnote that it is read live and never stored; the empty copy with "Home" updated to "Your day". Restyled only.

### 1.9 Activity

`SourcesScreen` becomes Activity root. **Only connected sources appear**: connection state belongs in You. The Connect button leaves this tab.

`SourceDetailScreen` keeps `headline`, `breakdown`, `breakdown_title` and `unavailable` exactly. The header compacts from roughly 470pt to 290: a 34pt hero with its label inline, two neutral glyph buttons, then `headline` as a two-column grid of separated cards, each keeping its `label`, `value_label ?? value` and `detail`.

**A breakdown row is tappable only when it has a `url`**, which is the semantic the screen already encodes by withholding the chevron. Use an external-link glyph rather than a chevron, because these leave the app.

### 1.10 You

Remove the AI summaries section entirely. Summarising and ranking is what the product is, so asking permission per source framed the core behaviour as an optional extra.

Notifications become one row, one toggle, one subtext line, with the level segmented control appearing only when on: roughly 200pt down to 60. Connections list every source with its state and take the Connect flow as a sheet. **No "Fix" button**: a connection is live, or it needs connecting.

### 1.11 Sheets

Keep the three regions `DetailSheet` already defines and the reason they exist: head and footer fixed, only the message scrolls. Add `medium` and `large` detents with a visible grabber, replacing the fixed `height: '82%'`.

### 1.12 Motion and haptics

Last, as a pass over finished screens. Springs via Reanimated, never duration plus bezier. Haptics mark a change of state, never motion; `prepare()` ahead of time; never `Heavy`.

---

## 3. Phase 2: backend

Everything here is a gap the redesign surfaced. **None of it blocks Phase 1**, which is drawn against what already works.

### 2.1 Actions that are offered and rejected

`actionsFor` and `overflowFor` in [`lib/actions.ts`](../mobile/src/lib/actions.ts) promise six actions that `perform()` raises `UnknownAction` on:

| Action | Offered for | Backend state |
|---|---|---|
| `reply` | Google Docs | `_send` accepts Slack and GitHub only |
| `comment` | Linear | same |
| `accept` | Calendar | no handler |
| `decline` | Calendar | no handler |
| `request_changes` | GitHub review | no handler |
| `assign_to_me` | GitHub assigned | no handler |

**Decide per action: implement it, or remove it from the matrix.** Leaving a button that fails is the worst of the three. My recommendation is to remove all six in Phase 1 so the UI only offers what works, and add them back as Phase 2 lands each one. `request_changes` is the cheapest, since the GitHub review API is already wired for `approve`.

### 2.2 Snooze has no picker

`act()` hardcodes three hours (`App.tsx:195`). The design has a picker: this evening, tomorrow morning, next week, pick a time. The endpoint already takes an arbitrary `until`, so **this is client-only work** and could move into Phase 1.

### 2.3 The board has no designated hero

`SourceDashboard.headline` is an unordered `StatLine[]`, but the board wants one number at 34pt above the rest. Either add `hero: StatLine | null`, or fix the convention that `headline[0]` is the hero and document it. **Convention is cheaper and reversible.**

### 2.4 Things deliberately not proposed

- **Diff stats on GitHub cards.** `FeedRow` has no file list or line counts, the v3 mockup invented them, and the card works without them. Only add if a real user need appears.
- **Gmail reply.** Genuinely useful, genuinely a project: OAuth scope, threading, quoting. Worth its own plan.

---

## 4. What must not regress

v4 ships with an automated check, and the same assertions should become a lint or a test:

- Spacing on `4 / 8 / 12 / 16 / 24 / 32 / 48 / 96` only
- Radii on `4 / 8 / 12 / 16 / pill` only, nested as `inner = outer − padding`
- Type on the seven roles only
- **No colour outside the neutral ladder and the three tier hues**, excepting brand marks and data visualisation
- Chip text at or above 4.5:1 on every tier fill, in both modes
- No non-inset shadow anywhere
- No content past the fold, and none hidden under a fixed footer
- No control under 28pt, and a 44pt touch target via `hitSlop`

It caught six things in v4 that reading did not, including a class-name collision that put 64px of margin on every secondary button, and a bloom bright enough to make the text on top of it unreadable.

---

## 5. Open questions

1. **"By EOD" grouping in the Feed.** The tier is deadline-based. If the intent was ever ownership, that is a backend change and it changes the Feed's grouping.
2. **Sequencing against the other session.** `backend/` and `mobile/` are both being edited on this branch by another session. Phase 1 rewrites `theme.ts` and every screen, so it needs a clean handoff or its own branch.
