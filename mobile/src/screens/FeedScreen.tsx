/**
 * To-dos: the queue, top to bottom.
 *
 * This used to be a full-screen deck swiped one card at a time, an action rail
 * stacked bottom-right the way Reels and Stories stack theirs. It read as a
 * place to consume rather than a queue to clear. It is now a vertical scroll of
 * bounded cards, the shape LinkedIn and Instagram use for their main feed:
 * several items visible at once, scanned top to bottom, each with its actions on
 * a bar beneath it.
 *
 * There is nothing above the list and nothing between the cards: no page title,
 * no section labels, no counts. The cards flow continuously, ordered most
 * pressing first, and each one carries its own tier as a coloured wash and a
 * chip. Colour means tier and only tier, and tapping a card opens the detail
 * sheet where the decision is made.
 */

import React, { useCallback, useMemo, useState } from 'react';
import { FlatList, RefreshControl, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { space, topInset, useTheme } from '../theme';
import { FeedCard } from '../components/FeedCard';
import { Clear, Skeleton } from '../components/states';
import type { FeedRow, Tier } from '../api/types';

const ORDER: Tier[] = ['urgent', 'today', 'can_wait', 'noise'];

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

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas }}>
      <FlatList
        data={ordered}
        keyExtractor={(row) => row.id}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{
          paddingTop: topInset(insets.top),
          paddingBottom: space.xl,
        }}
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
