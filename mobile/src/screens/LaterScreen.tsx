/**
 * Later: everything unactioned across every source, inside the 30-day window.
 *
 * This is where Noise lives. That is the whole reason the app can afford to
 * hide things from Home: nothing is deleted, it is just not shouted about, and
 * the user can always come here and check what was held back. A filter that
 * silently discards is a filter nobody trusts.
 */

import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, SectionList, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, space, radius, type } from '../theme';
import { FeedCard } from '../components/FeedCard';
import type { FeedRow } from '../api/types';

type Bucket = 'needs_you' | 'noise' | 'snoozed';

const TABS: { id: Bucket; label: string }[] = [
  { id: 'needs_you', label: 'Needs you' },
  { id: 'snoozed', label: 'Snoozed' },
  { id: 'noise', label: 'Held back' },
];

interface Props {
  rows: FeedRow[];
  onOpen: (row: FeedRow) => void;
  onAction: (row: FeedRow, action: string) => void;
}

export function LaterScreen({ rows, onOpen, onAction }: Props) {
  const [bucket, setBucket] = useState<Bucket>('needs_you');

  const shown = useMemo(() => {
    const now = Date.now();
    return rows.filter((row) => {
      const snoozed =
        row.snoozed_until !== null && new Date(row.snoozed_until).getTime() > now;
      if (bucket === 'snoozed') return snoozed;
      if (snoozed) return false;
      return bucket === 'noise' ? row.tier === 'noise' : row.tier !== 'noise';
    });
  }, [rows, bucket]);

  const sections = useMemo(() => groupByDay(shown), [shown]);

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Text style={styles.title}>Later</Text>

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
            </Pressable>
          );
        })}
      </View>

      <SectionList
        sections={sections}
        keyExtractor={(row) => row.id}
        contentContainerStyle={styles.body}
        stickySectionHeadersEnabled={false}
        renderSectionHeader={({ section }) => (
          <Text style={styles.day}>{section.title}</Text>
        )}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <FeedCard row={item} onPress={onOpen} onAction={onAction} />
          </View>
        )}
        ListEmptyComponent={<Text style={styles.quiet}>Nothing here.</Text>}
        ListFooterComponent={
          shown.length > 0 ? (
            <Text style={styles.footer}>
              Items are kept for 30 days, then removed.
            </Text>
          ) : null
        }
      />
    </SafeAreaView>
  );
}

function groupByDay(rows: FeedRow[]) {
  const buckets = new Map<string, FeedRow[]>();
  rows.forEach((row) => {
    const key = dayLabel(row.occurred_at);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(row);
  });
  return Array.from(buckets, ([title, data]) => ({ title, data }));
}

function dayLabel(iso: string | null): string {
  if (!iso) return 'Undated';
  const date = new Date(iso);
  const today = new Date();
  const days = Math.floor(
    (new Date(today.toDateString()).getTime() - new Date(date.toDateString()).getTime()) /
      86400000,
  );
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  title: { ...type.h1, color: colors.fg, paddingHorizontal: space.lg, paddingBottom: space.sm },
  tabs: {
    flexDirection: 'row',
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingBottom: space.md,
  },
  tab: {
    paddingHorizontal: space.md,
    paddingVertical: space.sm - 2,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
  },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { ...type.small, fontWeight: '600', color: colors.dim },
  tabTextActive: { color: '#FFFFFF' },
  body: { paddingBottom: space.xxl },
  day: {
    ...type.small,
    fontWeight: '600',
    color: colors.dim,
    paddingHorizontal: space.lg,
    paddingTop: space.lg,
    paddingBottom: space.sm,
  },
  row: { paddingHorizontal: space.lg, paddingBottom: space.md },
  quiet: { ...type.small, color: colors.dim, padding: space.lg },
  footer: {
    ...type.small,
    fontSize: 11,
    color: colors.dim,
    textAlign: 'center',
    paddingTop: space.lg,
  },
});
