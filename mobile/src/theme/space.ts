/**
 * The spacing scale and the radius ramp.
 *
 * Eight spacing steps and five radii, and nothing else is permitted. If a value
 * cannot be expressed on the scale, the value is wrong rather than the scale.
 * The two OS insets are the only exceptions, because they are measurements of
 * the device rather than decisions of ours.
 */

export const space = {
  xxs: 4,
  xs: 8,
  sm: 12,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  huge: 96,
} as const;

/** Status bar and home indicator. Off the scale, and allowed to be. */
export const inset = { top: 54, bottom: 34 } as const;

/** Nested radii follow `inner = outer - padding`, never a second guess. */
export const radius = { xs: 4, sm: 8, md: 12, lg: 16, pill: 999 } as const;

/** Fixed heights, transcribed from the mockup. */
export const size = {
  chip: 28,
  segmented: 32,
  control: 44,
  bigButton: 48,
  tabBar: 83,
  tabItem: 49,
  collapsedHeader: 44,
  row: 64,
} as const;
