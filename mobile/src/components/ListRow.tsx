/**
 * The grouped list under the card feed, and the same row shape everywhere it
 * appears: Home, Later, and a source dashboard.
 *
 * Each row is a bordered card with its own padding rather than a line in a
 * table, so the list reads as a set of things rather than a grid. The one shape
 * is reused deliberately: three screens listing feed items in three different
 * styles is what made the app feel unfinished.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, s, type, pipColor, tierLabel } from '../theme';
import { ago, deadlineLabel } from '../lib/time';
import { BrandMark } from './BrandMark';
import type { FeedRow, Tier } from '../api/types';

export function GroupHeader({ tier, count }: { tier: Tier; count: number }) {
  return (
    <View style={styles.groupHeader}>
      <View style={[styles.pip, { backgroundColor: pipColor[tier] }]} />
      <Text style={styles.groupLabel}>{tierLabel[tier]}</Text>
      <Text style={styles.groupCount}>{count}</Text>
    </View>
  );
}

export function ListRow({
  row,
  onPress,
}: {
  row: FeedRow;
  onPress: (row: FeedRow) => void;
}) {
  const meta = deadlineLabel(row.deadline) ?? ago(row.occurred_at);
  const urgent = row.tier === 'urgent';
  return (
    <Pressable
      onPress={() => onPress(row)}
      style={({ pressed }) => [
        styles.row,
        urgent && styles.rowUrgent,
        pressed && styles.rowPressed,
      ]}
    >
      <BrandMark source={row.source} size={s(24)} radius={s(7)} />
      <View style={styles.rowBody}>
        <Text style={styles.rowTitle} numberOfLines={1} ellipsizeMode="tail">
          {row.sender_name ? `${row.sender_name}: ` : ''}
          {row.title}
        </Text>
        {/* Why this row exists. Without it a list of titles is just an inbox,
            which is the thing this product replaces. */}
        {row.summary ? (
          <Text style={styles.rowSub} numberOfLines={1} ellipsizeMode="tail">
            {row.summary}
          </Text>
        ) : null}
      </View>
      <Text style={[styles.rowMeta, urgent && styles.rowMetaUrgent]}>{meta}</Text>
    </Pressable>
  );
}

export function SectionDivider({ label }: { label: string }) {
  return <Text style={styles.divider}>{label}</Text>;
}

const styles = StyleSheet.create({
  groupHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(7),
    paddingHorizontal: s(16),
    paddingTop: s(14),
    paddingBottom: s(6),
  },
  pip: { width: s(7), height: s(7), borderRadius: s(3.5) },
  groupLabel: { ...type.groupLabel, color: colors.fg },
  groupCount: { ...type.groupCount, marginLeft: 'auto' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(10),
    marginHorizontal: s(13),
    marginBottom: s(7),
    paddingHorizontal: s(12),
    paddingVertical: s(11),
    backgroundColor: colors.surface,
    borderRadius: s(12),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  rowUrgent: { borderColor: '#E7C6AE', backgroundColor: colors.urgentSoft },
  rowPressed: { opacity: 0.6 },
  rowBody: { flex: 1, gap: s(2) },
  rowTitle: { ...type.rowTitle, fontWeight: '600', color: colors.fg },
  rowSub: { ...type.rowSub },
  rowMeta: { ...type.ago },
  rowMetaUrgent: { color: colors.urgent },
  divider: {
    ...type.divider,
    paddingHorizontal: s(16),
    paddingTop: s(16),
    paddingBottom: s(6),
  },
});
