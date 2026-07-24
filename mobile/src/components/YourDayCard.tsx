/**
 * The day object: two rings, and the count that neither of them states.
 *
 * The review's question was the right one, and the answer was that the colours
 * meant two things each. Green was meetings on the outer ring and by-EOD on the
 * inner one; red was now on the outer ring and urgent on the inner one. Two
 * collisions, on the one element meant to be read at a glance.
 *
 * The fix is a rule rather than a repaint. **The outer ring is time, so it is
 * monochrome**, on a four-step grey ladder: hairline for the day still to come,
 * border for what has gone, mid for a meeting, and the brightest thing on the
 * screen for now. **The inner ring is work, so it is the only place a category
 * hue appears.** It needs no legend, because the selector immediately below it
 * is the legend, in the same colours and the same order.
 *
 * The number in the middle is what needs you, which is a third fact again, so
 * the hero is never a restatement of either ring.
 */

import React from 'react';
import { View } from 'react-native';
import Svg, {
  Circle,
  Defs,
  RadialGradient,
  Rect,
  Stop,
  G,
} from 'react-native-svg';
import { space, useTheme, type Category } from '../theme';
import { T } from './ui';

export interface Meeting {
  title: string;
  start: Date;
  end: Date;
}

/**
 * The ring is a full 24-hour clock. Midnight is at the top and noon at the
 * bottom, and everything runs clockwise from there, so a position on the ring
 * is just the hour of the day: `now` and every meeting land where they would on
 * a real clock face.
 *
 * It used to draw a compressed 08:00-20:00 window with everything outside it
 * clamped to the edge, which meant it was quietly wrong twice: an evening was
 * unrepresentable, so a 22:00 marker pinned to the top and read as midnight,
 * and a breakfast meeting and a midnight one landed on the same point. A day is
 * 0 to 24, so the ring is 0 to 24.
 */
const at = (hour: number) => clamp(hour / 24);

const R_TIME = 104;
const R_WORK = 80;
const BOX = 224;
const CENTRE = BOX / 2;

/** A 2pt gap between category arcs, so three of them are countable rather than
 *  merely proportional. */
const GAP = 0.008;

const ORDER: Category[] = ['urgent', 'byEod', 'canWait'];

export function DayRing({
  meetings,
  counts,
  now = new Date(),
}: {
  meetings: Meeting[];
  /** How many items sit in each of the three live categories. */
  counts: Record<'urgent' | 'byEod' | 'canWait', number>;
  now?: Date;
}) {
  const c = useTheme();
  const nowFrac = at(hoursOf(now));
  const total = counts.urgent + counts.byEod + counts.canWait;

  const timeC = 2 * Math.PI * R_TIME;
  const workC = 2 * Math.PI * R_WORK;

  return (
    <View style={{ height: 284, alignItems: 'center', justifyContent: 'center', marginTop: space.md }}>
      <View style={{ position: 'absolute', width: 300, height: 300 }}>
        <Svg width={300} height={300}>
          <Defs>
            <RadialGradient id="dayglow" cx="50%" cy="50%" r="50%">
              <Stop
                offset="0"
                stopColor={`rgb(${c.rgb.urgent})`}
                stopOpacity={c.mode === 'light' ? 0.09 : 0.14}
              />
              <Stop offset="0.62" stopColor={`rgb(${c.rgb.urgent})`} stopOpacity={0} />
            </RadialGradient>
          </Defs>
          <Rect width={300} height={300} fill="url(#dayglow)" />
        </Svg>
      </View>

      <Svg width={BOX} height={BOX}>
        {/* Outer: the day. Monochrome, always. */}
        <Circle
          cx={CENTRE}
          cy={CENTRE}
          r={R_TIME}
          fill="none"
          stroke={c.hairline}
          strokeWidth={5}
        />
        {/* Four ticks at the quarter-days, so the ring reads as a clock rather
            than a progress bar: midnight up, noon down, six and eighteen on the
            sides. */}
        {[0, 6, 12, 18].map((hour) => (
          <Tick key={hour} frac={at(hour)} colour={c.border} />
        ))}
        <Arc r={R_TIME} c={timeC} from={0} to={nowFrac} colour={c.border} width={5} />
        {meetings.map((meeting, index) => {
          const from = at(hoursOf(meeting.start));
          const to = at(hoursOf(meeting.end));
          if (to <= from) return null;
          return (
            <Arc
              key={index}
              r={R_TIME}
              c={timeC}
              from={from}
              to={to}
              colour={c.mid}
              width={5}
            />
          );
        })}
        <G
          transform={`rotate(${nowFrac * 360} ${CENTRE} ${CENTRE})`}
        >
          <Circle cx={CENTRE} cy={8} r={5} fill={c.high} />
        </G>

        {/* Inner: the work. The only place a category hue appears. */}
        <Circle
          cx={CENTRE}
          cy={CENTRE}
          r={R_WORK}
          fill="none"
          stroke={c.hairline}
          strokeWidth={16}
        />
        {total > 0
          ? ORDER.reduce<{ at: number; nodes: React.ReactNode[] }>(
              (acc, category) => {
                const share =
                  counts[category as keyof typeof counts] / total;
                if (share === 0) return acc;
                acc.nodes.push(
                  <Arc
                    key={category}
                    r={R_WORK}
                    c={workC}
                    from={acc.at}
                    to={acc.at + share - GAP}
                    colour={c.hue[category]}
                    width={16}
                  />,
                );
                return { at: acc.at + share, nodes: acc.nodes };
              },
              { at: 0, nodes: [] },
            ).nodes
          : null}
      </Svg>

      <View style={{ position: 'absolute', alignItems: 'center' }}>
        <T role="hero" numeric>
          {String(total)}
        </T>
        <T role="label" tone="low" style={{ marginTop: space.xxs }}>
          need you
        </T>
      </View>

      {/* The outer ring's key. The inner ring has none, because the selector
          directly beneath it is its key. */}
      <View
        style={{
          position: 'absolute',
          bottom: 0,
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.xs,
        }}
      >
        {/* A 24-hour clock needs no range printed on it, only what its two
            marks mean. */}
        <Dot colour={c.mid} />
        <T role="label" tone="low">
          Meeting
        </T>
        <Dot colour={c.high} />
        <T role="label" tone="low">
          Now
        </T>
      </View>
    </View>
  );
}

function Arc({
  r,
  c: circumference,
  from,
  to,
  colour,
  width,
}: {
  r: number;
  c: number;
  from: number;
  to: number;
  colour: string;
  width: number;
}) {
  const length = Math.max(0, (to - from) * circumference);
  return (
    <Circle
      cx={CENTRE}
      cy={CENTRE}
      r={r}
      fill="none"
      stroke={colour}
      strokeWidth={width}
      strokeDasharray={`${length} ${circumference - length}`}
      strokeDashoffset={-from * circumference}
      // Twelve o'clock is zero, and the day runs clockwise from there.
      transform={`rotate(-90 ${CENTRE} ${CENTRE})`}
    />
  );
}

/** A short radial tick on the outer ring, at a fraction of the 24-hour clock. */
function Tick({ frac, colour }: { frac: number; colour: string }) {
  const angle = frac * 2 * Math.PI - Math.PI / 2;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const inner = R_TIME - 7;
  const outer = R_TIME + 7;
  return (
    <Circle
      cx={CENTRE + cos * ((inner + outer) / 2)}
      cy={CENTRE + sin * ((inner + outer) / 2)}
      r={1.6}
      fill={colour}
    />
  );
}

function Dot({ colour }: { colour: string }) {
  return (
    <View
      style={{ width: 8, height: 8, borderRadius: 999, backgroundColor: colour }}
    />
  );
}

// Local time throughout. `getHours` is the device's own calendar, so an item
// that arrives as UTC on the wire is placed where the person holding the phone
// would put it.
const hoursOf = (date: Date) => date.getHours() + date.getMinutes() / 60;
const clamp = (value: number) => Math.max(0, Math.min(1, value));
