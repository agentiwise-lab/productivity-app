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
import { radius, space, useTheme } from '../theme';
import { CollapsedTitle, ScreenHeader } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Icon } from '../components/Icon';
import { T } from '../components/ui';
import { TopTint } from '../components/Bloom';
import { Explain, Skeleton } from '../components/states';
import type { SourceInfo } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

export function ActivityScreen({
  sources,
  loadingStatus,
  onOpen,
}: {
  sources: SourceInfo[];
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
        contentContainerStyle={{ paddingTop: insets.top, paddingBottom: space.xl }}
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
            <SourceCard key={info.source} info={info} onPress={() => onOpen(info)} />
          ))
        )}
      </AnimatedScrollView>
      <CollapsedTitle title={title} scrollY={scrollY} />
    </View>
  );
}

function SourceCard({
  info,
  onPress,
}: {
  info: SourceInfo;
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
          hue, which never shares a screen with a tier. A corner radial rather
          than a band: it reads as light falling across the card instead of a
          stripe painted along the top of it. */}
      <TopTint category="summary" width={361} height={130} />

      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm, flex: 1 }}>
          <BrandMark source={info.source} size={32} />
          <T role="heading">{info.label}</T>
        </View>
        {/* A chevron rather than a status word: every card here is connected
            by definition, so the word would only ever say the same thing. */}
        <Icon name="chevron" size={16} color={c.low} weight={1.8} />
      </View>

      <View style={{ flexDirection: 'row', gap: space.xl, marginTop: space.md }}>
        <Stat value={info.count} label="Items" />
        <Stat value={info.urgent} label="Urgent" />
      </View>
    </Pressable>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <View>
      <T role="title" numeric>
        {String(value)}
      </T>
      <T role="label" tone="low">
        {label}
      </T>
    </View>
  );
}
