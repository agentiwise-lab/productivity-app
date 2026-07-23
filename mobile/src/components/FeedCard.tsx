/**
 * The card. Plan 6.1 lists nine elements and calls none of them optional, so
 * none of them are conditional on space here either.
 *
 * The urgency treatment is a tinted ground and a left rail rather than a red
 * badge: on a screen where three or four things are urgent, a badge on each
 * stops meaning anything, while a change of ground still reads at a glance.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, space, radius, type } from '../theme';
import { ago, deadlineLabel } from '../lib/time';
import { BrandMark } from './BrandMark';
import { actionsFor } from '../lib/actions';
import type { FeedRow } from '../api/types';

const TAG_LABEL: Record<string, string> = {
  review: 'REVIEW',
  approve: 'APPROVE',
  reply: 'REPLY',
  assigned: 'ASSIGNED',
  comment: 'COMMENT',
  decide: 'DECIDE',
  rsvp: 'RSVP',
  alert: 'ALERT',
  fyi: 'FYI',
};

interface Props {
  row: FeedRow;
  onPress: (row: FeedRow) => void;
  onAction: (row: FeedRow, action: string) => void;
  /** Cards in the horizontal feed are fixed width; list rows are not. */
  width?: number;
}

export function FeedCard({ row, onPress, onAction, width }: Props) {
  const urgent = row.tier === 'urgent';
  const deadline = deadlineLabel(row.deadline);
  const [primary, secondary] = actionsFor(row);

  return (
    <Pressable
      onPress={() => onPress(row)}
      style={[
        styles.card,
        width ? { width } : undefined,
        urgent && styles.cardUrgent,
      ]}
    >
      {urgent && <View style={styles.rail} />}

      <View style={styles.head}>
        <BrandMark source={row.source} size={26} />
        <Text style={[styles.tag, urgent && styles.tagUrgent]}>
          {TAG_LABEL[row.type_tag] ?? row.type_tag.toUpperCase()}
        </Text>
        <View style={styles.spacer} />
        <Text style={[styles.time, urgent && styles.timeUrgent]}>
          {deadline ?? ago(row.occurred_at)}
        </Text>
      </View>

      <Text style={styles.title} numberOfLines={2}>
        {row.sender_name ? (
          <>
            <Text style={styles.sender}>{row.sender_name}</Text>
            <Text>{'  '}</Text>
          </>
        ) : null}
        {row.title}
      </Text>

      {/* The AI one-liner. While classification is pending there is nothing
          honest to say, so the row simply omits it rather than showing a
          placeholder that looks like a summary. */}
      {row.summary ? (
        <Text style={styles.summary} numberOfLines={1}>
          {row.summary}
        </Text>
      ) : null}

      <View style={styles.foot}>
        {row.context_chip ? (
          <View style={styles.chip}>
            <Text style={styles.chipText} numberOfLines={1}>
              {row.context_chip}
            </Text>
          </View>
        ) : null}
        <View style={styles.spacer} />
        <Pressable
          onPress={() => onAction(row, secondary.id)}
          style={styles.secondaryBtn}
          hitSlop={6}
        >
          <Text style={styles.secondaryText}>{secondary.label}</Text>
        </Pressable>
        <Pressable
          onPress={() => onAction(row, primary.id)}
          style={[styles.primaryBtn, urgent && styles.primaryBtnUrgent]}
          hitSlop={6}
        >
          <Text style={styles.primaryText}>{primary.label}</Text>
        </Pressable>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.line,
    padding: space.lg,
    gap: space.sm,
    overflow: 'hidden',
  },
  cardUrgent: {
    backgroundColor: colors.urgentSoft,
    borderColor: '#E7C6AE',
  },
  rail: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 3,
    backgroundColor: colors.urgent,
  },
  head: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  spacer: { flex: 1 },
  tag: {
    ...type.mono,
    color: colors.dim,
  },
  tagUrgent: { color: colors.urgent },
  time: { ...type.mono, color: colors.dim, letterSpacing: 0 },
  timeUrgent: { color: colors.urgent },
  title: { ...type.title, color: colors.fg },
  sender: { fontWeight: '700', color: colors.fg },
  summary: { ...type.small, color: colors.dim },
  foot: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  chip: {
    backgroundColor: colors.bg,
    borderRadius: radius.sm,
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    maxWidth: 140,
  },
  chipText: { ...type.small, fontSize: 11, color: colors.dim },
  secondaryBtn: {
    paddingHorizontal: space.md,
    paddingVertical: space.sm - 2,
    borderRadius: radius.sm,
  },
  secondaryText: { ...type.small, fontWeight: '600', color: colors.accent },
  primaryBtn: {
    backgroundColor: colors.accent,
    paddingHorizontal: space.md,
    paddingVertical: space.sm - 2,
    borderRadius: radius.sm,
  },
  primaryBtnUrgent: { backgroundColor: colors.urgent },
  primaryText: { ...type.small, fontWeight: '600', color: '#FFFFFF' },
});
