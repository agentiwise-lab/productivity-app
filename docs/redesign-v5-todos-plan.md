# v5 To-dos redesign: scrollable feed

Reference mock: [`docs/mockups/v5-todos.html`](mockups/v5-todos.html)

## 1. Scope and principle

This is a **UI/UX-only** change to one tab. The backend, the wire contract
(`FeedRow`), the classification pipeline, the action service, and the detail
sheet are all already built and stay exactly as they are. Nothing about *what*
an item is, *which tier* it lands in, or *which actions* it offers changes. Only
*how the To-dos tab draws that* changes.

The To-dos tab (internally still the `feed` route) stops being a full-screen
Reels deck swiped one card at a time and becomes a **vertical scroll of bounded
cards**, the LinkedIn/Instagram feed shape. Per the review of the mock:

- **No left edge line.** Tier reads from a single quiet top wash plus the chip.
- **No page header.** The list begins on the first section label; the section
  labels and the per-card chips already name everything.
- **The modal flow is kept verbatim.** Tapping a card opens the detail sheet.
  Reply and Comment open the composer rather than firing an empty send.
- The vertical action rail becomes a **horizontal action bar** under each card.

Only two files are rewritten: `mobile/src/screens/FeedScreen.tsx` and
`mobile/src/components/FeedCard.tsx`. Everything they call
(`lib/actions.ts`, `lib/rowText.ts`, `components/DetailSheet.tsx`,
`components/ui.tsx`, `components/BrandMark.tsx`, `App.tsx` wiring) is unchanged.

## 2. The per-source event matrix

This is the exhaustive map of what each source pings, what tier and type each
event resolves to, and what actions the card then offers. It is derived from
the code that already ships: the integration mappers set `reason`,
`backend/services/rules.py` turns `reason` into `(tier, type_tag)`, and
`mobile/src/lib/actions.ts` (`railFor` + `IMPLEMENTED`) turns
`(source, type_tag, status)` into the buttons. The new UI draws exactly this
matrix; it does not add or remove a single action.

**Actions legend.** `Reply`/`Comment`/`Changes` need text, so they open the
composer (`needsComposer`). Everything else is one shot. `Open` and `Snooze`
exist on every source; `Read` (mark-read) exists only where the source has an
unread state to move (Slack, Gmail). A button only renders if the backend
actually implements it, so nothing on a card can fail. The **first** action is
drawn as the filled primary whenever the row is Urgent or By EOD; Can wait and
Later rows carry no filled action. A few inherited first-action choices read
oddly (Comment filled on a security alert, Reply filled on a bot failure); they
are existing `railFor` behaviour and out of scope for a UI-only redraw.

### GitHub
`reason` is GitHub's own notification reason, plus the PR flags
(`approval_requested`, `review_requested`, `review_state`, `check_conclusion`).

| Event (reason) | Tier | type_tag | Card actions (primary first) |
|---|---|---|---|
| `security_alert` | Urgent | alert | **Comment** · Open · Snooze |
| CI `failure` on your own PR | Urgent | alert | **Comment** · Open · Snooze |
| `approval_requested` | Urgent | approve | **Approve** · Comment · Changes |
| `review_requested` | Urgent | review | **Approve** · Comment · Changes |
| `changes_requested` on your PR | By EOD | decide | **Comment** · Open · Snooze |
| `assign` | By EOD* | assigned | **Assign to me** · Comment · Snooze |
| `mention` | By EOD* | reply | **Comment** · Open · Snooze |
| `team_mention` | Can wait | reply | Comment · Open · Snooze |
| `comment` | Can wait | comment | Comment · Open · Snooze |
| `subscribed`/`author`/`manual`/`state_change`/`ci_activity` | Later (noise) | fyi | Open · Bring back |

\* rule floor; the model may promote or demote using the prose. Implemented
GitHub actions: `comment`, `approve`, `request_changes`, `assign_to_me`.

### Slack
A Slack message has no type, only text, so tier is always a judgement; the
mapper does the filtering before the rules.

| Event (reason) | Tier | type_tag | Card actions |
|---|---|---|---|
| `slack_dm` (blocking) | By EOD* | reply | **Reply** · Read · Snooze |
| `slack_mention` | By EOD* | reply | **Reply** · Read · Snooze |
| `slack_thread_reply` | Can wait | reply | Reply · Read · Snooze |
| `slack_bot_failure` (your build broke) | By EOD* | alert | **Reply** · Read · Snooze |
| `slack_bot_noise` | Later (noise) | fyi | Open · Bring back · Read |

Implemented Slack actions: `reply`, `mark_read`.

### Linear
Linear states its own priority and dates, so most of it is settled without the
model.

| Event (reason) | Tier | type_tag | Card actions |
|---|---|---|---|
| `linear_urgent` (priority Urgent) | Urgent | assigned | **Comment** · Open · Snooze |
| `linear_high` (priority High) | By EOD | assigned | **Comment** · Open · Snooze |
| `linear_due` (has due date) | By EOD | assigned | **Comment** · Open · Snooze |
| `linear_in_progress` | By EOD* | assigned | **Comment** · Open · Snooze |
| `linear_assigned` (no priority/date) | By EOD* | assigned | **Comment** · Open · Snooze |
| `linear_backlog` | Can wait | assigned | Comment · Open · Snooze |

Implemented Linear actions: `comment`. Comment is the filled primary on Urgent
and By EOD items (priority Urgent/High, due, in-progress, assigned) and unfilled
on Can wait (backlog).

### Calendar
| Event (reason) | Tier | type_tag | Card actions |
|---|---|---|---|
| `calendar_invite` (blocking) | By EOD | rsvp | **Accept** · Decline · Open |
| `calendar_starting` (imminent) | Urgent | fyi | **Accept** · Decline · Open |
| `calendar_changed` | By EOD | fyi | **Accept** · Decline · Open |
| `calendar_cancelled` | Later (noise) | fyi | Open · Bring back |

Implemented Calendar actions: `accept`, `decline`. (Note: an already-accepted
`calendar_starting` event still offers Accept/Decline today. That is existing
behaviour and out of scope for a UI-only change; flagged for a later pass.)

### Gmail
| Event (reason) | Tier | type_tag | Card actions |
|---|---|---|---|
| `gmail_message` | By EOD* | reply | **Reply** · Open · Snooze |
| `gmail_bulk` (newsletters, promos) | Later (noise) | fyi | Open · Bring back · Read |

`Read` appears in Later here because Gmail is one of the two sources with an
unread state; the same is true for Slack. GitHub, Linear, Calendar, and Docs
Later cards show Open · Bring back only.

Implemented Gmail actions: `reply`, `mark_read` (Read appears in the sheet's
overflow).

### Google Docs
| Event (reason) | Tier | type_tag | Card actions |
|---|---|---|---|
| `docs_mention` | By EOD* | comment | **Open** · Snooze |
| `docs_comment` | Can wait | comment | Open · Snooze |
| `docs_edited` | Later (noise) | fyi | Open · Bring back |

Implemented Docs actions: none (the Drive comments API is not wired). Reply is
filtered out, so Docs opens and snoozes only. This is deliberate: a button that
would fail is worse than one that is absent.

**Tier to section mapping in the feed:** `urgent -> Urgent`,
`today -> By EOD`, `can_wait -> Can wait`, `noise/snoozed -> Later`.

## 3. How the current functionality resolves in the new UI

Every behaviour of the current full-screen card has a home in the new bounded
card. Nothing is dropped except the two affordances the full-screen format
existed to serve.

| Current (Reels deck) | New (scrollable feed) |
|---|---|
| Horizontal `FlatList`, `pagingEnabled`, one card per screen | Vertical `FlatList`, section-grouped, several cards per screen |
| Swipe left/right to move between items | Scroll |
| Tier order encoded by swipe sequence | Tier order encoded by **section labels** (Urgent / By EOD / Can wait / Later) with a count |
| Full-bleed bloom + top tint carry tier | A single low-alpha **top wash** carries tier |
| No left edge (never had one); category also on chip | Same: chip carries the label, wash carries the hue |
| `t-display` (34pt) title, vertically centred to fill the screen | `t-heading` (17pt) title, top-anchored in a bounded card |
| Vertical action rail, bottom-right, Instagram-Reels shape | Horizontal **action bar** under the content, evenly split, hairline dividers |
| `OpenHint` pulsing ripple hints the card opens | Removed: in a list, tapping a card to open detail is the expected gesture and needs no hint |
| Tap card body -> `onOpen(row)` opens sheet | Same: tap anywhere on the card's content region -> `onOpen(row)` |
| Rail Reply/Comment -> `onOpen(row, true)` (composer) | Same: action-bar Reply/Comment -> `onOpen(row, true)` |
| Rail one-shot -> `haptics.commit()` + `onAction(row, id)` | Same |
| `reason` shown as a "why this is <tier>" block | Shown as a compact "why" block on **Urgent cards only**; deeper reasoning stays in the sheet, which keeps the feed scannable |
| Meta strip: blocking · when · repo | Same meta line, above the action bar |
| Loading -> `Skeleton`; empty -> `Clear` | Same states, unchanged |

The detail sheet, its composer-on-demand, the Open-as-link, the overflow
actions, and every per-source text rule (`rowText.ts`) are untouched. The feed
still passes the same `onOpen` and `onAction` handlers from `App.tsx`.

## 4. Implementation spec

### 4.1 `FeedScreen.tsx`

- Keep the input props and the filter/sort. Replace the horizontal paging
  `FlatList` with a vertical one whose data is a flattened, section-grouped
  array so headers virtualize with the cards:
  - Group `ordered` by tier in `ORDER` (`urgent, today, can_wait, noise`).
  - Build `Item[] = sections.flatMap(s => [{kind:'header', label, count}, ...s.rows.map(row => ({kind:'card', row}))])`.
  - `renderItem` switches on `kind`: `header` renders `SectionLabel`, `card`
    renders `FeedCard`.
  - `keyExtractor`: `header:${label}` / `card:${row.id}`.
- Drop `useWindowDimensions`, the measured `height`, `getItemLayout`, and the
  `onLayout` seed: a vertical list sizes itself.
- `Skeleton` (loading) and `Clear` (empty) states unchanged.
- Section labels use the existing `SectionLabel` (`tight` on the first).

### 4.2 `FeedCard.tsx`

Bounded card, no bleed, no safe-area math, no bloom.

```
<View card>                              // surface, radius.md(16), marginHorizontal space.md,
                                         // marginBottom space.xs, border hairline, overflow hidden
  <Wash category vertical height 128 alpha 0.16 />   // reuse ui Wash, top only
  <Pressable onPress={() => onOpen(row)}>            // the whole content region opens the sheet
    <Header> BrandMark 40 · stack{ sourceName, headerSubline } · Chip(category, solid) </Header>
    <Body>   primaryLine (heading, 2 lines) · cardSubtitle (body, mid, 2 lines) </Body>
    {urgent && row.reason ? <Why> "Why this is urgent" · reason </Why> : null}
    <Meta>   is_blocking? "Blocking" · when · repo? </Meta>
  </Pressable>
  <ActionBar>                            // borderTop hairline, flexDirection row
    rail.map(action => <ActionButton />) // flex:1, height 48, hairline divider between,
                                         // icon 20 + label; primary: high + bold, else mid
  </ActionBar>
</View>
```

- `ActionButton.onPress`: identical logic to today's `RailButton`:
  `needsComposer(id) ? onOpen(row, true) : (haptics.commit(), onAction(row, id))`.
- All geometry from theme tokens (`space`, `radius`, `size`, `type`) so the
  design audit stays clean. Card radius 16, margins 16/4, wash alpha 0.16,
  type roles heading/body/secondary/label only.
- Delete `OpenHint`, `Bloom`/`TopTint` imports, `useWindowDimensions`,
  `useSafeAreaInsets`, `topInset`.

### 4.3 What is NOT touched
`DetailSheet.tsx`, `lib/actions.ts`, `lib/rowText.ts`, `lib/subtext.ts`,
`components/ui.tsx`, `Bloom.tsx` (kept for other screens), `App.tsx`, the tab
label ("To-dos"), and the entire backend.

## 5. Verification

Frontend-only, so no TDD (per the frontend rule), but proven live:

1. `npm run web`, render the To-dos tab at 393x852 in both appearances.
2. Confirm: no left line, no page header, list starts on the first section
   label, cards separated, action bar renders the right buttons per source,
   primary emphasis only on Urgent/By EOD.
3. Tap a card -> sheet opens. Tap Reply -> sheet opens with composer focused.
   Tap a one-shot (Snooze/Approve) -> acts in place. This exercises the kept
   modal flow end to end.
4. Run `scripts/audit.js` `__audit()` on the tab in both modes; expect an
   empty result (no stray colours, off-scale spacing, off-ramp radii,
   off-scale type, outset shadows, sub-28 controls, past-fold, or sub-AA
   contrast).
5. `Skeleton` on cold load and `Clear` on an empty queue both still show.
