/**
 * Later: what arrived from a source and did not need you.
 *
 * Read live and stored nowhere. It used to be 360 saved rows, which meant
 * keeping a month of newsletters in the database to render a list that is
 * different tomorrow anyway. Now it asks the provider what is currently unread,
 * unanswered or open, so it cannot drift from what you see in Gmail itself.
 *
 * The rows stream in. Pulling every unread message takes most of a minute, and
 * a list that appears only at the end reads as broken, so batches are appended
 * as they land and the count climbs while you look at it.
 *
 * One source at a time, chosen from the strip. "Everything" is deliberately not
 * an option: it would be four slow fetches to build a list nobody reads to the
 * end of.
 *
 * The structure above is exactly what was built. Only the surface changed.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, View } from 'react-native';
import Animated, {
  useAnimatedScrollHandler,
  useSharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { haptics, radius, size, space, useTheme } from '../theme';
import { CollapsedTitle, ScreenHeader } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Row } from '../components/ListRow';
import { SectionLabel, T } from '../components/ui';
import { Explain } from '../components/states';
import { streamEvents, type StreamHandle } from '../api/stream';
import { ago } from '../lib/time';
import type { ApiClient } from '../api/client';
import type { LaterRow, Source } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

/** Only the sources that have a "did not need you" pile worth reading. */
const SOURCES: { id: Source; label: string }[] = [
  { id: 'gmail', label: 'Gmail' },
  { id: 'slack', label: 'Slack' },
  { id: 'linear', label: 'Linear' },
  { id: 'github', label: 'GitHub' },
];

export function LaterScreen({
  api,
  onOpen,
}: {
  api: ApiClient;
  onOpen: (url: string) => void;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const [source, setSource] = useState<Source>('gmail');
  const [all, setAll] = useState<LaterRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const handle = useRef<StreamHandle | null>(null);
  const scrollY = useSharedValue(0);
  const onScroll = useAnimatedScrollHandler((event) => {
    scrollY.value = event.contentOffset.y;
  });

  // One stream for every source, opened once. Switching source used to start a
  // fresh fetch and wait on it again; now it is a filter over rows already in
  // hand, so the strip responds immediately.
  useEffect(() => {
    const { url, headers } = api.laterStream();
    handle.current = streamEvents<LaterRow>({
      url,
      headers,
      onBatch: (batch) => setAll((current) => [...current, ...batch]),
      onDone: () => setLoading(false),
      onError: (message) => {
        setError(message);
        setLoading(false);
      },
    });
    return () => handle.current?.cancel();
  }, [api]);

  const rows = useMemo(
    () => all.filter((row) => row.source === source),
    [all, source],
  );
  const label = SOURCES.find((entry) => entry.id === source)?.label ?? '';
  const title = `${all.length} did not need you`;

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas }}>
      <AnimatedScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentContainerStyle={{
          paddingTop: insets.top,
          paddingBottom: space.xl,
        }}
      >
        <ScreenHeader eyebrow="Last 30 days" title={title} />

        {/* Icon-only when inactive, icon plus label when active, so the strip
            stays one line however many sources there are. */}
        <View
          style={{
            flexDirection: 'row',
            gap: space.xs,
            paddingHorizontal: space.md,
            paddingTop: space.md,
          }}
        >
          {SOURCES.map((entry) => {
            const on = entry.id === source;
            return (
              <Pressable
                key={entry.id}
                onPress={() => {
                  haptics.select();
                  setSource(entry.id);
                }}
                style={[
                  {
                    height: size.control,
                    borderRadius: radius.md,
                    borderWidth: 1,
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: space.xs,
                    paddingHorizontal: space.sm,
                    borderColor: c.hairline,
                    backgroundColor: c.surface,
                  },
                  // The selector takes the same hue the rows below it take,
                  // because it is selecting within Later rather than between
                  // categories.
                  on ? { borderColor: c.hue.later, backgroundColor: c.overlay } : null,
                ]}
              >
                <BrandMark source={entry.id} size={16} />
                {on ? (
                  // The hue lives in the border and the fill. As text on a
                  // tinted overlay it measured 3.6 in light mode, and a label
                  // that has to be legible cannot be the place the colour is
                  // carried.
                  <T role="label" tone="high">
                    {entry.label}
                  </T>
                ) : null}
              </Pressable>
            );
          })}
        </View>

        <SectionLabel
          label={label}
          tight
          // The header never claims a total it does not have yet.
          count={loading ? 'counting...' : `${rows.length} items`}
        />

        {rows.map((row) => (
          <Row
            key={row.source_ref}
            category="later"
            leading={<BrandMark source={row.source} size={32} />}
            title={
              <T role="body" lines={1}>
                {row.sender_name ? (
                  <T role="body" medium>
                    {row.sender_name}
                  </T>
                ) : null}
                {row.sender_name ? ' · ' : ''}
                {row.title}
              </T>
            }
            subtitle={row.summary}
            meta={ago(row.occurred_at)}
            glyph={row.url ? 'external' : null}
            onPress={row.url ? () => onOpen(row.url) : undefined}
          />
        ))}

        {loading ? (
          <View style={{ alignItems: 'center', gap: space.sm, paddingTop: space.xl }}>
            <ActivityIndicator color={c.hue.later} />
            {all.length > 0 ? (
              <T role="secondary" tone="mid" numeric>
                {`${all.length} from all sources so far`}
              </T>
            ) : null}
            <T
              role="secondary"
              tone="low"
              style={{ paddingHorizontal: space.xxl, textAlign: 'center' }}
            >
              Reading every source at once.
            </T>
          </View>
        ) : null}

        {!loading && error ? (
          <Explain title="Could not read Later" body={error} />
        ) : null}

        {!loading && !error && rows.length === 0 ? (
          <Explain
            title="Nothing waiting here"
            body={`Everything from ${label} either needed you, and is on Your day, or you have already dealt with it.`}
          />
        ) : null}

        {!loading && rows.length > 0 ? (
          <View style={{ paddingHorizontal: space.md, paddingTop: space.xs }}>
            <T role="secondary" tone="low">
              {rows.length} from {label}. Read live, never stored.
            </T>
          </View>
        ) : null}
      </AnimatedScrollView>
      <CollapsedTitle title={title} scrollY={scrollY} />
    </View>
  );
}
