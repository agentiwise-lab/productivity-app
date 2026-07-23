/**
 * Home, rebuilt against docs/mockups/home.html rather than from memory.
 *
 * Four bands in this order: the ruler says what the day looks like, the three
 * counts say how much is waiting and double as filters, the card feed is the
 * queue you swipe through acting as you go, and the grouped list underneath
 * shows every tier so the filter never hides anything.
 *
 * The cards and the list read one ranked array, so they cannot disagree. On
 * scroll the ruler collapses to the sticky line, because once you are in the
 * feed the shape of your day is context rather than content.
 */

import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type, tierLabel } from '../theme';
import { Header, StickyDay } from '../components/Chrome';
import { YourDayCard, type Meeting } from '../components/YourDayCard';
import { FeedCard, Dots, CARD_WIDTH, CARD_GAP } from '../components/FeedCard';
import { GroupHeader, ListRow, SectionDivider } from '../components/ListRow';
import { Clear, NothingConnected, Skeleton, StaleBanner } from '../components/states';
import type { FeedRow, Tier } from '../api/types';

const TIERS: Tier[] = ['urgent', 'today', 'can_wait'];

/** A mark per tier, so the chips read at a glance rather than as three numbers. */
const TIER_GLYPH: Record<Tier, string> = {
  urgent: '!',
  today: '◐',
  can_wait: '○',
  noise: '·',
};

const TIER_TINT: Record<Tier, string> = {
  urgent: colors.urgentSoft,
  today: colors.accentSoft,
  can_wait: colors.line,
  noise: colors.line,
};
const COLLAPSE_AT = s(70);

interface Props {
  rows: FeedRow[];
  loading: boolean;
  stale: boolean;
  fetchedAt: Date | null;
  meetings: Meeting[];
  connectedCount: number;
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
  connectedCount,
  onRefresh,
  onOpen,
  onAction,
  onConnect,
}: Props) {
  const [filter, setFilter] = useState<Tier | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [card, setCard] = useState(0);
  const now = useRef(new Date()).current;

  // Noise never reaches Home. Not a preference: it is what the screen is for.
  const live = useMemo(() => rows.filter((row) => row.tier !== 'noise'), [rows]);
  const heldBack = rows.length - live.length;

  const counts = useMemo(() => {
    const tally: Record<Tier, number> = { urgent: 0, today: 0, can_wait: 0, noise: 0 };
    live.forEach((row) => (tally[row.tier] += 1));
    return tally;
  }, [live]);

  const shown = filter ? live.filter((row) => row.tier === filter) : live;

  const groups = useMemo(
    () =>
      TIERS.map((tier) => ({
        tier,
        rows: shown.filter((row) => row.tier === tier),
      })).filter((group) => group.rows.length > 0),
    [shown],
  );

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  }, [onRefresh]);

  const next = meetings.find((meeting) => meeting.end > now);
  const dateLabel = now
    .toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
    .replace(',', '');

  if (loading && rows.length === 0) {
    return (
      <SafeAreaView style={styles.screen} edges={['top']}>
        <Header title="Today" subtitle={dateLabel} />
        <Skeleton />
      </SafeAreaView>
    );
  }

  if (connectedCount === 0) {
    return (
      <SafeAreaView style={styles.screen} edges={['top']}>
        <Header title="Today" subtitle={dateLabel} />
        <NothingConnected onConnect={onConnect} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Header title="Today" subtitle={dateLabel} />
      {collapsed && next ? (
        <StickyDay
          time={`${String(next.start.getHours()).padStart(2, '0')}:${String(
            next.start.getMinutes(),
          ).padStart(2, '0')}`}
          label={next.title}
          free="today"
        />
      ) : null}

      <ScrollView
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
        contentContainerStyle={styles.body}
      >
        <YourDayCard meetings={meetings} now={now} />

        {stale ? <StaleBanner fetchedAt={fetchedAt} /> : null}

        {/* Only selection highlights. Colouring Urgent permanently meant it
            looked chosen at all times, so tapping the others read as two
            filters being active at once. */}
        <View style={styles.chips}>
          {TIERS.map((tier) => {
            const selected = filter === tier;
            return (
              <Pressable
                key={tier}
                onPress={() => setFilter(selected ? null : tier)}
                style={[
                  styles.chip,
                  selected && (tier === 'urgent' ? styles.chipOnUrgent : styles.chipOn),
                ]}
              >
                {/* Mark and count share the top line; the label owns the full
                    width beneath it. Side by side, a two-digit count and a
                    word like "Can wait" fought for the same few points. */}
                <View style={styles.chipTop}>
                  <View
                    style={[
                      styles.chipGlyph,
                      { backgroundColor: TIER_TINT[tier] },
                      selected && styles.chipGlyphOn,
                    ]}
                  >
                    <Text style={styles.chipGlyphText}>{TIER_GLYPH[tier]}</Text>
                  </View>
                  <Text style={[styles.chipNumber, selected && styles.chipTextOn]}>
                    {counts[tier]}
                  </Text>
                </View>
                <Text
                  style={[styles.chipLabel, selected && styles.chipTextOn]}
                  numberOfLines={1}
                >
                  {tierLabel[tier]}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {shown.length === 0 ? (
          <Clear heldBack={heldBack} filtered={filter !== null} />
        ) : (
          <>
            <View style={styles.feedWrap}>
              <FlatList
                horizontal
                data={shown.slice(0, 10)}
                keyExtractor={(row) => row.id}
                showsHorizontalScrollIndicator={false}
                snapToInterval={CARD_WIDTH + CARD_GAP}
                decelerationRate="fast"
                contentContainerStyle={styles.feed}
                onScroll={(event) =>
                  setCard(
                    Math.round(
                      event.nativeEvent.contentOffset.x / (CARD_WIDTH + CARD_GAP),
                    ),
                  )
                }
                scrollEventThrottle={16}
                renderItem={({ item, index }) => (
                  <FeedCard
                    row={item}
                    dimmed={index !== card}
                    onPress={onOpen}
                    onAction={onAction}
                  />
                )}
              />
            </View>
            <Dots count={Math.min(shown.length, 10)} active={card} />

            <SectionDivider label="All items" />
            {groups.map((group) => (
              <View key={group.tier}>
                <GroupHeader tier={group.tier} count={group.rows.length} />
                {group.rows.map((row) => (
                  <ListRow key={row.id} row={row} onPress={onOpen} />
                ))}
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  body: { paddingBottom: s(30) },
  chips: { flexDirection: 'row', gap: s(6), paddingHorizontal: s(13), paddingTop: s(11) },
  chip: {
    flex: 1,
    gap: s(5),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(10),
    backgroundColor: colors.surface,
    paddingVertical: s(7),
    paddingHorizontal: s(7),
  },
  chipOn: { borderColor: colors.accent, backgroundColor: colors.accentSoft },
  chipOnUrgent: { borderColor: colors.urgent, backgroundColor: colors.urgentSoft },
  chipGlyph: {
    width: s(20),
    height: s(20),
    borderRadius: s(6),
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipGlyphOn: { backgroundColor: 'rgba(255,255,255,0.65)' },
  chipGlyphText: { fontSize: s(10), fontWeight: '700', color: colors.fg },
  chipTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  chipNumber: { ...type.chipNumber, fontSize: s(15), color: colors.fg },
  chipLabel: { ...type.chipLabel, color: colors.dim, width: '100%' },
  chipTextOn: { color: colors.accent },
  feedWrap: { paddingTop: s(9) },
  feed: { paddingHorizontal: s(13), gap: CARD_GAP },
});
