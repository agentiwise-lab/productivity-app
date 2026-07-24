/**
 * Film grain, at 5.5%.
 *
 * Large flat fields of near-black band on OLED, and a flat field is also what
 * makes a dark interface read as cheap rather than deep. A few percent of noise
 * breaks the banding and gives the canvas a surface. It is meant to be
 * invisible: if you can see it, it is too strong.
 *
 * Mounted once, above everything, and it never receives a touch.
 */

import React from 'react';
import { Image, StyleSheet, View } from 'react-native';
import { GRAIN_TILE } from './grainTile';

export function Grain() {
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.layer]}>
      <Image
        source={{ uri: GRAIN_TILE }}
        resizeMode="repeat"
        style={StyleSheet.absoluteFill}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  layer: {
    opacity: 0.045,
    zIndex: 30,
    // Overlay rather than normal, so the noise darkens and lightens around the
    // colour under it instead of simply fogging it grey. Platforms without
    // blend modes fall back to a fog too faint to notice.
    mixBlendMode: 'overlay',
  },
});
