/**
 * Home, as approved in docs/mockups/home.html.
 *
 * Four bands, in this order and for this reason: the ruler says how much day is
 * left, the counts say how much of it is spoken for, the card feed is the thing
 * you act on now, and the list is everything else. Scrolling collapses the
 * ruler to a single line, because once you are reading the feed the shape of
 * your day is context, not content.
 *
 * The card feed and the list are the same rows in the same order. They read
 * from one ranked array so the two can never disagree about what matters most.
 */

import React, { useCallback, useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, space, radius, type, tierLabel } from '../theme';
import { FeedCard } from '../components/FeedCard';
import { YourDay, type Meeting } from '../components/YourDay';
import { Clear, NothingConnected, Skeleton, StaleBanner } from '../components/states';
import type { FeedRow, Tier } from '../api/types';

const FILTERS: Tier[] = ['urgent', 'today', 'can_wait'];
const COLLAPSE_AT = 56;

interface Props {
  rows: FeedRow[];
  loading: boolean;
  stale: boolean;
  fetchedAt: Date | null;
  meetings: Meeting[];
  connected: boolean;
  onRefresh: () => Promise<void>;
  onOpen: (row: FeedRow) => void;
  onAction: (row: FeedRow, action: string) => void;
  onConnect: () => void;
}

export function HomeScreen({
  rows,
  loading,
  stale,
  fetchedAt,
  meetings,
  connected,
  onRefresh,
  onOpen,
  onAction,
  onConnect,
}: Props) {
  const { width } = useWindowDimensions();
  const [filter, setFilter] = useState<Tier | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Noise never reaches Home. It is not filtered in the UI as a preference;
  // it is simply not what this screen is for.
  const live = useMemo(() => rows.filter((row) => row.tier !== 'noise'), [rows]);
  const heldBack = rows.length - live.length;

  const counts = useMemo(() => {
    const tally: Record<string, number> = { urgent: 0, today: 0, can_wait: 0 };
    live.forEach((row) => (tally[row.tier] += 1));
    return tally;
  }, [live]);

  const shown = filter ? live.filter((row) => row.tier === filter) : live;
  const dueToday = live.filter((row) => row.deadline !== null).length;

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  }, [onRefresh]);

  if (loading && rows.length === 0) {
    return (
      <SafeAreaView style={styles.screen} edges={['top']}>
        <Header />
        <Skeleton />
      </SafeAreaView>
    );
  }

  if (!connected) {
    return (
      <SafeAreaView style={styles.screen} edges={['top']}>
        <Header />
        <NothingConnected onConnect={onConnect} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Header />
      {collapsed ? (
        <YourDay meetings={meetings} dueToday={dueToday} compact />
      ) : null}

      <ScrollView
        stickyHeaderIndices={[]}
        scrollEventThrottle={16}
        onScroll={(event) =>
          setCollapsed(event.nativeEvent.contentOffset.y > COLLAPSE_AT)
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={refresh}
            tintColor={colors.accent}
          />
        }
        contentContainerStyle={styles.scrollBody}
      >
        {!collapsed ? (
          <YourDay meetings={meetings} dueToday={dueToday} />
        ) : null}

        {stale ? <StaleBanner fetchedAt={fetchedAt} /> : null}

        <View style={styles.counts}>
          {FILTERS.map((tier) => {
            const active = filter === tier;
            return (
              <Pressable
                key={tier}
                onPress={() => setFilter(active ? null : tier)}
                style={[
                  styles.count,
                  active && styles.countActive,
                  tier === 'urgent' && counts[tier] > 0 && styles.countUrgent,
                  tier === 'urgent' && active && styles.countUrgentActive,
                ]}
              >
                <Text
                  style={[
                    styles.countValue,
                    tier === 'urgent' && counts[tier] > 0 && styles.countValueUrgent,
                    active && styles.countTextActive,
                  ]}
                >
                  {counts[tier]}
                </Text>
                <Text style={[styles.countLabel, active && styles.countTextActive]}>
                  {tierLabel[tier]}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {shown.length === 0 ? (
          <Clear heldBack={heldBack} />
        ) : (
          <>
            <FlatList
              horizontal
              data={shown.slice(0, 8)}
              keyExtractor={(row) => row.id}
              showsHorizontalScrollIndicator={false}
              snapToInterval={width * 0.82 + space.md}
              decelerationRate="fast"
              contentContainerStyle={styles.cardStrip}
              renderItem={({ item }) => (
                <FeedCard
                  row={item}
                  width={width * 0.82}
                  onPress={onOpen}
                  onAction={onAction}
                />
              )}
            />

            <Text style={styles.sectionTitle}>All items</Text>
            <View style={styles.list}>
              {shown.map((row) => (
                <ListRow key={row.id} row={row} onPress={onOpen} onAction={onAction} />
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Header() {
  return (
    <View style={styles.header}>
      <Text style={styles.headerTitle}>Today</Text>
      <View style={styles.spacer} />
    </View>
  );
}

function ListRow({
  row,
  onPress,
  onAction,
}: {
  row: FeedRow;
  onPress: (row: FeedRow) => void;
  onAction: (row: FeedRow, action: string) => void;
}) {
  return <FeedCard row={row} onPress={onPress} onAction={onAction} />;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: space.lg,
    // SafeAreaView contributes the notch inset on a device but nothing on
    // web, where the title would otherwise sit against the very top edge.
    paddingTop: space.sm,
    paddingBottom: space.sm,
  },
  headerTitle: { ...type.h1, color: colors.fg },
  spacer: { flex: 1 },
  scrollBody: { paddingBottom: space.xxl },
  counts: {
    flexDirection: 'row',
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingTop: space.lg,
  },
  count: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.md,
    paddingVertical: space.md,
    paddingHorizontal: space.md,
  },
  countActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  countUrgent: { backgroundColor: colors.urgentSoft, borderColor: '#E7C6AE' },
  countUrgentActive: { backgroundColor: colors.urgent, borderColor: colors.urgent },
  countValue: { ...type.h1, fontSize: 24, color: colors.fg },
  countValueUrgent: { color: colors.urgent },
  countLabel: { ...type.small, fontSize: 11, color: colors.dim },
  countTextActive: { color: '#FFFFFF' },
  cardStrip: { paddingHorizontal: space.lg, paddingTop: space.lg, gap: space.md },
  sectionTitle: {
    ...type.h2,
    color: colors.fg,
    paddingHorizontal: space.lg,
    paddingTop: space.xl,
    paddingBottom: space.sm,
  },
  list: { paddingHorizontal: space.lg, gap: space.md },
});
