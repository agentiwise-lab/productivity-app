/**
 * Seven roles. There is no eighth.
 *
 * The old theme had ten sizes with sub-point gaps between them, which is not a
 * hierarchy: it is ten values that happen to be different. These seven are far
 * enough apart to be told apart at a glance.
 *
 * `letterSpacing` in React Native is density-independent pixels rather than em,
 * and the mockup is drawn at one pixel to one point, so the tracking below is
 * transcribed rather than converted.
 *
 * Each weight is registered as its own family. Asking for `fontWeight: '600'`
 * on a family that only shipped its regular cut fails silently on iOS: it
 * renders the regular and says nothing.
 */

import type { TextStyle } from 'react-native';

export const fonts = {
  sans: 'Geist_400Regular',
  sansMedium: 'Geist_500Medium',
  sansSemi: 'Geist_600SemiBold',
  /**
   * The label and display faces. The mockup sets `font-stretch: 88%`, a width
   * axis only a variable font carries and React Native cannot address. Archivo
   * ships a SemiCondensed named instance at 87.5%, which is that value to
   * within half a per cent, so the static cut is vendored under
   * `assets/fonts/` and loaded by name.
   *
   * Regular-width Archivo was what shipped first, and it was wrong by more than
   * it sounds: every display and label string measured 10 to 13 per cent wider
   * than the mockup, which is why titles wrapped a line early and the whole
   * screen read heavier than it was drawn.
   */
  display: 'Archivo_SemiCondensed_600SemiBold',
  mono: 'GeistMono_400Regular',
} as const;

export const type = {
  hero: {
    fontFamily: fonts.display,
    fontSize: 56,
    lineHeight: 56,
    letterSpacing: -1.4,
  },
  display: {
    fontFamily: fonts.display,
    fontSize: 34,
    lineHeight: 40,
    letterSpacing: -0.7,
  },
  title: {
    fontFamily: fonts.sansSemi,
    fontSize: 22,
    lineHeight: 28,
    letterSpacing: -0.4,
  },
  heading: {
    fontFamily: fonts.sansSemi,
    fontSize: 17,
    lineHeight: 24,
    letterSpacing: -0.1,
  },
  body: {
    fontFamily: fonts.sans,
    fontSize: 15,
    lineHeight: 20,
    letterSpacing: 0,
  },
  secondary: {
    fontFamily: fonts.sans,
    fontSize: 13,
    lineHeight: 20,
    letterSpacing: 0.1,
  },
  label: {
    fontFamily: fonts.display,
    fontSize: 11,
    lineHeight: 16,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
} as const satisfies Record<string, TextStyle>;

/** Body weight, for the one place a row title is emphasised inside a line. */
export const bodyMedium = { ...type.body, fontFamily: fonts.sansMedium };

/**
 * Machine values only: counts, times, ages, ids, refs. Tabular figures so a
 * column of them aligns, which is the entire reason to reach for it.
 */
export const mono = {
  body: { ...type.body, fontFamily: fonts.mono, fontVariant: ['tabular-nums'] },
  secondary: {
    ...type.secondary,
    fontFamily: fonts.mono,
    fontVariant: ['tabular-nums'],
  },
  label: {
    ...type.secondary,
    fontFamily: fonts.mono,
    fontSize: 11,
    lineHeight: 16,
    fontVariant: ['tabular-nums'],
  },
  heading: { ...type.heading, fontFamily: fonts.mono, fontVariant: ['tabular-nums'] },
  hero: { ...type.hero, fontVariant: ['tabular-nums'] },
  display: { ...type.display, fontVariant: ['tabular-nums'] },
  title: { ...type.title, fontVariant: ['tabular-nums'] },
} as const;

/**
 * Dynamic Type. Body copy scales all the way, because someone who needs 200%
 * text needs it most on the thing they are trying to read. The three display
 * roles clamp at 1.3, past which a 56pt hero stops fitting its own ring.
 *
 * `allowFontScaling={false}` is banned everywhere except the hero.
 */
export const maxScale = {
  hero: 1.3,
  display: 1.3,
  label: 1.3,
} as const;
