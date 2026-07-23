/**
 * Later: everything unactioned, every source, inside the 30-day window.
 *
 * This is what earns the right to hide things from Home. Nothing is deleted, it
 * is only not shouted about, and the user can always come here and see exactly
 * what was held back and why. A filter that discards silently is a filter
 * nobody trusts.
 *
 * Rows carry the reason they are here, and an empty bucket explains what would
 * land in it rather than saying "Nothing here" and stopping.
 */

import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type } from '../theme';
import { Header } from '../components/Chrome';
import { GroupHeader, ListRow } from '../components/ListRow';
import { EmptyBucket } from '../components/states';
import type { FeedRow, Tier } from '../api/types';

/**
 * Later holds what was set aside, not what is live. Anything still needing you
 * is on Home, and duplicating it here made the two screens disagree about what
 * the word "later" meant.
 */
type Bucket = 'noise' | 'snoozed';

const TABS: { id: Bucket; label: string }[] = [
  { id: 'noise', label: 'Held back' },
  { id: 'snoozed', label: 'Snoozed' },
];

const EMPTY: Record<Bucket, { title: string; explains: string; hint: string }> = {
  snoozed: {
    title: 'Nothing snoozed',
    explains:
      'Snooze an item from its card and it waits here until the time you chose, instead of sitting in your feed.',
    hint: 'Try Snooze on any card in Home.',
  },
  noise: {
    title: 'Nothing held back',
    explains:
      'Status updates, your own pull requests, bulk email and chatter you were not addressed in are filed here rather than shown on Home.',
    hint: 'Everything filtered out stays visible here, never deleted.',
  },
};

const TIER_ORDER: Tier[] = ['urgent', 'today', 'can_wait', 'noise'];

export function LaterScreen({
  rows,
  onOpen,
}: {
  rows: FeedRow[];
  onOpen: (row: FeedRow) => void;
}) {
  const [bucket, setBucket] = useState<Bucket>('noise');

  const shown = useMemo(() => {
    const now = Date.now();
    return rows.filter((row) => {
      const snoozed =
        row.snoozed_until !== null && new Date(row.snoozed_until).getTime() > now;
      if (bucket === 'snoozed') return snoozed;
      if (snoozed) return false;
      return row.tier === 'noise';
    });
  }, [rows, bucket]);

  const groups = useMemo(
    () =>
      TIER_ORDER.map((tier) => ({
        tier,
        rows: shown.filter((row) => row.tier === tier),
      })).filter((group) => group.rows.length > 0),
    [shown],
  );

  const counts = useMemo(() => {
    const now = Date.now();
    const snoozed = rows.filter(
      (r) => r.snoozed_until !== null && new Date(r.snoozed_until).getTime() > now,
    ).length;
    return {
      snoozed,
      noise: rows.filter((r) => r.tier === 'noise').length,
    };
  }, [rows]);

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Header title="Later" subtitle="30-day window" rightGlyph=" " />

      <View style={styles.tabs}>
        {TABS.map((tab) => {
          const active = tab.id === bucket;
          return (
            <Pressable
              key={tab.id}
              onPress={() => setBucket(tab.id)}
              style={[styles.tab, active && styles.tabActive]}
            >
              <Text style={[styles.tabText, active && styles.tabTextActive]}>
                {tab.label}
              </Text>
              <Text style={[styles.tabCount, active && styles.tabTextActive]}>
                {counts[tab.id]}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        {shown.length === 0 ? (
          <EmptyBucket {...EMPTY[bucket]} />
        ) : (
          groups.map((group) => (
            <View key={group.tier}>
              <GroupHeader tier={group.tier} count={group.rows.length} />
              {group.rows.map((row) => (
                <ListRow key={row.id} row={row} onPress={onOpen} />
              ))}
            </View>
          ))
        )}
        {shown.length > 0 ? (
          <Text style={styles.footnote}>Kept for 30 days, then removed.</Text>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  tabs: { flexDirection: 'row', gap: s(6), paddingHorizontal: s(13), paddingTop: s(10) },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: s(5),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(9),
    backgroundColor: colors.surface,
    paddingVertical: s(7),
  },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { ...type.chipLabel, color: colors.dim },
  tabCount: { fontFamily: 'Menlo', fontSize: s(9), color: colors.dim },
  tabTextActive: { color: colors.onAccent },
  body: { paddingBottom: s(30) },
  footnote: {
    ...type.rowSub,
    textAlign: 'center',
    paddingTop: s(16),
  },
});
