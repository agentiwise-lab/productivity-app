/**
 * The states an unconsidered screen gets wrong.
 *
 * An empty feed reads as "nothing needs you" whether the truth is that you are
 * clear, that nothing is connected, or that we could not ask. None of these say
 * "Nothing here" and stop; every one names what would have appeared and what to
 * do about it.
 *
 * There are no placeholder rows anywhere. A skeleton that resolves into nothing
 * is a screen that lied for two seconds.
 */

import React, { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { radius, space, useTheme } from '../theme';
import { BigButton, T } from './ui';
import { clockTime } from '../lib/time';

/** A slow pulse, so a loading screen is visibly alive rather than merely empty. */
function usePulse() {
  const value = useSharedValue(0.65);
  useEffect(() => {
    value.value = withRepeat(
      withTiming(1, { duration: 700, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [value]);
  return useAnimatedStyle(() => ({ opacity: value.value }));
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  const c = useTheme();
  const pulse = usePulse();
  return (
    <View>
      {Array.from({ length: rows }, (_, index) => (
        <Animated.View
          key={index}
          style={[
            {
              height: 64,
              marginHorizontal: space.md,
              marginBottom: space.xs,
              borderRadius: radius.md,
              backgroundColor: c.overlay,
            },
            pulse,
          ]}
        />
      ))}
    </View>
  );
}

/** The Day ring while its counts hydrate: a pulsing ring of the same size, so
 *  the screen holds its shape instead of flashing an empty "0 NEED YOU". */
export function RingSkeleton() {
  const c = useTheme();
  const pulse = usePulse();
  return (
    <View style={{ height: 300, alignItems: 'center', justifyContent: 'center', marginTop: space.md }}>
      <Animated.View
        style={[
          {
            width: 232,
            height: 232,
            borderRadius: 116,
            borderWidth: 22,
            borderColor: c.overlay,
          },
          pulse,
        ]}
      />
    </View>
  );
}

/** The three tier tiles under the ring, as placeholders. */
export function TilesSkeleton() {
  const c = useTheme();
  const pulse = usePulse();
  return (
    <View style={{ flexDirection: 'row', gap: space.xs, marginHorizontal: space.md }}>
      {[0, 1, 2].map((i) => (
        <Animated.View
          key={i}
          style={[
            { flex: 1, height: 64, borderRadius: radius.md, backgroundColor: c.overlay },
            pulse,
          ]}
        />
      ))}
    </View>
  );
}

/** A block of honest copy. Two lines, and never a shrug. */
export function Explain({
  title,
  body,
  action,
  onAction,
  top = 48,
}: {
  title: string;
  body: string;
  action?: string;
  onAction?: () => void;
  top?: number;
}) {
  return (
    <View style={{ paddingHorizontal: space.md, paddingTop: top }}>
      <T role="title">{title}</T>
      <T role="body" tone="mid" style={{ marginTop: space.xs }}>
        {body}
      </T>
      {action && onAction ? (
        <BigButton
          label={action}
          variant="primary"
          onPress={onAction}
          style={{
            marginTop: space.md,
            alignSelf: 'flex-start',
            paddingHorizontal: space.lg,
          }}
        />
      ) : null}
    </View>
  );
}

export function Clear({
  heldBack,
  filtered = false,
}: {
  heldBack: number;
  filtered?: boolean;
}) {
  return (
    <Explain
      title={filtered ? 'Nothing in this category' : 'You are clear for today'}
      body={
        heldBack > 0
          ? `${heldBack} ${heldBack === 1 ? 'item' : 'items'} arrived and did not need you. They are in Later.`
          : 'Nothing across your sources is waiting on you.'
      }
    />
  );
}

export function NothingConnected({ onConnect }: { onConnect: () => void }) {
  return (
    <Explain
      title="Connect your first tool"
      body="Your feed is built from GitHub, Slack, Calendar, Linear, Gmail and Docs. Connect one to see what needs you."
      action="Open You"
      onAction={onConnect}
    />
  );
}

/**
 * Not a banner in an accent colour: the point is that the rows below are real
 * but old, so it sits quietly above them rather than shouting over them.
 */
export function StaleBanner({ fetchedAt }: { fetchedAt: Date | null }) {
  const c = useTheme();
  return (
    <View
      style={{
        marginHorizontal: space.md,
        marginTop: space.xs,
        backgroundColor: c.surface,
        borderRadius: radius.md,
        padding: space.sm,
      }}
    >
      <T role="secondary" tone="mid">
        Cannot reach the backend. Showing what we had
        {fetchedAt ? ` from ${clockTime(fetchedAt)}` : ''}.
      </T>
    </View>
  );
}
