/**
 * Activity: what has been going on in each source.
 *
 * A different question from the feed's "what needs me now", which is why it is
 * a tab rather than a settings page.
 *
 * **The numbers here are the source's own activity, not the feed's.** The first
 * version counted feed items per source, so GitHub read "nothing in 30 days"
 * while the board one tap inside listed twelve open pull requests: the feed only
 * holds what needs action right now, which is the opposite of what this tab
 * asks. Each card now shows the same live summary the board does, and never a
 * "needs you" figure, because needing you is the feed's job and not this one's.
 *
 * **Only connected sources appear.** Connection state belongs in You, and a
 * source you have not connected has nothing to report.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { ScrollView, Pressable, View } from 'react-native';
import Animated, {
  useAnimatedScrollHandler,
  useSharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { radius, space, topInset, useTheme } from '../theme';
import { CollapsedTitle, ScreenHeader } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Icon } from '../components/Icon';
import { T } from '../components/ui';
import { TopTint } from '../components/Bloom';
import { Explain, Skeleton } from '../components/states';
import type { ApiClient } from '../api/client';
import type { SourceDashboard, SourceInfo, StatLine } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

/** loading, or the board, or the reason there is no board to show. */
type Board = 'loading' | SourceDashboard | { error: string };

export function ActivityScreen({
  sources,
  api,
  loadingStatus,
  onOpen,
}: {
  sources: SourceInfo[];
  api: ApiClient;
  loadingStatus: boolean;
  onOpen: (info: SourceInfo) => void;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const scrollY = useSharedValue(0);
  const onScroll = useAnimatedScrollHandler((event) => {
    scrollY.value = event.contentOffset.y;
  });

  const connected = useMemo(
    () => sources.filter((info) => info.status === 'connected'),
    [sources],
  );
  const title = `${connected.length} ${connected.length === 1 ? 'source' : 'sources'} connected`;

  // One board per connected source, fetched in parallel. They are computed live
  // at each provider and slow by design, so each card fills in on its own
  // rather than the tab waiting on the slowest of them.
  const [boards, setBoards] = useState<Record<string, Board>>({});
  const key = connected.map((info) => info.source).join(',');
  useEffect(() => {
    let live = true;
    setBoards((prev) => {
      const next: Record<string, Board> = {};
      for (const info of connected) next[info.source] = prev[info.source] ?? 'loading';
      return next;
    });
    connected.forEach((info) => {
      api
        .sourceDashboard(info.source)
        .then((board) => {
          if (live) setBoards((prev) => ({ ...prev, [info.source]: board }));
        })
        .catch(() => {
          if (live)
            setBoards((prev) => ({
              ...prev,
              [info.source]: { error: 'Could not read this source right now.' },
            }));
        });
    });
    return () => {
      live = false;
    };
    // Refetch only when the set of connected sources changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas }}>
      <AnimatedScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentContainerStyle={{ paddingTop: topInset(insets.top), paddingBottom: space.xl }}
      >
        <ScreenHeader eyebrow="Last 30 days" title={title} />
        <View style={{ height: space.lg }} />

        {loadingStatus && connected.length === 0 ? (
          <Skeleton rows={3} />
        ) : connected.length === 0 ? (
          <Explain
            title="Nothing connected yet"
            body="Activity reports on the sources you have connected. Connect one in You and its board appears here."
            top={0}
          />
        ) : (
          connected.map((info) => (
            <SourceCard
              key={info.source}
              info={info}
              board={boards[info.source] ?? 'loading'}
              onPress={() => onOpen(info)}
            />
          ))
        )}
      </AnimatedScrollView>
      <CollapsedTitle title={title} scrollY={scrollY} />
    </View>
  );
}

/**
 * One source, at a glance: the two or three figures that describe its month.
 * The board a tap away has the full breakdown.
 */
function SourceCard({
  info,
  board,
  onPress,
}: {
  info: SourceInfo;
  board: Board;
  onPress: () => void;
}) {
  const c = useTheme();
  const stats = summarise(board);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        {
          marginHorizontal: space.md,
          marginBottom: space.sm,
          padding: space.md,
          borderRadius: radius.lg,
          backgroundColor: c.surface,
          borderWidth: 1,
          borderColor: c.hairline,
          overflow: 'hidden',
        },
        pressed ? { opacity: 0.7 } : null,
      ]}
    >
      {/* A board is a summary rather than a category, so it takes the summary
          hue, which never shares a screen with a tier. */}
      <TopTint category="summary" width={361} height={120} />

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
        <BrandMark source={info.source} size={32} />
        <T role="heading" style={{ flex: 1 }} lines={1}>
          {info.label}
        </T>
        <Icon name="chevron" size={16} color={c.low} />
      </View>

      {board === 'loading' ? (
        <T role="secondary" tone="low" style={{ marginTop: space.md }}>
          Reading the last 30 days...
        </T>
      ) : 'error' in board ? (
        <T role="secondary" tone="low" style={{ marginTop: space.md }}>
          {board.error}
        </T>
      ) : stats.length === 0 ? (
        <T role="secondary" tone="low" style={{ marginTop: space.md }}>
          Quiet across the last 30 days.
        </T>
      ) : (
        <View style={{ flexDirection: 'row', marginTop: space.md, gap: space.lg }}>
          {stats.map((stat, index) => (
            <Stat
              key={stat.label}
              value={stat.value_label ?? String(stat.value)}
              label={stat.label}
              hero={index === 0}
            />
          ))}
        </View>
      )}
    </Pressable>
  );
}

/**
 * The headline figures, at most three, that a glance can hold.
 *
 * The board leads with a "Needs you" figure, which is the feed's question and
 * not this tab's: Activity is for seeing what a source has been doing, so the
 * "needs you" stat is dropped and what is left is pure volume. What remains is
 * the source's real headline (open PRs, meetings, messages) and the two figures
 * under it.
 */
function summarise(board: Board): StatLine[] {
  if (board === 'loading' || 'error' in board) return [];
  return board.headline
    .filter((stat) => stat.label.trim().toLowerCase() !== 'needs you')
    .slice(0, 3);
}

function Stat({
  value,
  label,
  hero,
}: {
  value: string;
  label: string;
  hero: boolean;
}) {
  return (
    <View style={{ minWidth: 0 }}>
      {/* The first figure is the source's headline and reads a step larger, the
          way the board inside draws it. */}
      <T role={hero ? 'title' : 'heading'} numeric tone="high">
        {value}
      </T>
      <T role="label" tone="low" lines={1}>
        {label}
      </T>
    </View>
  );
}
