/**
 * The states plan 6.4 says must exist. The mockups only ever showed the happy
 * path, and each of these is a moment where an unconsidered screen actively
 * misleads: an empty feed reads as "nothing needs you" whether the truth is
 * that you are clear, that nothing is connected yet, or that we could not ask.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { colors, space, radius, type } from '../theme';
import { clockTime } from '../lib/time';

export function Skeleton() {
  return (
    <View style={styles.pad}>
      {[0, 1, 2].map((n) => (
        <View key={n} style={styles.skeletonCard}>
          <View style={[styles.bar, { width: '32%' }]} />
          <View style={[styles.bar, { width: '86%', height: 14 }]} />
          <View style={[styles.bar, { width: '54%' }]} />
        </View>
      ))}
    </View>
  );
}

export function Clear({ heldBack }: { heldBack: number }) {
  return (
    <View style={styles.center}>
      <Text style={styles.clearTitle}>You're clear for today</Text>
      <Text style={styles.clearBody}>
        {heldBack > 0
          ? `${heldBack} ${heldBack === 1 ? 'item' : 'items'} held back as noise. They're in Later.`
          : 'Nothing needs you right now.'}
      </Text>
    </View>
  );
}

export function NothingConnected({ onConnect }: { onConnect: () => void }) {
  return (
    <View style={styles.center}>
      <Text style={styles.clearTitle}>Connect your first tool</Text>
      <Text style={styles.clearBody}>
        Your feed is built from GitHub, Slack, Calendar and Docs. Connect one to
        see what needs you.
      </Text>
      <Pressable onPress={onConnect} style={styles.cta}>
        <Text style={styles.ctaText}>Connect a tool</Text>
      </Pressable>
    </View>
  );
}

/**
 * Shown above a cached feed, never instead of it. The point is that the rows
 * below are real but old, which a spinner or a blank screen cannot say.
 */
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

export function ConnectionBroken({
  provider,
  onReconnect,
}: {
  provider: string;
  onReconnect: () => void;
}) {
  return (
    <Pressable onPress={onReconnect} style={[styles.banner, styles.bannerBad]}>
      <Text style={[styles.bannerText, styles.bannerBadText]}>
        {provider} disconnected. Tap to reconnect.
      </Text>
    </Pressable>
  );
}

export function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.accent} />
    </View>
  );
}

const styles = StyleSheet.create({
  pad: { padding: space.lg, gap: space.md },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: space.xl,
    gap: space.sm,
  },
  clearTitle: { ...type.h1, fontSize: 22, color: colors.fg, textAlign: 'center' },
  clearBody: { ...type.body, color: colors.dim, textAlign: 'center' },
  cta: {
    marginTop: space.md,
    backgroundColor: colors.accent,
    paddingHorizontal: space.xl,
    paddingVertical: space.md,
    borderRadius: radius.md,
  },
  ctaText: { ...type.body, fontWeight: '600', color: '#FFFFFF' },
  skeletonCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.line,
    padding: space.lg,
    gap: space.sm,
  },
  bar: { height: 10, borderRadius: radius.sm, backgroundColor: colors.line },
  banner: {
    marginHorizontal: space.lg,
    marginBottom: space.sm,
    backgroundColor: colors.accentSoft,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
  },
  bannerBad: { backgroundColor: colors.urgentSoft },
  bannerText: { ...type.small, color: colors.accent },
  bannerBadText: { color: colors.urgent },
});
