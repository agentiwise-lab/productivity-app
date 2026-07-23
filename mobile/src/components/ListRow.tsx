/**
 * The grouped list under the card feed, matching .lsthd and .row.
 *
 * This is the half of Home that stops the filter from hiding anything: the
 * cards are the queue you work, the list is the whole picture, and every tier
 * is present in order whether or not it is filtered above. Each group carries a
 * coloured pip and a count, so the shape of the day is readable without
 * counting rows.
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
  return (
    <Pressable onPress={() => onPress(row)} style={styles.row}>
      <BrandMark source={row.source} size={s(24)} radius={s(7)} />
      <View style={styles.rowBody}>
        <Text style={styles.rowTitle} numberOfLines={2}>
          {row.title}
        </Text>
        {/* The reason this row exists at all. Without it a list of titles is
            just an inbox, which is the thing this product replaces. */}
        {row.summary ? (
          <Text style={styles.rowSub} numberOfLines={1}>
            {row.summary}
          </Text>
        ) : null}
      </View>
      <Text style={styles.rowMeta}>{meta}</Text>
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
    paddingTop: s(12),
    paddingBottom: s(5),
  },
  pip: { width: s(6), height: s(6), borderRadius: s(3) },
  groupLabel: { ...type.groupLabel, color: colors.fg },
  groupCount: { ...type.groupCount, marginLeft: 'auto' },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: s(9),
    paddingHorizontal: s(16),
    paddingTop: s(8),
    paddingBottom: s(9),
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
  },
  rowBody: { flex: 1 },
  rowTitle: { ...type.rowTitle, color: colors.fg, marginBottom: s(3) },
  rowSub: { ...type.rowSub },
  rowMeta: { ...type.ago, marginTop: s(2) },
  divider: {
    ...type.divider,
    paddingHorizontal: s(16),
    paddingTop: s(12),
    paddingBottom: s(2),
  },
});
