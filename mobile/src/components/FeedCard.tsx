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

import React, { useEffect } from 'react';
import { Pressable, useWindowDimensions, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
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
import { needsComposer, railFor, type RailAction } from '../lib/actions';
import { ago, deadlineLabel } from '../lib/time';
import { decodeEntities, subtext } from '../lib/subtext';
import type { FeedRow, Source } from '../api/types';

/**
 * The 34pt line. Normally the subject, but a mail with no subject was drawing
 * the literal string "(no subject)" as large as everything else on the screen.
 * When the title says nothing, the message says it instead.
 */
function cardTitle(row: FeedRow): string {
  const title = decodeEntities((row.title || '').trim());
  const empty = !title || /^\(no subject\)$/i.test(title);
  if (!empty) return title;
  const fallback = subtext(row);
  return fallback || row.sender_name || 'Message';
}

const SOURCE_NAME: Record<Source, string> = {
  github: 'GitHub',
  slack: 'Slack',
  gmail: 'Gmail',
  linear: 'Linear',
  calendar: 'Calendar',
  google_docs: 'Google Docs',
};

/**
 * The line under the source name: what this item belongs to, in the terms of
 * its own source. A GitHub item is a repository, a Gmail item is who sent it, a
 * Linear item is its project or identifier, a Slack item is its channel or the
 * person. Naming it "Inbox" for every mail, which is what `context_chip` did,
 * told the reader nothing they did not already know from the mark beside it.
 */
function context(row: FeedRow): string | null {
  const value = subline(row);
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  // Never the source name printed twice, and never a generic mailbox label.
  const lower = trimmed.toLowerCase();
  if (lower === SOURCE_NAME[row.source].toLowerCase()) return null;
  if (lower === 'inbox') return row.sender_name || row.sender_handle || null;
  return trimmed;
}

function subline(row: FeedRow): string | null {
  switch (row.source) {
    case 'github':
      return row.repo || row.context_chip;
    case 'gmail':
      return row.sender_name || row.sender_handle || null;
    case 'slack':
      return row.context_chip || row.sender_name || row.sender_handle;
    case 'linear':
      // The issue identifier (ENG-412) or its project, never the word "Linear".
      return row.context_chip && row.context_chip !== 'Linear'
        ? row.context_chip
        : row.repo || null;
    case 'calendar':
      return row.context_chip;
    default:
      return row.context_chip || row.repo || row.sender_handle;
  }
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
  const heading = cardTitle(row);
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
            {heading}
          </T>

          {body && body !== heading ? (
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

      {/* The one hint that the card opens. Centred at the bottom where nothing
          else sits, breathing slowly so it is noticed without being read as an
          instruction. Tapping it is tapping the card. */}
      <OpenHint onPress={() => onOpen(row)} />

      {/* The column sits over the You tab beneath it: its buttons are centred
          on the same x as the last nav item, which is why the right inset is
          small rather than a full margin. A wide rail floating in from the
          edge was most of what read as the card wasting its right half. */}
      <View
        style={{
          position: 'absolute',
          right: space.xs,
          bottom: space.md,
          alignItems: 'center',
          gap: space.md,
        }}
      >
        {rail.map((action) => (
          <RailButton
            key={action.id}
            action={action}
            onPress={() => {
              // A reply or a comment needs text, so it opens the sheet with the
              // composer rather than firing an empty send. Everything else is
              // one shot and acts in place.
              if (needsComposer(action.id)) {
                onOpen(row);
                return;
              }
              haptics.commit();
              onAction(row, action.id);
            }}
          />
        ))}
      </View>

      {/* Clears the rail column on the right rather than a fixed 96. */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.xs,
          paddingLeft: space.md,
          paddingRight: 72,
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

/**
 * A "details" grabber, in the shape iOS uses for a sheet that can be pulled up.
 * It breathes on a four-second cycle between two low opacities, so it lives at
 * the edge of noticing: enough to say the card is a door, quiet enough that it
 * never competes with the copy or the rail.
 */
function OpenHint({ onPress }: { onPress: () => void }) {
  const c = useTheme();
  const pulse = useSharedValue(0.35);
  useEffect(() => {
    pulse.value = withRepeat(
      withTiming(0.7, { duration: 2000, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [pulse]);
  const style = useAnimatedStyle(() => ({ opacity: pulse.value }));

  return (
    <Pressable
      onPress={onPress}
      hitSlop={16}
      accessibilityLabel="Open details"
      style={{
        position: 'absolute',
        bottom: space.xs,
        left: 0,
        right: 0,
        alignItems: 'center',
      }}
    >
      <Animated.View
        style={[
          {
            width: 36,
            height: 4,
            borderRadius: 999,
            backgroundColor: c.high,
          },
          style,
        ]}
      />
    </Pressable>
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
      // 44 of touch height via hitSlop rather than an empty 44pt box: the box
      // was leaving a wide gap between the glyph and its label.
      hitSlop={{ top: 8, bottom: 8, left: 12, right: 12 }}
      style={({ pressed }) => [
        { alignItems: 'center', gap: space.xxs },
        pressed ? { opacity: 0.6 } : null,
      ]}
    >
      <Icon
        name={action.glyph}
        size={action.primary ? 26 : 23}
        color={action.primary ? c.high : c.mid}
        weight={action.primary ? 'bold' : 'regular'}
      />
      <T role="label" tone={action.primary ? 'high' : 'mid'}>
        {action.label}
      </T>
    </Pressable>
  );
}
