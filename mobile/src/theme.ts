/**
 * Sand & Slate. The palette is locked; see docs/design-system.md.
 *
 * Only two colours carry meaning. Ochre means "this is urgent" and appears
 * nowhere else, so it never has to compete for attention. Slate is the app's
 * own voice: headers, actions, anything the product says rather than reports.
 * Everything else is a neutral warm enough to make paper, not a screen.
 */

export const colors = {
  bg: '#F4F1EC',
  surface: '#FFFDFA',
  fg: '#20242B',
  dim: '#79808A',
  line: '#E0DCD4',
  accent: '#2F4858',
  accentSoft: '#E0E7EC',
  urgent: '#B25B33',
  urgentSoft: '#F7E7DC',
} as const;

/** 4 / 8 / 12 / 16 / 24 / 32. Nothing is eyeballed. */
export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  pill: 999,
} as const;

export const type = {
  /** Section titles. */
  h1: { fontSize: 26, fontWeight: '600' as const, letterSpacing: -0.4 },
  h2: { fontSize: 17, fontWeight: '600' as const, letterSpacing: -0.2 },
  /** Card titles. */
  title: { fontSize: 15, fontWeight: '600' as const, lineHeight: 20 },
  body: { fontSize: 14, fontWeight: '400' as const, lineHeight: 19 },
  small: { fontSize: 12, fontWeight: '400' as const, lineHeight: 16 },
  /** Type tags and times. Mono so digits line up down the right edge. */
  mono: {
    fontSize: 10,
    fontWeight: '600' as const,
    letterSpacing: 0.8,
    fontFamily: 'Courier',
  },
} as const;

export const tierColor = {
  urgent: colors.urgent,
  today: colors.accent,
  can_wait: colors.dim,
  noise: colors.dim,
} as const;

export const tierLabel = {
  urgent: 'Urgent',
  today: 'Today',
  can_wait: 'Can wait',
  noise: 'Noise',
} as const;

export type Tier = keyof typeof tierColor;
