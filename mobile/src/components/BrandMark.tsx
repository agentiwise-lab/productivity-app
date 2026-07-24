/**
 * A source's own mark, in its own colour.
 *
 * This is one of exactly two exemptions from "colour is the category". A mark
 * is identity rather than priority, and it never occupies a position where a
 * category signal lives, so it cannot be misread as one. Monochrome marks were
 * tried and rejected: they cost the instant recognition that is the only
 * reason to draw a mark instead of writing the word.
 *
 * Paths are Simple Icons, CC0.
 *
 * Five sizes and no others, each with its own radius and glyph box, because a
 * mark scaled to an arbitrary size stops sitting on the same optical baseline
 * as the text beside it.
 */

import React from 'react';
import { Text, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { fonts, useTheme } from '../theme';
import type { Source } from '../api/types';

const PATHS: Record<Source, string> = {
  github:
    'M12 2C6.5 2 2 6.6 2 12.3c0 4.5 2.9 8.3 6.8 9.7.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.4-3.4-1.4-.4-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.6 2.4 1.1 3 .9.1-.7.3-1.1.6-1.4-2.2-.3-4.6-1.2-4.6-5.2 0-1.1.4-2 1-2.8-.1-.3-.4-1.3.1-2.7 0 0 .8-.3 2.7 1.1.8-.2 1.7-.3 2.5-.3s1.7.1 2.5.3c1.9-1.4 2.7-1.1 2.7-1.1.5 1.4.2 2.4.1 2.7.6.8 1 1.7 1 2.8 0 4-2.4 4.9-4.6 5.2.3.3.7 1 .7 2v2.9c0 .3.2.6.7.5 3.9-1.4 6.8-5.2 6.8-9.7C22 6.6 17.5 2 12 2z',
  slack:
    'M6 15.2a2.1 2.1 0 1 1-2.1-2.1H6v2.1zm1.1 0a2.1 2.1 0 0 1 4.2 0v5.2a2.1 2.1 0 0 1-4.2 0v-5.2zM9.2 6.1a2.1 2.1 0 1 1 2.1-2.1v2.1H9.2zm0 1.1a2.1 2.1 0 0 1 0 4.2H4a2.1 2.1 0 0 1 0-4.2h5.2zM18 9.3a2.1 2.1 0 1 1 2.1 2.1H18V9.3zm-1.1 0a2.1 2.1 0 0 1-4.2 0V4.1a2.1 2.1 0 0 1 4.2 0v5.2zM14.8 18a2.1 2.1 0 1 1-2.1 2.1V18h2.1zm0-1.1a2.1 2.1 0 0 1 0-4.2H20a2.1 2.1 0 0 1 0 4.2h-5.2z',
  linear:
    'M2.2 13.9a10 10 0 0 0 7.9 7.9L2.2 13.9zM2 11.6 12.4 22a10 10 0 0 0 2.4-.5L2.5 9.2a10 10 0 0 0-.5 2.4zm1.3-4.2 13.3 13.3a10 10 0 0 0 1.7-1.3L4.6 5.7a10 10 0 0 0-1.3 1.7zM6.3 3.6a10 10 0 0 1 14.1 14.1L6.3 3.6z',
  gmail:
    'M2 6.4c0-1 .8-1.8 1.8-1.8h.9L12 10.9l7.3-6.3h.9c1 0 1.8.8 1.8 1.8v11.2c0 1-.8 1.8-1.8 1.8h-1.8V9.5L12 14.9 5.6 9.5v9.9H3.8c-1 0-1.8-.8-1.8-1.8V6.4z',
  google_docs:
    'M14 2H6.4C5.1 2 4 3.1 4 4.4v15.2C4 20.9 5.1 22 6.4 22h11.2c1.3 0 2.4-1.1 2.4-2.4V8l-6-6zm-1 7V3.6L18.4 9H13zM8 12.4h8v1.4H8v-1.4zm0 3.2h8V17H8v-1.4zM8 9h4v1.4H8V9z',
  calendar:
    'M6.6 2v2H4.8C3.8 4 3 4.8 3 5.8v13.4C3 20.2 3.8 21 4.8 21h14.4c1 0 1.8-.8 1.8-1.8V5.8c0-1-.8-1.8-1.8-1.8h-1.8V2h-1.8v2H8.4V2H6.6zM4.8 8.6h14.4v10.6H4.8V8.6zm2.6 2.4v2.2h2.2V11H7.4zm4.4 0v2.2H14V11h-2.2zm4.4 0v2.2h2.2V11h-2.2zM7.4 15.2v2.2h2.2v-2.2H7.4zm4.4 0v2.2H14v-2.2h-2.2z',
};

/** size, tile radius, glyph box. Five, and only five. */
const SIZES = {
  16: { radius: 4, glyph: 11 },
  20: { radius: 4, glyph: 12 },
  24: { radius: 8, glyph: 14 },
  32: { radius: 8, glyph: 18 },
  44: { radius: 12, glyph: 24 },
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
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        backgroundColor: c.overlay,
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      {/* A one-pixel specular edge along the top. It is what stops the tile
          reading as a flat grey square at 16pt, where the glyph inside it is
          too small to carry the shape on its own. */}
      <View
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 1,
          backgroundColor:
            c.mode === 'dark' ? 'rgba(255,255,255,0.20)' : 'rgba(18,32,31,0.12)',
        }}
      />
      <Svg width={glyph} height={glyph} viewBox="0 0 24 24">
        <Path d={PATHS[source]} fill={c.brand[source]} />
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
