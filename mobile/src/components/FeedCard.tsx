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
import {
  cardSubtitle,
  headerSubline,
  primaryLine,
  sourceName,
} from '../lib/rowText';
import type { FeedRow, Source } from '../api/types';

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
  const safeArea = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const category = CATEGORY_OF_TIER[row.tier];
  const rail = railFor(row);
  const heading = primaryLine(row);
  const subline = headerSubline(row);
  const body = cardSubtitle(row);
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
            <T role="heading">{sourceName(row)}</T>
            {/* The item's own context: the sender, the channel, the repo, or
                the kind of ask. Never "Inbox", and never the source name
                printed twice. */}
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
          else sits, pinging slowly so it is noticed without being read as an
          instruction. Tapping it is tapping the card. */}
      <OpenHint colour={c.hue[category]} onPress={() => onOpen(row)} />

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
                onOpen(row, true);
                return;
              }
              haptics.commit();
              onAction(row, action.id);
            }}
          />
        ))}
      </View>

      {/* Clears the rail column on the right. */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.xs,
          paddingLeft: space.md,
          paddingRight: space.huge,
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
 * The one hint that the card opens: a slow ripple around a small dot, the way a
 * live point pings on a map.
 *
 * The earlier version was a horizontal grab-bar at the very bottom, which on a
 * real phone lands a few points above the home indicator and reads as a second,
 * broken one. A ripple is round, so it cannot be mistaken for that bar, and it
 * sits well clear of the indicator zone. It pulses rather than sits still,
 * because a static dot is decoration and a pulsing one is an invitation.
 */
function OpenHint({ colour, onPress }: { colour: string; onPress: () => void }) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withRepeat(
      withTiming(1, { duration: 2800, easing: Easing.out(Easing.ease) }),
      -1,
      false,
    );
  }, [p]);

  // Two rings a half-cycle apart, so there is always one expanding. Kept faint
  // and in the category hue rather than white, so it reads as a quiet live
  // point rather than a bright control.
  const ring = (offset: number) =>
    useAnimatedStyle(() => {
      const t = (p.value + offset) % 1;
      return {
        transform: [{ scale: 0.5 + t * 0.9 }],
        opacity: (1 - t) * 0.28,
      };
    });
  const ringA = ring(0);
  const ringB = ring(0.5);

  // 44 of touch, an 18pt ping: a tap target's worth of area, a hint's worth of ink.
  return (
    <Pressable
      onPress={onPress}
      hitSlop={16}
      accessibilityLabel="Open details"
      style={{
        position: 'absolute',
        bottom: 60,
        left: 0,
        right: 0,
        alignItems: 'center',
        justifyContent: 'center',
        height: 18,
      }}
    >
      {[ringA, ringB].map((style, index) => (
        <Animated.View
          key={index}
          pointerEvents="none"
          style={[
            {
              position: 'absolute',
              width: 18,
              height: 18,
              borderRadius: 999,
              borderWidth: 1,
              borderColor: colour,
            },
            style,
          ]}
        />
      ))}
      <View
        style={{
          width: 5,
          height: 5,
          borderRadius: 999,
          backgroundColor: colour,
          opacity: 0.6,
        }}
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
