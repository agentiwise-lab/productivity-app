/**
 * A small centred pill just above the footer, shown while one or more sources
 * are pulling their backfill after a connect. Promise-driven: the parent adds a
 * source when its connect-refresh starts and removes it when the promise
 * resolves, so there is no countdown to drift out of sync with the real work.
 */

import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { radius, space, useTheme } from '../theme';
import type { Source } from '../api/types';
import { T } from './ui';

export function SyncPill({ sources }: { sources: Set<Source> }) {
  const c = useTheme();
  if (sources.size === 0) return null;

  const label =
    sources.size === 1 ? 'Syncing…' : `Syncing ${sources.size} sources…`;

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
