/**
 * One item, as a bounded card in a scrollable feed.
 *
 * Not a full screen any more. Several cards share the viewport, so the tier no
 * longer arrives as a full-bleed bloom rising off the bottom edge; it is one
 * quiet wash across the top, and the chip carries the word. There is no left
 * edge line: the wash and the chip are the whole signal.
 *
 * The card is three regions: a header (who and what), a body (the subject and a
 * preview), and an action bar beneath a hairline (what you can do). Tapping the
 * content opens the detail sheet, where the decision is actually made. Reply and
 * Comment on the bar open the sheet with its composer rather than firing an
 * empty send; every other action is one shot and acts in place.
 *
 * What changes per source is the body text (via rowText) and the bar's actions
 * (via lib/actions), so a GitHub review and a Slack mention stay the same shape
 * of decision and the reader never relearns the layout scrolling down.
 */

import React from 'react';
import { Pressable, View } from 'react-native';
import {
  CATEGORY_LABEL,
  CATEGORY_OF_TIER,
  haptics,
  radius,
  size,
  space,
  useTheme,
} from '../theme';
import { BrandMark } from './BrandMark';
import { Icon } from './Icon';
import { Chip, T, Wash } from './ui';
import { needsComposer, railFor, type RailAction } from '../lib/actions';
import { ago, deadlineLabel } from '../lib/time';
import {
  cardSubtitle,
  headerSubline,
  primaryLine,
  sourceName,
} from '../lib/rowText';
import type { FeedRow } from '../api/types';

export function FeedCard({
  row,
  onAction,
  onOpen,
}: {
  row: FeedRow;
  onAction: (row: FeedRow, action: string) => void;
  /** Tapping the body opens the sheet, where the decision is actually made. */
  onOpen: (row: FeedRow, compose?: boolean) => void;
}) {
  const c = useTheme();
  const category = CATEGORY_OF_TIER[row.tier];
  const rail = railFor(row);
  const heading = primaryLine(row);
  const subline = headerSubline(row);
  const body = cardSubtitle(row);
  const when = deadlineLabel(row.deadline) ?? ago(row.occurred_at);
  // The grounds for the decision, shown inline only on the strongest tier; on
  // every other card it stays in the sheet, which keeps the feed scannable.
  // Gmail and Slack already carry the reason as their subtitle, so the boxed
  // "why" would only repeat it there.
  const showWhy =
    row.tier === 'urgent' &&
    !!row.reason &&
    row.source !== 'gmail' &&
    row.source !== 'slack';
  // "Blocking" means a person is waiting on you, a signal separate from the
  // tier. It only earns a place when it varies: on GitHub (review/approval/
  // assign) and Calendar (invites) it distinguishes some items from others. On
  // Gmail (every non-bulk mail) and Slack (every DM/mention/reply) it is true
  // for everything that reaches the feed, so it says nothing the chip does not
  // and the meta is just the time.
  const showBlocking =
    row.is_blocking && row.source !== 'gmail' && row.source !== 'slack';

  return (
    <View
      style={{
        marginHorizontal: space.md,
        marginBottom: space.sm,
        borderRadius: radius.lg,
        borderWidth: 1,
        borderColor: c.hairline,
        backgroundColor: c.surface,
        overflow: 'hidden',
      }}
    >
      {/* One wash across the top, low, so the tier reads at a glance without a
          bloom competing with the next card down. */}
      <Wash category={category} height={128} direction="vertical" alpha={0.16} />

      <Pressable onPress={() => onOpen(row)}>
        {/* Header. */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: space.sm,
            paddingHorizontal: space.md,
            paddingTop: space.md,
          }}
        >
          <BrandMark source={row.source} size={44} />
          <View style={{ flex: 1, minWidth: 0 }}>
            <T role="heading" lines={1}>
              {sourceName(row)}
            </T>
            {subline ? (
              <T role="secondary" tone="low" lines={1}>
                {subline}
              </T>
            ) : null}
          </View>
          {CATEGORY_LABEL[category] ? (
            <Chip
              label={CATEGORY_LABEL[category]}
              variant="solid"
              category={category}
            />
          ) : null}
        </View>

        {/* Body. */}
        <View style={{ paddingHorizontal: space.md, paddingTop: space.sm }}>
          <T role="heading" lines={2}>
            {heading}
          </T>
          {body && body !== heading ? (
            <T role="body" tone="mid" lines={2} style={{ marginTop: space.xxs }}>
              {body}
            </T>
          ) : null}
        </View>

        {showWhy ? (
          <View
            style={{
              marginHorizontal: space.md,
              marginTop: space.sm,
              borderRadius: radius.md,
              padding: space.sm,
              backgroundColor: c.lift,
            }}
          >
            <T role="label" tone="mid">
              Why this is urgent
            </T>
            <T role="body" style={{ marginTop: space.xxs }} lines={3}>
              {row.reason}
            </T>
          </View>
        ) : null}

        {/* Meta. */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: space.xs,
            paddingHorizontal: space.md,
            paddingTop: space.sm,
            paddingBottom: space.md,
          }}
        >
          {showBlocking ? (
            <>
              <T role="label">Blocking</T>
              <T role="label" tone="mid">
                ·
              </T>
            </>
          ) : null}
          <T role="secondary" tone="mid" numeric>
            {when}
          </T>
          {row.repo ? (
            <>
              <T role="label" tone="mid">
                ·
              </T>
              <T role="secondary" tone="mid" numeric lines={1}>
                {row.repo}
              </T>
            </>
          ) : null}
        </View>
      </Pressable>

      {/* Action bar: the rail, laid horizontal under a hairline. Evenly split,
          glyph plus label, the primary at full weight. Same onPress logic the
          vertical rail had: a composer action opens the sheet, everything else
          acts in place. */}
      <View style={{ flexDirection: 'row', borderTopWidth: 1, borderTopColor: c.hairline }}>
        {rail.map((action, index) => (
          <ActionButton
            key={action.id}
            action={action}
            divider={index > 0}
            onPress={() => {
              if (needsComposer(action.id)) {
                onOpen(row, true);
                return;
              }
              haptics.commit();
              onAction(row, action.id);
            }}
          />
        ))}
      </View>
    </View>
  );
}

function ActionButton({
  action,
  divider,
  onPress,
}: {
  action: RailAction;
  /** A hairline between it and the button to its left. */
  divider: boolean;
  onPress: () => void;
}) {
  const c = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityLabel={action.label}
      style={({ pressed }) => [
        {
          flex: 1,
          height: size.bigButton,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: space.xs,
        },
        divider ? { borderLeftWidth: 1, borderLeftColor: c.hairline } : null,
        pressed ? { opacity: 0.6 } : null,
      ]}
    >
      <Icon
        name={action.glyph}
        size={20}
        color={action.primary ? c.high : c.mid}
        weight={action.primary ? 'bold' : 'regular'}
      />
      <T role="label" tone={action.primary ? 'high' : 'mid'}>
        {action.label}
      </T>
    </Pressable>
  );
}
