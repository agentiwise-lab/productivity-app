/**
 * The glyph set, transcribed path for path from the mockup's `<defs>`.
 *
 * Drawn rather than imported. Every glyph is a stroked 24-unit shape with round
 * caps and joins, which is the one visual decision that makes the set feel like
 * a set: an icon library gives you consistency with its own house, not with
 * yours, and the four category glyphs below have no equivalent in any library
 * because they encode this product's own ladder.
 *
 * The category glyphs are the ladder the app already ships as `TIER_GLYPH`,
 * drawn as vectors: a struck bell for urgent, a half-filled disc for by EOD,
 * an open ring for can wait, a dot for later. They read as a filling sequence,
 * so they survive greyscale and they survive being small.
 */

import React from 'react';
import Svg, { Circle, Path, Rect, G } from 'react-native-svg';

export type GlyphName =
  | 'sun'
  | 'cards'
  | 'clock'
  | 'pulse'
  | 'user'
  | 'external'
  | 'refresh'
  | 'plus'
  | 'chevron'
  | 'check'
  | 'reply'
  | 'snooze'
  | 'chat'
  | 'checks'
  | 'more'
  | 'send'
  | 'calendar'
  | 'up'
  | 'tierUrgent'
  | 'tierByEod'
  | 'tierCanWait'
  | 'tierLater';

interface Props {
  name: GlyphName;
  size: number;
  color: string;
  /** Stroke width. 1.7 for a secondary glyph, 2 for a primary one. */
  weight?: number;
}

export function Icon({ name, size, color, weight = 1.8 }: Props) {
  const stroke = {
    stroke: color,
    strokeWidth: weight,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    fill: 'none' as const,
  };

  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {body(name, stroke, color)}
    </Svg>
  );
}

type Stroke = ReturnType<typeof strokeShape>;
function strokeShape() {
  return {
    stroke: '',
    strokeWidth: 0,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    fill: 'none' as const,
  };
}

function body(name: GlyphName, s: Stroke, color: string) {
  switch (name) {
    case 'sun':
      return (
        <G {...s}>
          <Circle cx={12} cy={12} r={4.2} />
          <Path d="M12 2.6v2.4M12 19v2.4M21.4 12H19M5 12H2.6M18.6 5.4l-1.7 1.7M7.1 16.9l-1.7 1.7M18.6 18.6l-1.7-1.7M7.1 7.1L5.4 5.4" />
        </G>
      );
    case 'cards':
      return (
        <G {...s}>
          <Rect x={3} y={7.5} width={14} height={13} rx={2.6} />
          <Path d="M7.2 4.4h10.4a2.6 2.6 0 0 1 2.6 2.6v10.2" />
        </G>
      );
    case 'clock':
      return (
        <G {...s}>
          <Circle cx={12} cy={12} r={9} />
          <Path d="M12 6.8V12l3.6 2.1" />
        </G>
      );
    case 'pulse':
      return <Path {...s} d="M2.8 12h4l2.4-6.4 4.4 12.8L16 12h5.2" />;
    case 'user':
      return (
        <G {...s}>
          <Circle cx={12} cy={8.2} r={4} />
          <Path d="M4.2 20.4a8.2 8.2 0 0 1 15.6 0" />
        </G>
      );
    case 'external':
      return (
        <G {...s}>
          <Path d="M14 4h6v6M20 4l-8.6 8.6" />
          <Path d="M18 14.4V19a1.6 1.6 0 0 1-1.6 1.6H5A1.6 1.6 0 0 1 3.4 19V7.6A1.6 1.6 0 0 1 5 6h4.6" />
        </G>
      );
    case 'refresh':
      return (
        <G {...s}>
          <Path d="M20.4 11.2A8.4 8.4 0 1 0 18 17.6" />
          <Path d="M20.8 5.6v6h-6" />
        </G>
      );
    case 'plus':
      return <Path {...s} d="M12 5.2v13.6M5.2 12h13.6" />;
    case 'chevron':
      return <Path {...s} d="M9.4 5.6L15.8 12l-6.4 6.4" />;
    case 'check':
      return <Path {...s} d="M4.8 12.6l4.8 4.8L19.2 7.8" />;
    case 'reply':
      return (
        <G {...s}>
          <Path d="M9 6.4L3.4 12 9 17.6" />
          <Path d="M3.4 12h9.2a8 8 0 0 1 8 8v.6" />
        </G>
      );
    case 'snooze':
      return (
        <G {...s}>
          <Circle cx={12} cy={13} r={8} />
          <Path d="M12 9.4V13l2.6 1.6M9 2.6h6" />
        </G>
      );
    case 'chat':
      return (
        <Path
          {...s}
          d="M20.4 11.6a7.6 7.6 0 0 1-8.2 7.6L6.2 21.4l1.4-4.2A7.6 7.6 0 1 1 20.4 11.6Z"
        />
      );
    case 'checks':
      return (
        <G {...s}>
          <Path d="M2.6 12.6l4 4L14.2 9" />
          <Path d="M10.4 15.4l1.2 1.2L21.4 6.8" />
        </G>
      );
    case 'more':
      return (
        <G fill={color}>
          <Circle cx={5} cy={12} r={1.6} />
          <Circle cx={12} cy={12} r={1.6} />
          <Circle cx={19} cy={12} r={1.6} />
        </G>
      );
    case 'send':
      return <Path {...s} d="M21 3L10.5 13.5M21 3l-6.6 18-3.9-7.5L3 9.6 21 3Z" />;
    case 'calendar':
      return (
        <G {...s}>
          <Rect x={3.4} y={5} width={17.2} height={16} rx={2.6} />
          <Path d="M3.4 10h17.2M8 3v4M16 3v4" />
        </G>
      );
    /** Bring a snoozed item back to the live queue. */
    case 'up':
      return <Path {...s} d="M12 20.4V4.6M5.4 11.2L12 4.6l6.6 6.6" />;

    /* ── the category ladder ─────────────────────────────────────────── */
    case 'tierUrgent':
      return (
        <G>
          <Circle cx={12} cy={12} r={9} fill="none" stroke={color} strokeWidth={2} />
          <Path
            d="M12 7.2v5.4"
            stroke={color}
            strokeWidth={2}
            strokeLinecap="round"
          />
          <Circle cx={12} cy={16.4} r={1.15} fill={color} />
        </G>
      );
    case 'tierByEod':
      return (
        <G>
          <Circle cx={12} cy={12} r={9} fill="none" stroke={color} strokeWidth={2} />
          <Path d="M12 3.6a8.4 8.4 0 0 1 0 16.8Z" fill={color} />
        </G>
      );
    case 'tierCanWait':
      return (
        <Circle cx={12} cy={12} r={9} fill="none" stroke={color} strokeWidth={2} />
      );
    case 'tierLater':
      return <Circle cx={12} cy={12} r={3.4} fill={color} />;
  }
}

/** The category glyph for a category, so callers never map this themselves. */
export const CATEGORY_GLYPH = {
  urgent: 'tierUrgent',
  byEod: 'tierByEod',
  canWait: 'tierCanWait',
  later: 'tierLater',
  none: 'tierCanWait',
  summary: 'tierCanWait',
} as const satisfies Record<string, GlyphName>;
