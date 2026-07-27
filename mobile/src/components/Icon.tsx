/**
 * The glyph set.
 *
 * Eighteen of these were hand-drawn, transcribed path for path from the
 * mockup's `<defs>`, and the reasoning at the time was that an icon library
 * gives you consistency with its own house rather than with yours. That was
 * wrong in the way it usually is: a set of twenty drawn by one person over an
 * afternoon has no optical correction, no consistent terminal, no consistent
 * corner radius and no consistent apparent weight, so it reads as drawn rather
 * than as designed. Phosphor's set has all four, at four weights, and is what
 * gives the bar its platform feel.
 *
 * **The four category glyphs stay drawn**, because they are not icons: they are
 * this product's own ladder, a filling sequence from a struck disc through a
 * half disc and an open ring to a dot. No library has them, and their whole job
 * is to survive greyscale and survive being small.
 */

import React from 'react';
import Svg, { Circle, Path } from 'react-native-svg';
import {
  Alarm,
  ArrowBendUpLeft,
  ArrowClockwise,
  ArrowLineUp,
  ArrowSquareOut,
  ArrowUUpLeft,
  CalendarBlank,
  CaretRight,
  Cards,
  ChartLineUp,
  ChatCircle,
  Check,
  Checks,
  Clock,
  DotsThree,
  PaperPlaneTilt,
  PencilSimple,
  Plus,
  Sun,
  User,
  UserPlus,
  X,
} from 'phosphor-react-native';

export type GlyphName =
  | 'sun'
  | 'cards'
  | 'clock'
  | 'pulse'
  | 'user'
  | 'external'
  | 'refresh'
  | 'pencil'
  | 'plus'
  | 'chevron'
  | 'check'
  | 'reply'
  | 'snooze'
  | 'chat'
  | 'checks'
  | 'more'
  | 'changes'
  | 'assign'
  | 'decline'
  | 'send'
  | 'calendar'
  | 'up'
  | 'tierUrgent'
  | 'tierByEod'
  | 'tierCanWait'
  | 'tierLater';

/**
 * Phosphor's four weights, in the two this app uses.
 *
 * `regular` is every resting state. `fill` is the selected tab and the one
 * primary action on a card, which is how a platform bar signals selection: by
 * filling the glyph rather than by tinting it, so the signal survives for a
 * reader who cannot separate the two colours.
 */
export type IconWeight = 'regular' | 'bold' | 'fill' | 'duotone';

const PHOSPHOR = {
  sun: Sun,
  cards: Cards,
  clock: Clock,
  pulse: ChartLineUp,
  user: User,
  external: ArrowSquareOut,
  refresh: ArrowClockwise,
  plus: Plus,
  chevron: CaretRight,
  check: Check,
  reply: ArrowBendUpLeft,
  snooze: Alarm,
  chat: ChatCircle,
  checks: Checks,
  more: DotsThree,
  // Sending a review back is a return rather than an ellipsis, which is what
  // the "Changes" button used to draw.
  changes: ArrowUUpLeft,
  assign: UserPlus,
  decline: X,
  send: PaperPlaneTilt,
  calendar: CalendarBlank,
  up: ArrowLineUp,
} as const;

interface Props {
  name: GlyphName;
  size: number;
  color: string;
  weight?: IconWeight;
}

export function Icon({ name, size, color, weight = 'regular' }: Props) {
  const Glyph = PHOSPHOR[name as keyof typeof PHOSPHOR];
  if (Glyph) return <Glyph size={size} color={color} weight={weight} />;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {ladder(name, color)}
    </Svg>
  );
}

/** The category ladder, which is the product's own and not anybody's set. */
function ladder(name: GlyphName, color: string) {
  switch (name) {
    case 'tierUrgent':
      return (
        <>
          <Circle cx={12} cy={12} r={9} fill="none" stroke={color} strokeWidth={2} />
          <Path
            d="M12 7.2v5.4"
            stroke={color}
            strokeWidth={2}
            strokeLinecap="round"
          />
          <Circle cx={12} cy={16.4} r={1.15} fill={color} />
        </>
      );
    case 'tierByEod':
      return (
        <>
          <Circle cx={12} cy={12} r={9} fill="none" stroke={color} strokeWidth={2} />
          <Path d="M12 3.6a8.4 8.4 0 0 1 0 16.8Z" fill={color} />
        </>
      );
    case 'tierCanWait':
      return (
        <Circle cx={12} cy={12} r={9} fill="none" stroke={color} strokeWidth={2} />
      );
    default:
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
