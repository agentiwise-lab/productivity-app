/**
 * What the raw values mean. Components import from here and never from
 * `primitives`, so a repaint is one file rather than a search.
 */

import { brand, hueRgb, hues, neutrals, type Mode } from './primitives';
import type { Source, Tier } from '../api/types';

/**
 * The six categories. Four are the tiers; the last two cover the rows that
 * have no category at all, and neither ever shares a screen with a tier hue,
 * so neither can be misread as one.
 */
export type Category =
  | 'urgent'
  | 'byEod'
  | 'canWait'
  | 'later'
  | 'none'
  | 'summary';

/** The wire tiers, in the app's own words. */
export const CATEGORY_OF_TIER: Record<Tier, Category> = {
  urgent: 'urgent',
  today: 'byEod',
  can_wait: 'canWait',
  noise: 'later',
};

/**
 * "Today" beside "Urgent" reads as a time window rather than a priority, and
 * urgent things are also today. "By EOD" says what is actually being claimed.
 * The wire value stays `today`: renaming a persisted enum for a label is a
 * migration that buys nothing.
 */
export const CATEGORY_LABEL: Record<Category, string> = {
  urgent: 'Urgent',
  byEod: 'By EOD',
  canWait: 'Can wait',
  later: 'Later',
  none: '',
  summary: '',
};

export interface Palette {
  mode: Mode;
  /** Neutral ladder. */
  canvas: string;
  surface: string;
  raised: string;
  overlay: string;
  hairline: string;
  border: string;
  faint: string;
  low: string;
  mid: string;
  high: string;
  onSolid: string;
  scrim: string;
  tabBar: string;
  lift: string;
  /** The six category hues, solid. */
  hue: Record<Category, string>;
  /** The same six as "r,g,b", for washes, blooms and tints. */
  rgb: Record<Category, string>;
  /** Brand marks, which keep their own colours. */
  brand: Record<Source, string>;
}

export function paletteFor(mode: Mode): Palette {
  return {
    mode,
    ...neutrals[mode],
    hue: hues[mode],
    rgb: hueRgb[mode],
    brand,
  };
}

/**
 * The bloom that rises from the bottom of a feed card.
 *
 * Two layers rather than one: a radial that reads as a source of light below
 * the screen edge, and a linear that keeps the bottom eighth from going flat
 * where the radial has already fallen off. Light mode halves every stop,
 * because a light field carries a tint much further before it stops reading as
 * a glow and starts reading as a fill.
 */
const BLOOM_PEAK: Record<Category, number> = {
  urgent: 0.5,
  byEod: 0.42,
  later: 0.4,
  canWait: 0.34,
  none: 0.34,
  summary: 0.34,
};

export function bloom(palette: Palette, category: Category) {
  const rgb = palette.rgb[category];
  const light = palette.mode === 'light';
  const peak = light ? BLOOM_PEAK[category] * 0.44 : BLOOM_PEAK[category];
  const mid = light ? 0.06 : 0.16;
  return {
    rgb,
    stops: [
      `rgba(${rgb},${peak})`,
      `rgba(${rgb},${mid})`,
      `rgba(${rgb},0)`,
    ] as const,
    /** Where the middle stop sits, as a fraction of the bloom's height. */
    locations: [0, 0.42, 0.74] as const,
    /** The linear layer, which light mode drops entirely. */
    linear: light ? null : (`rgba(${rgb},0.16)` as const),
  };
}

/** The 120pt wash behind a row, and the 220pt one at the top of a sheet. */
export function wash(palette: Palette, category: Category, alpha = 0.16) {
  const rgb = palette.rgb[category];
  return [`rgba(${rgb},${alpha})`, `rgba(${rgb},0)`] as const;
}
