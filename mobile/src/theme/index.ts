/**
 * The one import for anything visual.
 *
 * `useTheme()` returns the resolved palette. Styles that depend on it are built
 * through `makeStyles`, which caches one StyleSheet per mode, so switching
 * appearance costs a lookup rather than a rebuild on every render.
 */

import { useMemo } from 'react';
import { StyleSheet } from 'react-native';
import { useAppearance } from './appearance';
import { paletteFor, type Palette } from './semantic';

export * from './primitives';
export * from './semantic';
export * from './space';
export * from './type';
export * as motion from './motion';
export * as haptics from './haptics';
export { AppearanceProvider, useAppearance } from './appearance';
export type { Appearance } from './appearance';

export function useTheme(): Palette {
  const { mode } = useAppearance();
  return useMemo(() => paletteFor(mode), [mode]);
}

/**
 * A themed stylesheet. The factory runs once per mode and the result is kept,
 * because a stylesheet rebuilt on every render defeats the point of having one.
 */
export function makeStyles<T extends StyleSheet.NamedStyles<T>>(
  build: (c: Palette) => T,
): () => T {
  const cache = new Map<string, T>();
  return function useStyles(): T {
    const palette = useTheme();
    const hit = cache.get(palette.mode);
    if (hit) return hit;
    const made = StyleSheet.create(build(palette));
    cache.set(palette.mode, made);
    return made;
  };
}
