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
  const value = useSharedValue(0.4);
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
              backgroundColor: c.surface,
            },
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

/**
 * The empty state of the meetings section on Day, which is a different claim
 * from an empty feed.
 *
 * "You are clear for today" was appearing here with urgent and by-EOD items
 * still waiting in the ring directly above it, because the meetings list being
 * empty is not the day being empty. This talks about the calendar, and then, if
 * anything still needs the reader, points them at it rather than at Later.
 */
export function NoMeetingsLeft({
  counts,
}: {
  counts: { urgent: number; byEod: number; canWait: number };
}) {
  const pressing = counts.urgent + counts.byEod;
  const total = pressing + counts.canWait;
  const body =
    total === 0
      ? 'Nothing on your calendar, and nothing waiting on you either.'
      : pressing > 0
        ? `Nothing on your calendar. ${line(counts)} still on you: pick a category above.`
        : `Nothing on your calendar. ${counts.canWait} can wait, above.`;
  return <Explain title="No meetings left today" body={body} top={space.lg} />;
}

function line(counts: { urgent: number; byEod: number }): string {
  const parts: string[] = [];
  if (counts.urgent) parts.push(`${counts.urgent} urgent`);
  if (counts.byEod) parts.push(`${counts.byEod} by end of day`);
  return parts.join(', ');
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
