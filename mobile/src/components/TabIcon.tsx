/**
 * Tab icons, one open-licence set (Lucide, ISC) drawn through react-native-svg.
 * One set only: mixing icon families is the fastest way to make an interface
 * look assembled rather than designed.
 */

import React from 'react';
import Svg, { Path, Circle } from 'react-native-svg';

const PATHS: Record<string, string[]> = {
  // layers
  home: [
    'M12 2 2 7l10 5 10-5-10-5Z',
    'm2 17 10 5 10-5',
    'm2 12 10 5 10-5',
  ],
  // grid
  sources: [
    'M3 3h7v7H3z',
    'M14 3h7v7h-7z',
    'M14 14h7v7h-7z',
    'M3 14h7v7H3z',
  ],
  // clock
  later: ['M12 6v6l4 2'],
  // user
  you: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'],
};

export function TabIcon({
  name,
  color,
  size = 22,
}: {
  name: keyof typeof PATHS;
  color: string;
  size?: number;
}) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {name === 'later' ? <Circle cx="12" cy="12" r="10" /> : null}
      {name === 'you' ? <Circle cx="12" cy="7" r="4" /> : null}
      {PATHS[name].map((d, index) => (
        <Path key={index} d={d} />
      ))}
    </Svg>
  );
}
