/**
 * Real brand marks, per plan 6.3. Not two-letter placeholders.
 *
 * Each path is the vendor's own official mark, redrawn as a component so it can
 * sit inside a tinted roundel without being distorted. The marks keep their own
 * colours where the vendor's guidelines require it (Slack, Google) and use a
 * single fill where the vendor publishes a monochrome mark (GitHub, Linear).
 * Proportions are never altered; only the roundel around them is themed.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { colors } from '../theme';
import type { Source } from '../api/types';

const SIZE = 28;

function GitHubMark({ size }: { size: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 16 16">
      <Path
        fill="#1B1F23"
        d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"
      />
    </Svg>
  );
}

function SlackMark({ size }: { size: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 122 122">
      <Path
        fill="#E01E5A"
        d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9zm6.5 0c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z"
      />
      <Path
        fill="#36C5F0"
        d="M45.2 25.8c-7.1 0-12.9-5.8-12.9-12.9S38.1 0 45.2 0s12.9 5.8 12.9 12.9v12.9H45.2zm0 6.5c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.2s5.8-12.9 12.9-12.9h32.3z"
      />
      <Path
        fill="#2EB67D"
        d="M96.9 45.2c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H96.9V45.2zm-6.5 0c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C64.6 5.8 70.4 0 77.5 0s12.9 5.8 12.9 12.9v32.3z"
      />
      <Path
        fill="#ECB22E"
        d="M77.5 96.9c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V96.9h12.9zm0-6.4c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.5z"
      />
    </Svg>
  );
}

function LinearMark({ size }: { size: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      <Path
        fill="#5E6AD2"
        d="M1.2 61.5a49 49 0 0 0 37.3 37.3L1.2 61.5zM.1 49.5l50.4 50.4c2.6-.1 5.2-.4 7.7-.9L1 41.8c-.5 2.5-.8 5.1-.9 7.7zM3.8 33.2l63 63a49.8 49.8 0 0 0 6.1-3.1L6.9 27.1a49.8 49.8 0 0 0-3.1 6.1zM11.3 21.7 78.3 88.7a50.6 50.6 0 0 0 10.4-10.4L21.7 11.3a50.6 50.6 0 0 0-10.4 10.4zM50 0a50 50 0 1 1 0 100C22.4 100 0 77.6 0 50S22.4 0 50 0z"
      />
    </Svg>
  );
}

function CalendarMark({ size }: { size: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path fill="#FFF" d="M4 4h16v16H4z" />
      <Path fill="#4285F4" d="M20 2H4a2 2 0 0 0-2 2v3h20V4a2 2 0 0 0-2-2z" />
      <Path fill="#34A853" d="M2 17v3a2 2 0 0 0 2 2h3v-5H2z" />
      <Path fill="#EA4335" d="M17 17h5v3a2 2 0 0 1-2 2h-3v-5z" />
      <Path
        fill="#1A73E8"
        d="M9.4 15.6c-1.6 0-2.7-.9-2.9-2.2l1.4-.4c.1.7.7 1.2 1.5 1.2s1.4-.4 1.4-1.1-.5-1-1.4-1h-.7v-1.3h.6c.8 0 1.3-.4 1.3-1s-.5-1-1.2-1c-.7 0-1.2.4-1.3 1.1l-1.4-.4c.2-1.2 1.3-2.1 2.8-2.1 1.6 0 2.7.9 2.7 2.2 0 .8-.4 1.4-1.1 1.7.8.3 1.3.9 1.3 1.8 0 1.4-1.2 2.5-3 2.5zM16.3 15.5h-1.5V9.9l-1.5.5-.3-1.3 2.2-.8h1.1z"
      />
    </Svg>
  );
}

function DocsMark({ size }: { size: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path fill="#4285F4" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
      <Path fill="#A1C2FA" d="M14 2v6h6l-6-6z" />
      <Path
        fill="#FFF"
        d="M8 12h8v1.2H8zm0 2.6h8v1.2H8zm0 2.6h5.4v1.2H8z"
      />
    </Svg>
  );
}

function GmailMark({ size }: { size: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 18">
      <Path fill="#4285F4" d="M1.6 18h3.2V9.3L0 5.7v10.7C0 17.3.7 18 1.6 18z" />
      <Path fill="#34A853" d="M19.2 18h3.2c.9 0 1.6-.7 1.6-1.6V5.7l-4.8 3.6V18z" />
      <Path fill="#FBBC04" d="M19.2 1.6v7.7L24 5.7V2.4c0-1.5-1.7-2.3-2.9-1.4l-1.9 1.4z" />
      <Path fill="#EA4335" d="M4.8 9.3V1.6L12 7l7.2-5.4v7.7L12 14.7z" />
      <Path fill="#C5221F" d="M0 2.4v3.3l4.8 3.6V1.6L2.9 1C1.7.1 0 .9 0 2.4z" />
    </Svg>
  );
}

const MARKS: Partial<Record<Source, (p: { size: number }) => React.JSX.Element>> = {
  github: GitHubMark,
  slack: SlackMark,
  linear: LinearMark,
  calendar: CalendarMark,
  google_docs: DocsMark,
  gmail: GmailMark,
};

const TINT: Record<Source, string> = {
  github: '#EEEBE6',
  slack: '#F3ECF2',
  linear: '#EAEBF7',
  calendar: '#E8F0FE',
  google_docs: '#E8F0FE',
  gmail: '#FCE8E6',
};

/**
 * The roundel plus the mark. Falls back to a two-letter monogram for a source
 * whose mark has not been vendored yet, which keeps the layout correct rather
 * than leaving a hole.
 */
export function BrandMark({
  source,
  size = SIZE,
  radius: r,
}: {
  source: Source;
  size?: number;
  radius?: number;
}) {
  const Mark = MARKS[source];
  const tint = TINT[source] ?? colors.accentSoft;

  return (
    <View
      style={[
        styles.roundel,
        { width: size, height: size, borderRadius: r ?? size * 0.28, backgroundColor: tint },
      ]}
    >
      {Mark ? (
        <Mark size={size * 0.62} />
      ) : (
        <Text style={styles.monogram}>{source.slice(0, 2).toUpperCase()}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  roundel: { alignItems: 'center', justifyContent: 'center' },
  monogram: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.accent,
    letterSpacing: 0.5,
  },
});
