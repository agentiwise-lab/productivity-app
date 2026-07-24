/**
 * Activity: what has been going on in each source.
 *
 * A different question from the feed's "what needs me now", which is why it is
 * a tab rather than a settings page.
 *
 * **Only connected sources appear.** Connection state belongs in You, and
 * showing a dead source here made half of this tab a settings screen wearing a
 * chart. A source you have not connected has nothing to report.
 */

import React from 'react';
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
import { Sparkline, SPARK_GAP, dailyCounts, hasShape } from '../components/Sparkline';
import type { FeedRow, SourceInfo } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

export function ActivityScreen({
  sources,
  rows,
  loadingStatus,
  onOpen,
}: {
  sources: SourceInfo[];
  /** The same feed the other tabs read, so the bars cannot disagree with them. */
  rows: FeedRow[];
  loadingStatus: boolean;
  onOpen: (info: SourceInfo) => void;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const scrollY = useSharedValue(0);
  const onScroll = useAnimatedScrollHandler((event) => {
    scrollY.value = event.contentOffset.y;
  });

  const connected = sources.filter((info) => info.status === 'connected');
  const title = `${connected.length} ${connected.length === 1 ? 'source' : 'sources'} connected`;

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
              counts={dailyCounts(
                rows
                  .filter((row) => row.source === info.source)
                  .map((row) => row.occurred_at ?? row.created_at),
              )}
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
 * One source, at a glance.
 *
 * It used to carry two 22pt numbers labelled `Items` and `Urgent`, which was
 * the wrong shape twice over. "Items" is the app's own internal word for a row
 * in its database and means nothing to a reader, and a source that is quiet
 * showed a pair of enormous zeroes: the emptiest card on the screen was also
 * the loudest. The card now states what it knows in one sentence and spends
 * its height on the thirty-day shape instead, which is the thing that is
 * actually worth glancing at. The real figures are one tap away on the board.
 */
function SourceCard({
  info,
  counts,
  onPress,
}: {
  info: SourceInfo;
  counts: number[];
  onPress: () => void;
}) {
  const c = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        {
          marginHorizontal: space.md,
          marginBottom: space.sm,
          padding: space.sm,
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
          hue, which never shares a screen with a tier. A corner radial rather
          than a band: it reads as light falling across the card instead of a
          stripe painted along the top of it. */}
      <TopTint category="summary" width={361} height={96} />

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
        <BrandMark source={info.source} size={32} />
        <View style={{ flex: 1, minWidth: 0 }}>
          <T role="heading" lines={1}>
            {info.label}
          </T>
          <T role="secondary" tone="low" lines={1}>
            {volumeLine(info)}
          </T>
        </View>
        {/* A chevron rather than a status word: every card here is connected
            by definition, so the word would only ever say the same thing. */}
        <Icon name="chevron" size={16} color={c.low} />
      </View>

      {hasShape(counts) ? (
        <View style={{ marginTop: SPARK_GAP }}>
          <Sparkline counts={counts} />
        </View>
      ) : null}
    </Pressable>
  );
}

/** What the source has been doing, in the reader's words rather than ours. */
function volumeLine(info: SourceInfo): string {
  if (info.count === 0) return 'Nothing in the last 30 days';
  const seen = `${info.count} in 30 days`;
  return info.urgent > 0 ? `${info.urgent} need you · ${seen}` : seen;
}
