/**
 * The category colour, arriving as light from beneath the screen edge.
 *
 * A 3pt line down the left of a card says "urgent" the way a form field says
 * it. This says it the way a room does. Two layers rather than one: a wide
 * ellipse centred below the bottom edge, which reads as a source of light off
 * screen, and a flat linear over the bottom eighth so the falloff does not go
 * abruptly matte where the ellipse has already run out.
 *
 * Light mode halves every stop and drops the linear entirely. A light field
 * carries a tint much further before it stops reading as a glow and starts
 * reading as a fill.
 */

import React, { useId } from 'react';
import { View } from 'react-native';
import Svg, { Defs, LinearGradient, RadialGradient, Rect, Stop } from 'react-native-svg';
import { bloom, useTheme, type Category } from '../theme';

const HEIGHT = 340;

export function Bloom({ category, width }: { category: Category; width: number }) {
  const c = useTheme();
  const { rgb, stops, locations, linear } = bloom(c, category);
  // `rgb` is the bare "r,g,b" triple the washes need for their alpha strings.
  // An SVG stop needs a colour, not three numbers, and an invalid stop-color
  // renders as fully transparent without warning.
  const colour = `rgb(${rgb})`;
  // Gradient ids live in one global namespace on the web renderer, so two
  // cards sharing an id means the second one silently paints the first one's
  // colour. Every instance gets its own.
  const id = useId().replace(/:/g, '');

  return (
    <View
      pointerEvents="none"
      style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: HEIGHT }}
    >
      <Svg width={width} height={HEIGHT}>
        <Defs>
          {/* 150% wide and 74% tall, centred at 50% across and 110% down, so
              the brightest point sits just off the bottom of the screen.
              An SVG radial gradient is a circle: the ellipse comes from the
              transform, because `rx` and `ry` are not part of the element and
              are silently dropped, which leaves a small circle mostly below
              the box and a bloom nobody can see. */}
          <RadialGradient {...ellipse(width * 1.5, HEIGHT * 0.74, width / 2, HEIGHT * 1.1)} id={`${id}b`}>
            <Stop offset="0" stopColor={colour} stopOpacity={alpha(stops[0])} />
            <Stop
              offset={String(locations[1])}
              stopColor={colour}
              stopOpacity={alpha(stops[1])}
            />
            <Stop offset={String(locations[2])} stopColor={colour} stopOpacity={0} />
          </RadialGradient>
          <LinearGradient id={`${id}l`} x1="0" y1="1" x2="0" y2="0">
            <Stop offset="0" stopColor={colour} stopOpacity={linear ? alpha(linear) : 0} />
            <Stop offset="0.58" stopColor={colour} stopOpacity={0} />
          </LinearGradient>
        </Defs>
        {linear ? <Rect width={width} height={HEIGHT} fill={`url(#${id}l)`} /> : null}
        <Rect width={width} height={HEIGHT} fill={`url(#${id}b)`} />
      </Svg>
    </View>
  );
}

/**
 * The top wash on a feed card. The review asked why the colour did not start at
 * the very top of the screen; the answer is that the card now bleeds under the
 * status bar, and this is what fills that space.
 */
export function TopTint({
  category,
  width,
  height = 320,
}: {
  category: Category;
  width: number;
  height?: number;
}) {
  const c = useTheme();
  const colour = `rgb(${c.rgb[category]})`;
  const peak = c.mode === 'light' ? 0.09 : 0.14;
  const id = useId().replace(/:/g, '');
  return (
    <View
      pointerEvents="none"
      style={{ position: 'absolute', left: 0, right: 0, top: 0, height }}
    >
      <Svg width={width} height={height}>
        <Defs>
          <RadialGradient {...ellipse(width * 1.2, height * 0.8, width * 0.12, 0)} id={`${id}t`}>
            <Stop offset="0" stopColor={colour} stopOpacity={peak} />
            <Stop offset="0.6" stopColor={colour} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Rect width={width} height={height} fill={`url(#${id}t)`} />
      </Svg>
    </View>
  );
}

/**
 * An elliptical radial gradient, as the props a circular one needs to become
 * it: radius on the long axis, squashed to the short one about its own centre.
 */
function ellipse(rx: number, ry: number, cx: number, cy: number) {
  return {
    gradientUnits: 'userSpaceOnUse' as const,
    cx,
    cy,
    r: rx,
    gradientTransform: `translate(${cx} ${cy}) scale(1 ${ry / rx}) translate(${-cx} ${-cy})`,
  };
}

/** Pull the alpha back out of an `rgba(r,g,b,a)` string. */
function alpha(colour: string): number {
  const match = colour.match(/,([\d.]+)\)$/);
  return match ? Number(match[1]) : 1;
}
