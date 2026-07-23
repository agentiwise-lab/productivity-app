/**
 * The states plan 6.4 requires. Each is a moment where an unconsidered screen
 * actively misleads: an empty feed reads as "nothing needs you" whether the
 * truth is that you are clear, that nothing is connected, or that we could not
 * ask. None of these say "Nothing here" and stop. Every one of them names what
 * would appear and what to do about it.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, s, type } from '../theme';
import { clockTime } from '../lib/time';

export function Skeleton() {
  return (
    <View style={styles.pad}>
      {[0, 1, 2].map((n) => (
        <View key={n} style={styles.skeletonCard}>
          <View style={[styles.bar, { width: '32%' }]} />
          <View style={[styles.bar, { width: '86%', height: s(11) }]} />
          <View style={[styles.bar, { width: '54%' }]} />
        </View>
      ))}
    </View>
  );
}

export function Clear({
  heldBack,
  filtered = false,
}: {
  heldBack: number;
  filtered?: boolean;
}) {
  return (
    <View style={styles.block}>
      <Text style={styles.blockTitle}>
        {filtered ? 'Nothing in this category' : "You're clear for today"}
      </Text>
      <Text style={styles.blockBody}>
        {heldBack > 0
          ? `${heldBack} ${heldBack === 1 ? 'item was' : 'items were'} held back as noise. They are in Later under Held back.`
          : 'Nothing across your sources is waiting on you.'}
      </Text>
    </View>
  );
}

export function NothingConnected({ onConnect }: { onConnect: () => void }) {
  return (
    <View style={styles.centre}>
      <Text style={styles.blockTitle}>Connect your first tool</Text>
      <Text style={styles.blockBody}>
        Your feed is built from GitHub, Slack, Calendar, Linear, Gmail and Docs.
        Connect one to see what needs you.
      </Text>
      <Pressable onPress={onConnect} style={styles.cta}>
        <Text style={styles.ctaText}>Open Sources</Text>
      </Pressable>
    </View>
  );
}

/**
 * An empty Later still has to be useful. It names the bucket, says what would
 * land there, and points at the thing worth doing instead.
 */
export function EmptyBucket({
  title,
  explains,
  hint,
}: {
  title: string;
  explains: string;
  hint?: string;
}) {
  return (
    <View style={styles.block}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.blockBody}>{explains}</Text>
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

export function StaleBanner({ fetchedAt }: { fetchedAt: Date | null }) {
  return (
    <View style={styles.banner}>
      <Text style={styles.bannerText}>
        Can't reach the backend. Showing what we had
        {fetchedAt ? ` from ${clockTime(fetchedAt)}` : ''}.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pad: { padding: s(13), gap: s(9) },
  block: { paddingHorizontal: s(20), paddingTop: s(26), gap: s(6) },
  centre: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: s(24), gap: s(6) },
  blockTitle: { fontSize: s(15), fontWeight: '600', color: colors.fg },
  emptyTitle: { ...type.groupLabel, color: colors.fg },
  blockBody: { ...type.why },
  hint: { ...type.rowSub, color: colors.accent, marginTop: s(2) },
  cta: {
    marginTop: s(10),
    backgroundColor: colors.accent,
    paddingHorizontal: s(20),
    paddingVertical: s(9),
    borderRadius: s(9),
  },
  ctaText: { ...type.button, color: colors.onAccent, fontWeight: '600' },
  skeletonCard: {
    backgroundColor: colors.surface,
    borderRadius: s(14),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    padding: s(12),
    gap: s(8),
  },
  bar: { height: s(8), borderRadius: s(4), backgroundColor: colors.line },
  banner: {
    marginHorizontal: s(13),
    marginTop: s(9),
    backgroundColor: colors.accentSoft,
    borderRadius: s(9),
    paddingHorizontal: s(10),
    paddingVertical: s(7),
  },
  bannerText: { ...type.rowSub, color: colors.accent },
});
