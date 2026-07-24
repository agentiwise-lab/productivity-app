/**
 * Raw values. Nothing here knows what anything means.
 *
 * Transcribed from docs/mockups/v4-screens.html, which is drawn at 393x852 with
 * one CSS pixel to one iOS point. There is no scale factor and there must never
 * be one again: every size in the old theme was a 272pt measurement multiplied
 * by 1.379, which is why nothing landed on a whole point.
 */

/** The six category hues. Colour is the category and never the source. */
export const hues = {
  dark: {
    urgent: '#FF6B5F',
    byEod: '#63E4C2',
    canWait: '#AB7FF8',
    later: '#F2B366',
    none: '#7FA6D9',
    summary: '#C9B79A',
  },
  light: {
    urgent: '#CC4432',
    byEod: '#0D8167',
    canWait: '#7144CC',
    later: '#96631F',
    none: '#3E6EA8',
    summary: '#6E5A40',
  },
} as const;

/** The same six as "r,g,b", for the washes and blooms that need an alpha. */
export const hueRgb = {
  dark: {
    urgent: '255,107,95',
    byEod: '99,228,194',
    canWait: '171,127,248',
    later: '242,179,102',
    none: '127,166,217',
    summary: '201,183,154',
  },
  light: {
    urgent: '204,68,50',
    byEod: '13,129,103',
    canWait: '113,68,204',
    later: '150,99,31',
    none: '62,110,168',
    summary: '110,90,64',
  },
} as const;

/**
 * The neutral ladder.
 *
 * Dark runs warm: R above G above B at every step. Light is the sage teal from
 * ad_analytics, whose own tokens call it weathered copper, at hue 179 and 19%
 * saturation. That mutedness is the character, not a compromise.
 *
 * Every text and fill pair here was measured rather than judged, and measured
 * against **every** surface the tone actually lands on rather than only the
 * commonest one. That distinction is not academic: `low` cleared 4.8 on
 * `surface` and was signed off, but section labels, the eyebrow, the tab labels
 * and the ring key all sit on `canvas`, and the unselected segments sit on
 * `overlay`, where the same value measured 4.3 and 3.8. Both ladders now clear
 * 4.5 on canvas, surface, raised and overlay alike.
 *
 * `faint` is deliberately below AA and is therefore **never** text a reader has
 * to read: it is the off-state toggle knob and nothing else.
 */
export const neutrals = {
  dark: {
    canvas: '#0C0B0A',
    surface: '#151311',
    raised: '#1D1A17',
    overlay: '#26221E',
    hairline: '#2E2A26',
    border: '#3B352F',
    faint: '#57504A',
    low: '#918A81',
    mid: '#A79F97',
    high: '#F5F1EC',
    onSolid: '#0C0B0A',
    scrim: 'rgba(0,0,0,0.58)',
    tabBar: 'rgba(12,11,10,0.74)',
    /** The `why` block, which is a lift off the surface rather than a colour. */
    lift: 'rgba(255,255,255,0.04)',
  },
  light: {
    canvas: '#DCE6E5',
    surface: '#EAF1F0',
    raised: '#F2F7F6',
    overlay: '#CBDAD9',
    hairline: '#BFD0CF',
    border: '#A8BEBD',
    faint: '#86A09F',
    low: '#47605F',
    mid: '#3E5453',
    high: '#12201F',
    onSolid: '#FFFDF9',
    scrim: 'rgba(18,32,31,0.34)',
    tabBar: 'rgba(220,230,229,0.80)',
    lift: 'rgba(18,32,31,0.05)',
  },
} as const;

/**
 * Brand marks keep their own colours. This is one of exactly two exemptions
 * from "colour is the category": a mark is identity, and it never sits where a
 * category signal lives, so it cannot be misread as one. Monochrome marks were
 * tried and rejected.
 */
export const brand = {
  github: '#AB7FF8',
  slack: '#36C5F0',
  linear: '#5E6AD2',
  gmail: '#EA4335',
  google_docs: '#4285F4',
  calendar: '#4285F4',
} as const;

export type Mode = 'dark' | 'light';
