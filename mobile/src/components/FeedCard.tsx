/**
 * One thing, filling the screen.
 *
 * The card bleeds under the status bar rather than starting below it, which is
 * what lets the category colour reach the very top of the screen. The status
 * bar floats over it and stays above every sheet, as it does on iOS.
 *
 * Every card is the same four regions and differs only in two of them: the
 * middle block, and the three actions on the rail. That is deliberate. A GitHub
 * review and a Slack mention are the same shape of decision, and drawing them
 * as two different screens would make the reader relearn the layout each swipe.
 *
 * The rail is bottom right and vertical, which is Instagram's shape. The glyph
 * is the button: no ring, no border, no fill. Hierarchy comes from glyph size
 * and label weight and never from colour, so the category hues stay meaningful.
 */

import React from 'react';
import { Pressable, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  CATEGORY_LABEL,
  CATEGORY_OF_TIER,
  haptics,
  space,
  topInset,
  useTheme,
} from '../theme';
import { Bloom, TopTint } from './Bloom';
import { BrandMark } from './BrandMark';
import { Icon } from './Icon';
import { Chip, T } from './ui';
import { railFor, type RailAction } from '../lib/actions';
import { ago, deadlineLabel } from '../lib/time';
import { subtext } from '../lib/subtext';
import type { FeedRow, Source } from '../api/types';

const SOURCE_NAME: Record<Source, string> = {
  github: 'GitHub',
  slack: 'Slack',
  gmail: 'Gmail',
  linear: 'Linear',
  calendar: 'Calendar',
  google_docs: 'Google Docs',
};

/** The line under the source name, or nothing when it would only repeat it. */
function context(row: FeedRow): string | null {
  const value = row.context_chip || row.repo || row.sender_handle || '';
  if (!value) return null;
  return value.toLowerCase() === SOURCE_NAME[row.source].toLowerCase()
    ? null
    : value;
}

export function FeedCard({
  row,
  onAction,
  onOpen,
}: {
  row: FeedRow;
  onAction: (row: FeedRow, action: string) => void;
  /** Tapping the body opens the sheet, where the decision is actually made. */
  onOpen: (row: FeedRow) => void;
}) {
  const c = useTheme();
  const safeArea = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const category = CATEGORY_OF_TIER[row.tier];
  const rail = railFor(row);
  const body = subtext(row);
  const when = deadlineLabel(row.deadline) ?? ago(row.occurred_at);

  return (
    <View style={{ flex: 1, backgroundColor: c.surface, overflow: 'hidden' }}>
      <TopTint category={category} width={width} />
      <Bloom category={category} width={width} />

      <Pressable
        onPress={() => onOpen(row)}
        // The card bleeds under the status bar so the category colour reaches
        // the top of the screen; the content still has to start below it.
        style={{
          flex: 1,
          paddingTop: topInset(safeArea.top) + space.xs,
          paddingHorizontal: space.md,
          minHeight: 0,
        }}
      >
        <View
          style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}
        >
          <BrandMark source={row.source} size={44} />
          <View style={{ flex: 1, minWidth: 0 }}>
            <T role="heading">{SOURCE_NAME[row.source]}</T>
            {/* Only when it says something the line above does not. Linear
                sets `context_chip` to "Linear", which read as the source name
                printed twice. */}
            {context(row) ? (
              <T role="secondary" tone="low" numeric lines={1}>
                {context(row)}
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

        {/* Centred rather than stacked under the header.
          A card is a whole screen and most items are a title and one line, so
          top-anchoring left three hundred points of nothing between the copy
          and the rail, and every card read as a page that had failed to load
          the rest of itself. Centring costs nothing when the content is long,
          because the block simply fills the space it is centred in. */}
        <View
          style={{
            flex: 1,
            justifyContent: 'center',
            paddingBottom: space.xxl,
          }}
        >
          <T role="display" lines={3}>
            {row.title}
          </T>

          {body ? (
            <T role="body" tone="mid" lines={3} style={{ marginTop: space.md }}>
              {body}
            </T>
          ) : null}

          {row.reason ? (
            // The middle block. `reason` is a real field that until now only ever
            // appeared inside the detail sheet, so the card was asking for a
            // decision without showing the grounds for it.
            <View
              style={{
                marginTop: space.lg,
                borderRadius: 12,
                padding: space.sm,
                backgroundColor: c.lift,
              }}
            >
              <T role="label" tone="mid">
                Why this is {(CATEGORY_LABEL[category] || 'here').toLowerCase()}
              </T>
              <T role="body" style={{ marginTop: space.xs }} lines={4}>
                {row.reason}
              </T>
            </View>
          ) : null}
        </View>
      </Pressable>

      <View
        style={{
          position: 'absolute',
          right: space.md,
          bottom: space.md,
          alignItems: 'center',
          gap: space.sm,
        }}
      >
        {rail.map((action) => (
          <RailButton
            key={action.id}
            action={action}
            onPress={() => {
              haptics.commit();
              onAction(row, action.id);
            }}
          />
        ))}
      </View>

      {/* 96 of right padding, so the strip never runs under the rail. */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.xs,
          paddingLeft: space.md,
          paddingRight: 96,
          paddingBottom: space.md,
        }}
      >
        {row.is_blocking ? (
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
    </View>
  );
}

function RailButton({
  action,
  onPress,
}: {
  action: RailAction;
  onPress: () => void;
}) {
  const c = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityLabel={action.label}
      style={({ pressed }) => [
        { width: 64, alignItems: 'center', gap: space.xxs },
        pressed ? { opacity: 0.6 } : null,
      ]}
    >
      <View
        style={{
          width: 44,
          height: 44,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon
          name={action.glyph}
          size={action.primary ? 27 : 24}
          color={action.primary ? c.high : c.mid}
          weight={action.primary ? 'bold' : 'regular'}
        />
      </View>
      <T role="label" tone={action.primary ? 'high' : 'mid'}>
        {action.label}
      </T>
    </Pressable>
  );
}
