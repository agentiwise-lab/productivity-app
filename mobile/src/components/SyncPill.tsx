/**
 * A small centred pill just above the footer. Two jobs, one pill so they never
 * stack: while a freshly connected source pulls its backfill it reads "Syncing…"
 * (per-source, from `sources`), and while a plain refresh sweep runs it reads
 * "Updating…" (from `updating`). Both are promise-driven by the parent, so there
 * is no countdown to drift out of sync with the real work. A connect wins over a
 * refresh because it is the more specific thing the user just did.
 */

import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { radius, space, useTheme } from '../theme';
import type { Source } from '../api/types';
import { T } from './ui';

export function SyncPill({
  sources,
  updating = false,
}: {
  sources: Set<Source>;
  updating?: boolean;
}) {
  const c = useTheme();
  if (sources.size === 0 && !updating) return null;

  const label =
    sources.size > 0
      ? sources.size === 1
        ? 'Syncing…'
        : `Syncing ${sources.size} sources…`
      : 'Updating…';

  return (
    <View pointerEvents="none" style={styles.wrap}>
      <View style={[styles.pill, { backgroundColor: c.overlay }]}>
        <ActivityIndicator size="small" color={c.hue.later} />
        <T role="label" tone="mid">
          {label}
        </T>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 92, // clears the tab bar
    alignItems: 'center',
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    paddingHorizontal: space.md,
    height: 32,
    borderRadius: radius.pill,
  },
});
