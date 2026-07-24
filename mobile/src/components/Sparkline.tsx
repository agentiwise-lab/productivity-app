/**
 * Fourteen days of a source's volume, as bars.
 *
 * Deliberately unlabelled and deliberately unscaled against anything but
 * itself. It answers one question, "is this source busier or quieter than it
 * was", and a shape answers that faster than a number does. Anything more
 * precise belongs on the board a tap away, which has the real figures.
 *
 * The counts come from the feed already in memory rather than from a call of
 * its own, so this cannot disagree with what the other four tabs are showing.
 */

import React from 'react';
import { View } from 'react-native';
import { space, useTheme } from '../theme';

/**
 * Thirty, because that is the window the screen's own heading promises, and
 * because thirty thin bars read as a shape where fourteen fat ones read as a
 * row of blocks.
 */
const DAYS = 30;
const HEIGHT = 24;
/** A day with nothing in it still gets a mark, or the row reads as truncated. */
const FLOOR = 2;

/** How many items landed on each of the last thirty days, oldest first. */
export function dailyCounts(
  stamps: (string | null)[],
  now = new Date(),
): number[] {
  const midnight = new Date(now);
  midnight.setHours(0, 0, 0, 0);
  const buckets = new Array(DAYS).fill(0);

  for (const stamp of stamps) {
    if (!stamp) continue;
    const at = new Date(stamp);
    if (Number.isNaN(at.getTime())) continue;
    const days = Math.floor((midnight.getTime() - at.getTime()) / 86_400_000);
    // Today is `days === -1` through `0`; anything later is a stamp in the
    // future, which a provider does occasionally hand us.
    const index = DAYS - 1 - Math.max(0, days + 1);
    if (index >= 0 && index < DAYS) buckets[index] += 1;
  }
  return buckets;
}

/** Nothing to draw is nothing to draw: a row of floor bars is a chart of a lie. */
export function hasShape(counts: number[]): boolean {
  return counts.some((count) => count > 0);
}

export function Sparkline({ counts }: { counts: number[] }) {
  const c = useTheme();
  const peak = Math.max(1, ...counts);

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'flex-end',
        gap: 2,
        height: HEIGHT,
      }}
      accessibilityLabel={`Volume over the last ${counts.length} days`}
    >
      {counts.map((count, index) => (
        <View
          key={index}
          style={{
            flex: 1,
            height: Math.max(FLOOR, Math.round((count / peak) * HEIGHT)),
            borderRadius: 2,
            // The summary hue, which is what a board is: never a category, so
            // it can never be mistaken for a claim about urgency.
            backgroundColor: c.hue.summary,
            opacity: count === 0 ? 0.24 : 0.5 + (count / peak) * 0.5,
          }}
        />
      ))}
    </View>
  );
}

/** The gap this sits under, so callers do not each pick their own. */
export const SPARK_GAP = space.xs;
