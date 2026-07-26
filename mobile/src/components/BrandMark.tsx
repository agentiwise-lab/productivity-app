/**
 * A source's own mark, in its own colours.
 *
 * This is one of exactly two exemptions from "colour is the category". A mark
 * is identity rather than priority, and it never occupies a position where a
 * category signal lives, so it cannot be misread as one.
 *
 * **These are the real marks.** The set that shipped first was six hand-drawn
 * approximations, each flattened to a single path in a single invented colour:
 * GitHub came out purple, Slack was one blue lobe instead of four, and Gmail
 * was a plain red envelope. An approximated logo is the one thing on a screen a
 * reader can identify as wrong without knowing anything about design, and it
 * made the whole app read as a drawing of an app. Geometry is now Simple Icons
 * (CC0) for the two monochrome brands, and the vendors' own published marks for
 * the four that are polychrome.
 *
 * Five sizes and no others, each with its own radius and glyph box, because a
 * mark scaled to an arbitrary size stops sitting on the same optical baseline
 * as the text beside it.
 */

import React from 'react';
import { Text, View } from 'react-native';
import Svg, { G, Path } from 'react-native-svg';
import { fonts, useTheme } from '../theme';
import type { Source } from '../api/types';

/** One coloured shape of a mark. */
interface Shape {
  d: string;
  /** A literal brand colour, or `ink` for a brand whose mark inverts. */
  fill: string | 'ink';
}

interface Mark {
  /** The mark's own coordinate space, which is rarely 24 and never square. */
  viewBox: string;
  shapes: Shape[];
}

/** GitHub and Linear: Simple Icons, CC0. The rest: the vendors' own marks. */
const MARKS: Record<Source, Mark> = {
  // GitHub has no chromatic mark. It is black on light and white on dark, which
  // is the one brand here whose own guidance asks for an inversion.
  github: {
    viewBox: '0 0 24 24',
    shapes: [
      {
        fill: 'ink',
        d: 'M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12',
      },
    ],
  },

  // Four lobes, four colours. Drawing it in one colour loses the only thing
  // that makes the mark readable at 20pt.
  slack: {
    viewBox: '0 0 24 24',
    shapes: [
      {
        fill: '#E01E5A',
        d: 'M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z',
      },
      {
        fill: '#36C5F0',
        d: 'M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z',
      },
      {
        fill: '#2EB67D',
        d: 'M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z',
      },
      {
        fill: '#ECB22E',
        d: 'M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z',
      },
    ],
  },

  linear: {
    viewBox: '0 0 24 24',
    shapes: [
      {
        fill: '#5E6AD2',
        d: 'M2.886 4.18A11.982 11.982 0 0 1 11.99 0C18.624 0 24 5.376 24 12.009c0 3.64-1.62 6.903-4.18 9.105L2.887 4.18ZM1.817 5.626l16.556 16.556c-.524.33-1.075.62-1.65.866L.951 7.277c.247-.575.537-1.126.866-1.65ZM.322 9.163l14.515 14.515c-.71.172-1.443.282-2.195.322L0 11.358a12 12 0 0 1 .322-2.195Zm-.17 4.862 9.823 9.824a12.02 12.02 0 0 1-9.824-9.824Z',
      },
    ],
  },

  // The envelope is five shapes: two flaps, two shoulders and the M itself.
  gmail: {
    viewBox: '52 42 88 66',
    shapes: [
      { fill: '#4285F4', d: 'M58 108h14V74L52 59v43c0 3.32 2.69 6 6 6' },
      { fill: '#34A853', d: 'M120 108h14c3.32 0 6-2.69 6-6V59l-20 15' },
      { fill: '#FBBC04', d: 'M120 48v26l20-15v-8c0-7.42-8.47-11.65-14.4-7.2' },
      { fill: '#EA4335', d: 'M72 74V48l24 18 24-18v26L96 92' },
      {
        fill: '#C5221F',
        d: 'M52 51v8l20 15V48l-5.6-4.2c-5.94-4.45-14.4-.22-14.4 7.2',
      },
    ],
  },

  // The source connects Google Drive now (native comment/share triggers), so it
  // wears Drive's own tricolor triangle, not the old blue Docs page.
  google_docs: {
    viewBox: '0 0 87.3 78',
    shapes: [
      {
        fill: '#0066DA',
        d: 'M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0c0 1.55.4 3.1 1.2 4.5z',
      },
      {
        fill: '#00AC47',
        d: 'M43.65 25L29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3L1.2 48.5C.4 49.9 0 51.45 0 53h27.5z',
      },
      {
        fill: '#EA4335',
        d: 'M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75L86.1 57.4c.8-1.4 1.2-2.95 1.2-4.5H59.798l5.852 11.5z',
      },
      {
        fill: '#00832D',
        d: 'M43.65 25L57.4 1.2C56.05.4 54.5 0 52.9 0H34.4c-1.6 0-3.15.45-4.5 1.2z',
      },
      {
        fill: '#2684FC',
        d: 'M59.8 53H27.5L13.75 76.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z',
      },
      {
        fill: '#FFBA00',
        d: 'M73.4 26.5l-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25 59.8 53h27.45c0-1.55-.4-3.1-1.2-4.5z',
      },
    ],
  },

  // Published at 200 square with the artwork offset by 3.75, which the group
  // transform below restores rather than the numbers being rewritten.
  calendar: {
    viewBox: '0 0 200 200',
    shapes: [
      {
        fill: '#FFFFFF',
        d: 'M148.882,43.618l-47.368-5.263l-57.895,5.263L38.355,96.25l5.263,52.632l52.632,6.579l52.632-6.579l5.263-53.947L148.882,43.618z',
      },
      {
        fill: '#1A73E8',
        d: 'M65.211,125.276c-3.934-2.658-6.658-6.539-8.145-11.671l9.132-3.763c0.829,3.158,2.276,5.605,4.342,7.342 c2.053,1.737,4.553,2.592,7.474,2.592c2.987,0,5.553-0.908,7.697-2.724s3.224-4.132,3.224-6.934c0-2.868-1.132-5.211-3.395-7.026 s-5.105-2.724-8.5-2.724h-5.276v-9.039H76.5c2.921,0,5.382-0.789,7.382-2.368c2-1.579,3-3.737,3-6.487 c0-2.447-0.895-4.395-2.684-5.855s-4.053-2.197-6.803-2.197c-2.684,0-4.816,0.711-6.395,2.145s-2.724,3.197-3.447,5.276 l-9.039-3.763c1.197-3.395,3.395-6.395,6.618-8.987c3.224-2.592,7.342-3.895,12.342-3.895c3.697,0,7.026,0.711,9.974,2.145 c2.947,1.434,5.263,3.421,6.934,5.947c1.671,2.539,2.5,5.382,2.5,8.539c0,3.224-0.776,5.947-2.329,8.184 c-1.553,2.237-3.461,3.947-5.724,5.145v0.539c2.987,1.25,5.421,3.158,7.342,5.724c1.908,2.566,2.868,5.632,2.868,9.211 s-0.908,6.776-2.724,9.579c-1.816,2.803-4.329,5.013-7.513,6.618c-3.197,1.605-6.789,2.421-10.776,2.421 C73.408,129.263,69.145,127.934,65.211,125.276z',
      },
      {
        fill: '#1A73E8',
        d: 'M121.25,79.961l-9.974,7.25l-5.013-7.605l17.987-12.974h6.895v61.197h-9.895L121.25,79.961z',
      },
      {
        fill: '#EA4335',
        d: 'M148.882,196.25l47.368-47.368l-23.684-10.526l-23.684,10.526l-10.526,23.684L148.882,196.25z',
      },
      {
        fill: '#34A853',
        d: 'M33.092,172.566l10.526,23.684h105.263v-47.368H43.618L33.092,172.566z',
      },
      {
        fill: '#4285F4',
        d: 'M12.039-3.75C3.316-3.75-3.75,3.316-3.75,12.039v136.842l23.684,10.526l23.684-10.526V43.618h105.263l10.526-23.684L148.882-3.75H12.039z',
      },
      {
        fill: '#188038',
        d: 'M-3.75,148.882v31.579c0,8.724,7.066,15.789,15.789,15.789h31.579v-47.368H-3.75z',
      },
      {
        fill: '#FBBC04',
        d: 'M148.882,43.618v105.263h47.368V43.618l-23.684-10.526L148.882,43.618z',
      },
      {
        fill: '#1967D2',
        d: 'M196.25,43.618V12.039c0-8.724-7.066-15.789-15.789-15.789h-31.579v47.368H196.25z',
      },
    ],
  },
};

/**
 * size, tile radius, glyph box. Five, and only five.
 *
 * The glyph is a little over half the tile at every step, which is the ratio a
 * platform icon sits at inside its own container. It used to be exactly half at
 * 16 and 20, where the mark then had too little ink to be identifiable.
 */
const SIZES = {
  16: { radius: 4, glyph: 10 },
  20: { radius: 4, glyph: 12 },
  24: { radius: 8, glyph: 14 },
  32: { radius: 8, glyph: 19 },
  44: { radius: 12, glyph: 26 },
} as const;

export type MarkSize = keyof typeof SIZES;

export function BrandMark({
  source,
  size = 32,
}: {
  source: Source;
  size?: MarkSize;
}) {
  const c = useTheme();
  const { radius, glyph } = SIZES[size];
  const mark = MARKS[source];

  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        backgroundColor: c.overlay,
        borderWidth: 0.5,
        borderColor: c.hairline,
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      <Svg width={glyph} height={glyph} viewBox={mark.viewBox}>
        {/* Calendar is the one mark published against an origin of its own.
            `transform` rather than the `translateX` prop, which react-native-svg
            passes straight through to the DOM on web and React then rejects. */}
        <G transform={source === 'calendar' ? 'translate(3.75 3.75)' : undefined}>
          {mark.shapes.map((shape, index) => (
            <Path
              key={index}
              d={shape.d}
              fill={shape.fill === 'ink' ? c.high : shape.fill}
            />
          ))}
        </G>
      </Svg>
    </View>
  );
}

/**
 * Initials, where there is a person rather than a service. Same tile, same
 * ladder, round instead of square so the two are never confused.
 */
export function Avatar({
  name,
  size = 32,
}: {
  name: string | null;
  size?: 24 | 32 | 44;
}) {
  const c = useTheme();
  const initials = (name ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
  const fontSize = size === 44 ? 15 : size === 24 ? 11 : 13;
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: 999,
        backgroundColor: c.overlay,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ fontFamily: fonts.sansSemi, fontSize, color: c.mid }}>
        {initials || '?'}
      </Text>
    </View>
  );
}
