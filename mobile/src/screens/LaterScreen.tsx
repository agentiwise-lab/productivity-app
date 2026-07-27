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
import { haptics, radius, size, space, topInset, useTheme } from '../theme';
import { ScreenHeader } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Row } from '../components/ListRow';
import { SectionLabel, T } from '../components/ui';
import { Explain } from '../components/states';
import { streamEvents, type StreamHandle } from '../api/stream';
import { ago } from '../lib/time';
import type { ApiClient } from '../api/client';
import type { FeedRow, LaterRow, Source, SourceInfo } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

/**
 * A live Later row rendered as a FeedRow so it can open the same detail sheet
 * the feed uses. It is noise (nothing here was judged), unread (never snoozed,
 * so the sheet offers Open and nothing that would fail), and its id is
 * synthetic because the row is streamed live and stored nowhere.
 */
function laterRowToFeedRow(row: LaterRow, index: number): FeedRow {
  return {
    id: `later:${row.source_ref}:${index}`,
    user_id: '',
    source: row.source,
    source_ref: row.source_ref,
    tier: 'noise',
    priority_score: 0,
    rule_tier: 'noise',
    llm_tier: null,
    tier_source: 'rule',
    type_tag: 'fyi',
    needs_llm: false,
    title: row.title,
    summary: row.summary,
    reason: null,
    url: row.url,
    repo: '',
    context_chip: row.context_chip,
    sender_name: row.sender_name,
    sender_handle: null,
    deadline: null,
    occurred_at: row.occurred_at,
    created_at: null,
    snoozed_until: null,
    handled_at: null,
    is_blocking: false,
    status: 'unread',
    body: row.summary,
  };
}

const LABELS: Record<Source, string> = {
  gmail: 'Gmail',
  slack: 'Slack',
  linear: 'Linear',
  github: 'GitHub',
  google_docs: 'Google Docs',
  calendar: 'Calendar',
};

export function LaterScreen({
  api,
  sources,
  onOpenRow,
}: {
  api: ApiClient;
  sources: SourceInfo[];
  onOpenRow: (row: FeedRow) => void;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();

  // Only sources the user has actually connected, and never Calendar: a meeting
  // is not a "did not need you" pile. This replaces the old hardcoded strip that
  // showed Linear even when it was never integrated.
  const available = useMemo(
    () =>
      sources.filter(
        (info) => info.status === 'connected' && info.source !== 'calendar',
      ),
    [sources],
  );

  const [source, setSource] = useState<Source | null>(null);
  // Settle on the first connected source once connections are known, and never
  // leave a source selected that the user has since disconnected.
  useEffect(() => {
    if (available.length === 0) {
      setSource(null);
      return;
    }
    setSource((current) =>
      current && available.some((info) => info.source === current)
        ? current
        : available[0].source,
    );
  }, [available]);
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
      // A stale access token would otherwise 401 the stream and show empty for
      // every source. Refresh once and reconnect with the new token.
      onUnauthorized: () => api.reauth(),
    });
    return () => handle.current?.cancel();
  }, [api]);

  const rows = useMemo(
    () => (source ? all.filter((row) => row.source === source) : []),
    [all, source],
  );
  const label = source ? LABELS[source] : '';
  // With nothing connected there is no count to report and no strip to show, so
  // the screen is just the "connect a source" prompt: a big "0 did not need you"
  // over an empty selector read as a broken screen rather than an empty one.
  const empty = available.length === 0;
  const title = empty ? 'Later' : `${all.length} did not need you`;

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas }}>
      <AnimatedScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{
          paddingTop: topInset(insets.top),
          paddingBottom: space.xl,
        }}
      >
        <ScreenHeader eyebrow={empty ? undefined : 'Last 30 days'} title={title} />

        {/* Icon-only when inactive, icon plus label when active, so the strip
            stays one line however many sources there are. */}
        {!empty ? (
        <View
          style={{
            flexDirection: 'row',
            gap: space.xs,
            paddingHorizontal: space.md,
            paddingTop: space.md,
          }}
        >
          {available.map((entry) => {
            const on = entry.source === source;
            return (
              <Pressable
                key={entry.source}
                onPress={() => {
                  haptics.select();
                  setSource(entry.source);
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
                <BrandMark source={entry.source} size={24} />
                {on ? (
                  // The hue lives in the border and the fill. As text on a
                  // tinted overlay it measured 3.6 in light mode, and a label
                  // that has to be legible cannot be the place the colour is
                  // carried.
                  <T role="label" tone="high">
                    {LABELS[entry.source]}
                  </T>
                ) : null}
              </Pressable>
            );
          })}
        </View>
        ) : null}

        {!empty ? (
          <SectionLabel
            label={label}
            tight
            // The header never claims a total it does not have yet. `count`
            // renders in the mono face, which is right for a figure and wrong
            // for a word, so the pending state is the figure's absence rather
            // than "counting..." typed out where the figure will go.
            count={loading ? null : `${rows.length} items`}
          />
        ) : null}

        {/* `source_ref` is a thread id, and a thread with two unread messages
            arrives twice, so the index keeps the key unique. */}
        {rows.map((row, index) => (
          <Row
            key={`${row.source_ref}-${index}`}
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
            // Opens the same detail sheet the feed uses, with the full content;
            // the external link is the sheet's Open button, not the row tap.
            glyph="chevron"
            onPress={() => onOpenRow(laterRowToFeedRow(row, index))}
          />
        ))}

        {!empty && loading ? (
          <View style={{ alignItems: 'center', gap: space.sm, paddingTop: space.xl }}>
            <ActivityIndicator color={c.hue.later} />
            {all.length > 0 ? (
              // Prose, in the prose face. `numeric` sets Geist Mono, which is
              // for machine values a reader scans in a column: a whole
              // sentence in it reads as console output rather than as the app
              // talking, and this line and the one below it are the same voice.
              <T role="secondary" tone="mid">
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

        {available.length === 0 ? (
          <Explain
            title="No sources connected"
            body="Connect a source in You, and anything from it that did not need you shows up here."
          />
        ) : !loading && !error && rows.length === 0 ? (
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
    </View>
  );
}
