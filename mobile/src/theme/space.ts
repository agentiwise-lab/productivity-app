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

/**
 * Status bar and home indicator. Off the scale, and allowed to be, because
 * they are measurements of the device rather than decisions of ours.
 *
 * 54 is the status bar on a Dynamic Island phone at this width; the notched
 * generation is 47 and a home-button phone is 20. `useTopInset` below prefers
 * whatever the OS reports and only falls back to this, so the number is a
 * default for the web preview rather than an assumption about the hardware.
 */
export const inset = { top: 54, bottom: 34 } as const;

/**
 * Where a screen's first pixel of content may go.
 *
 * Every scroll view starts at `useTopInset()` and never at zero. The status
 * bar is drawn by the OS over the top of the app, so anything at y=0 is under
 * the clock and the battery: the eyebrow on Day, Later, Activity and You all
 * sat there, which is why those four read as though the header were missing.
 *
 * `react-native-safe-area-context` reports zero on web, where there is no
 * status bar to avoid but there is a preview to judge the design in, so the
 * fallback keeps the browser honest about what the phone will show.
 */
export const topInset = (safeAreaTop: number) => safeAreaTop || inset.top;

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
