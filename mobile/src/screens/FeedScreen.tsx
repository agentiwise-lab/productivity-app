/**
 * To-dos: the queue, top to bottom.
 *
 * A vertical scroll of bounded cards, ordered most pressing first, each with its
 * tier as a coloured wash and chip. One compact, icon-only filter row sits above
 * the list: the connected platforms (their marks) then the tier glyphs in their
 * category hues. No labels, no "All" chip — tap to filter, tap again to clear,
 * nothing selected means everything. Colour means tier and only tier.
 */

import React, { useCallback, useMemo, useState } from 'react';
import { FlatList, Pressable, RefreshControl, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { CATEGORY_OF_TIER, radius, space, topInset, useTheme } from '../theme';
import { BrandMark } from '../components/BrandMark';
import { CATEGORY_GLYPH, Icon } from '../components/Icon';
import { FeedCard } from '../components/FeedCard';
import { Clear, Skeleton } from '../components/states';
import type { FeedRow, Source, Tier } from '../api/types';

const ORDER: Tier[] = ['urgent', 'today', 'can_wait', 'noise'];
const SOURCE_ORDER: Source[] = [
  'github',
  'slack',
  'linear',
  'calendar',
  'gmail',
  'google_docs',
];

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

  // One continuous stream, ordered by tier then priority.
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

  // Only platforms and tiers actually present, so a filter never lands on empty.
  const platforms = useMemo(() => {
    const seen = new Set<Source>(ordered.map((r) => r.source));
    return SOURCE_ORDER.filter((s) => seen.has(s));
  }, [ordered]);

  const tiers = useMemo(() => {
    const seen = new Set<Tier>(ordered.map((r) => r.tier));
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

  const iconBtn = (key: string, on: boolean, ring: string, onPress: () => void, glyph: React.ReactNode) => (
    <Pressable
      key={key}
      onPress={onPress}
      style={{
        width: 30,
        height: 30,
        borderRadius: radius.sm,
        borderWidth: 1,
        alignItems: 'center',
        justifyContent: 'center',
        // Every option carries a hairline border (like the Later selector);
        // selection colours the border and tints the fill.
        borderColor: on ? ring : c.hairline,
        backgroundColor: on ? c.overlay : c.surface,
      }}
    >
      {glyph}
    </Pressable>
  );

  // A fixed-width (equal-half) bordered box whose contents scroll horizontally
  // within it, so the two selectors never resize each other.
  const selectorBox = (children: React.ReactNode) => (
    <View
      style={{
        width: '42%',
        height: 38,
        borderRadius: radius.md,
        borderWidth: 1,
        borderColor: c.hairline,
        backgroundColor: c.surface,
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: 4, paddingHorizontal: 4, alignItems: 'center' }}
      >
        {children}
      </ScrollView>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas, paddingTop: topInset(insets.top) }}>
      {/* Two fixed-width selectors side by side: platforms (left) and tiers
          (right), each a bordered box that scrolls horizontally within its half
          so neither ever resizes the other. */}
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          paddingHorizontal: space.md,
          paddingTop: space.xxs,
          paddingBottom: space.sm,
        }}
      >
        {selectorBox(
          platforms.map((s) =>
            iconBtn(
              `src-${s}`,
              sourceFilter === s,
              c.hue.later,
              () => setSourceFilter((cur) => (cur === s ? null : s)),
              <BrandMark source={s} size={20} />,
            ),
          ),
        )}
        {selectorBox(
          tiers.map((t) => {
            const category = CATEGORY_OF_TIER[t];
            // Later wears a watch, matching the Later tab's clock glyph.
            const glyph =
              t === 'noise' ? 'clock' : CATEGORY_GLYPH[category];
            return iconBtn(
              `tier-${t}`,
              tierFilter === t,
              c.hue[category],
              () => setTierFilter((cur) => (cur === t ? null : t)),
              <Icon name={glyph} size={20} color={c.hue[category]} />,
            );
          }),
        )}
      </View>
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
            <RefreshControl refreshing={refreshing} onRefresh={pull} tintColor={c.low} />
          ) : undefined
        }
      />
    </View>
  );
}
