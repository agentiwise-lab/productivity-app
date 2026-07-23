/**
 * Sand & Slate, with the type scale taken from docs/mockups/home.html rather
 * than reinvented.
 *
 * The mockup is drawn at a 272pt phone width. Everything below is scaled from
 * that to a real 375pt screen by SCALE, so proportions hold instead of the
 * layout being re-guessed at device size. That is the difference between
 * matching the design and merely resembling it.
 */

const MOCKUP_WIDTH = 272;
const DEVICE_WIDTH = 375;
export const SCALE = DEVICE_WIDTH / MOCKUP_WIDTH; // 1.379

/** Scale a mockup measurement into device points. */
export const s = (mockupPx: number) => Math.round(mockupPx * SCALE * 10) / 10;

export const colors = {
  bg: '#F4F1EC',
  surface: '#FFFDFA',
  fg: '#20242B',
  dim: '#79808A',
  line: '#E0DCD4',
  accent: '#2F4858',
  accentSoft: '#E0E7EC',
  onAccent: '#F4F8FA',
  urgent: '#B25B33',
  urgentSoft: '#F7E7DC',
} as const;

/** Source roundel colours, straight from the mockup's .ic classes. */
export const roundel: Record<string, { bg: string; fg: string }> = {
  slack: { bg: '#E4DCCB', fg: '#7A5A2E' },
  github: { bg: '#252A31', fg: '#E6EAEE' },
  google_docs: { bg: '#D8E2E8', fg: '#2E5A72' },
  linear: { bg: '#DFDCEA', fg: '#4C4278' },
  calendar: { bg: '#E8D8D2', fg: '#8A3E30' },
  gmail: { bg: '#E8D8D2', fg: '#8A3E30' },
};

export const mono = 'Menlo';

export const type = {
  /** .hd .nm2 */
  headerTitle: { fontSize: s(12), fontWeight: '600' as const, letterSpacing: -0.1 },
  /** .hd .dt */
  headerDate: {
    fontFamily: mono,
    fontSize: s(8.5),
    letterSpacing: 0.5,
    color: colors.dim,
  },
  /** .ttl b */
  cardTitle: { fontSize: s(11.5), fontWeight: '600' as const },
  /** .ttl span, .rfoot */
  cardMeta: { fontFamily: mono, fontSize: s(9), color: colors.dim, letterSpacing: 0.4 },
  /** .chip .n */
  chipNumber: { fontFamily: mono, fontSize: s(15), fontWeight: '600' as const },
  /** .chip .t */
  chipLabel: { fontSize: s(8), letterSpacing: 0.4, textTransform: 'uppercase' as const },
  /** .tg */
  tag: {
    fontFamily: mono,
    fontSize: s(8),
    letterSpacing: 0.6,
    textTransform: 'uppercase' as const,
  },
  /** .fc-ago, .rmeta */
  ago: { fontFamily: mono, fontSize: s(8.5), color: colors.dim },
  /** .fcard h4 */
  cardHeading: { fontSize: s(13), lineHeight: s(13) * 1.32, fontWeight: '600' as const },
  /** .fcard .why */
  why: { fontSize: s(10.5), lineHeight: s(10.5) * 1.42, color: colors.dim },
  /** .fc-btn .b */
  button: { fontSize: s(10.5) },
  /** .divider */
  divider: {
    fontFamily: mono,
    fontSize: s(8.5),
    letterSpacing: 1.1,
    textTransform: 'uppercase' as const,
    color: colors.dim,
  },
  /** .lsthd .lb */
  groupLabel: { fontSize: s(11.5), fontWeight: '600' as const },
  /** .lsthd .ct */
  groupCount: { fontFamily: mono, fontSize: s(10), color: colors.dim },
  /** .row .rt */
  rowTitle: { fontSize: s(12), lineHeight: s(12) * 1.34 },
  /** .row .sm */
  rowSub: { fontSize: s(10), color: colors.dim },
  /** .tb div */
  tabLabel: {
    fontSize: s(7.5),
    letterSpacing: 0.4,
    textTransform: 'uppercase' as const,
  },
} as const;

/** Spacing scale, in device points, derived from the mockup's padding steps. */
export const space = {
  xs: s(3),
  sm: s(6),
  md: s(9),
  lg: s(13),
  xl: s(16),
  xxl: s(24),
} as const;

export const radius = {
  sm: s(4),
  md: s(9),
  lg: s(14),
  pill: 999,
} as const;

/** Roles used by the detail sheet and settings, on the same scale. */
export const text = {
  h2: { fontSize: s(13), fontWeight: '600' as const },
  body: { fontSize: s(11.5), lineHeight: s(11.5) * 1.4 },
  small: { fontSize: s(10), lineHeight: s(10) * 1.4 },
  monoLabel: { fontFamily: mono, fontSize: s(8.5), letterSpacing: 0.6 },
} as const;

/**
 * "Today" alongside "Urgent" reads as a time window rather than a priority, and
 * urgent things are also today. "By EOD" says what is actually being claimed.
 */
export const tierLabel = {
  urgent: 'Urgent',
  today: 'By EOD',
  can_wait: 'Can wait',
  noise: 'Noise',
} as const;

/** .lsthd .pip colours, in tier order. */
export const pipColor = {
  urgent: colors.urgent,
  today: colors.accent,
  can_wait: colors.line,
  noise: colors.line,
} as const;

export type Tier = keyof typeof tierLabel;
