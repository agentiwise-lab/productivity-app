/**
 * To-dos: the queue, top to bottom.
 *
 * A vertical scroll of bounded cards, ordered most pressing first, each with its
 * tier as a coloured wash and chip. Two filter strips sit above the list — one
 * for the platform (GitHub, Slack, …) and one for the tier (Urgent / By EOD /
 * Can wait / Later) — mirroring the Later tab's source selector, so the queue can
 * be narrowed the same way from either screen. Colour means tier and only tier.
 */

import React, { useCallback, useMemo, useState } from 'react';
import { FlatList, Pressable, RefreshControl, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  CATEGORY_LABEL,
  CATEGORY_OF_TIER,
  radius,
  size,
  space,
  topInset,
  useTheme,
} from '../theme';
import { BrandMark } from '../components/BrandMark';
import { FeedCard } from '../components/FeedCard';
import { T } from '../components/ui';
import { Clear, Skeleton } from '../components/states';
import type { FeedRow, Source, Tier } from '../api/types';

const ORDER: Tier[] = ['urgent', 'today', 'can_wait', 'noise'];

const SOURCE_LABEL: Record<Source, string> = {
  github: 'GitHub',
  slack: 'Slack',
  linear: 'Linear',
  calendar: 'Calendar',
  gmail: 'Gmail',
  google_docs: 'Drive',
};

export function FeedScreen({
  rows,
  loading,
  onAction,
  onOpen,
  onRefresh,
}: {
  rows: FeedRow[];
  loading: boolean;
  onAction: (row: FeedRow, action: string) => void;
  onOpen: (row: FeedRow, compose?: boolean) => void;
  /** Pull-to-refresh: the manual heavy sync, parity with Day. */
  onRefresh?: () => Promise<void> | void;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const [refreshing, setRefreshing] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<Source | null>(null);
  const [tierFilter, setTierFilter] = useState<Tier | null>(null);

  const pull = useCallback(async () => {
    if (!onRefresh) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  }, [onRefresh]);

  // One continuous stream, ordered by tier then priority. The tier is never
  // spelled out as a heading: the card's wash and chip already carry it.
  const ordered = useMemo(
    () =>
      [...rows]
        .filter((row) => row.status !== 'acted' && row.status !== 'dismissed')
        .sort(
          (a, b) =>
            ORDER.indexOf(a.tier) - ORDER.indexOf(b.tier) ||
            b.priority_score - a.priority_score,
        ),
    [rows],
  );

  // Which platforms and tiers actually have items, so a filter never points at
  // an empty set. Both keep the queue's own order.
  const platforms = useMemo(() => {
    const seen = new Set<Source>();
    for (const row of ordered) seen.add(row.source);
    return (Object.keys(SOURCE_LABEL) as Source[]).filter((s) => seen.has(s));
  }, [ordered]);

  const tiers = useMemo(() => {
    const seen = new Set<Tier>();
    for (const row of ordered) seen.add(row.tier);
    return ORDER.filter((t) => seen.has(t));
  }, [ordered]);

  const filtered = useMemo(
    () =>
      ordered.filter(
        (row) =>
          (!sourceFilter || row.source === sourceFilter) &&
          (!tierFilter || row.tier === tierFilter),
      ),
    [ordered, sourceFilter, tierFilter],
  );

  if (loading && ordered.length === 0) {
    return (
      <View style={{ flex: 1, backgroundColor: c.canvas, justifyContent: 'center' }}>
        <Skeleton rows={4} />
      </View>
    );
  }

  if (ordered.length === 0) {
    return (
      <View style={{ flex: 1, backgroundColor: c.canvas, justifyContent: 'center' }}>
        <Clear heldBack={rows.length - ordered.length} />
      </View>
    );
  }

  const chip = (opts: {
    key: string;
    on: boolean;
    hue: string;
    onPress: () => void;
    icon?: React.ReactNode;
    label?: string;
  }) => (
    <Pressable
      key={opts.key}
      onPress={opts.onPress}
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
        opts.on ? { borderColor: opts.hue, backgroundColor: c.overlay } : null,
      ]}
    >
      {opts.icon}
      {opts.label ? (
        <T role="label" tone={opts.on ? 'high' : 'mid'}>
          {opts.label}
        </T>
      ) : null}
    </Pressable>
  );

  const strips = (
    <View style={{ gap: space.xs, paddingBottom: space.sm }}>
      {/* Platform: an "All" chip, then a BrandMark per source present. */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: space.xs, paddingHorizontal: space.md }}
      >
        {chip({
          key: 'src-all',
          on: sourceFilter === null,
          hue: c.hue.later,
          onPress: () => setSourceFilter(null),
          label: 'All',
        })}
        {platforms.map((s) =>
          chip({
            key: `src-${s}`,
            on: sourceFilter === s,
            hue: c.hue.later,
            onPress: () => setSourceFilter((cur) => (cur === s ? null : s)),
            icon: <BrandMark source={s} size={24} />,
            label: sourceFilter === s ? SOURCE_LABEL[s] : undefined,
          }),
        )}
      </ScrollView>
      {/* Tier: an "All" chip, then Urgent / By EOD / Can wait / Later. */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: space.xs, paddingHorizontal: space.md }}
      >
        {chip({
          key: 'tier-all',
          on: tierFilter === null,
          hue: c.hue.later,
          onPress: () => setTierFilter(null),
          label: 'All',
        })}
        {tiers.map((t) => {
          const category = CATEGORY_OF_TIER[t];
          return chip({
            key: `tier-${t}`,
            on: tierFilter === t,
            hue: c.hue[category],
            onPress: () => setTierFilter((cur) => (cur === t ? null : t)),
            label: CATEGORY_LABEL[category],
          });
        })}
      </ScrollView>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas, paddingTop: topInset(insets.top) }}>
      {strips}
      <FlatList
        data={filtered}
        keyExtractor={(row) => row.id}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingBottom: space.xl }}
        renderItem={({ item }) => (
          <FeedCard row={item} onAction={onAction} onOpen={onOpen} />
        )}
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={refreshing}
              onRefresh={pull}
              tintColor={c.low}
            />
          ) : undefined
        }
      />
    </View>
  );
}
