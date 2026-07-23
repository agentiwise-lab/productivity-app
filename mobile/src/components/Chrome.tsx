/**
 * Header, tab bar and the collapsed sticky line, matching the mockup exactly.
 *
 * The header is centred and quiet on purpose: the screen title is the least
 * interesting thing on it, so it takes one small line with the date beside it
 * rather than a large left-aligned banner competing with the content.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import { colors, s, type } from '../theme';

/**
 * A title and, where it earns its place, one line of context beneath it.
 *
 * The mockup carried a hamburger and a target glyph. Neither had anywhere to
 * go, and a control that does nothing is worse than no control: it invites a
 * tap and then ignores it. They are gone until they mean something.
 */
export function Header({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
  onLeft?: () => void;
  onRight?: () => void;
  rightGlyph?: string;
}) {
  return (
    <View style={styles.header}>
      <Text style={styles.headerTitle}>{title}</Text>
      {subtitle ? <Text style={styles.headerDate}>{subtitle}</Text> : null}
    </View>
  );
}

/**
 * What the ruler becomes once you scroll. It keeps the one fact from the ruler
 * that still matters while you are reading the feed: when the next thing is,
 * and how much room you have before it.
 */
export function StickyDay({
  time,
  label,
  free,
}: {
  time: string;
  label: string;
  free: string;
}) {
  return (
    <View style={styles.sticky}>
      <Text style={styles.stickyTime}>{time}</Text>
      <Text style={styles.stickyLabel} numberOfLines={1}>
        {label}
      </Text>
      <Text style={styles.stickyFree}>{free}</Text>
    </View>
  );
}

const TAB_ICONS: Record<string, React.ReactNode> = {
  Home: (
    <>
      <Path d="M12 2 2 7l10 5 10-5-10-5Z" />
      <Path d="m2 17 10 5 10-5" />
      <Path d="m2 12 10 5 10-5" />
    </>
  ),
  Sources: (
    <>
      <Path d="M3 3h7v7H3z" />
      <Path d="M14 3h7v7h-7z" />
      <Path d="M14 14h7v7h-7z" />
      <Path d="M3 14h7v7H3z" />
    </>
  ),
  Later: (
    <>
      <Circle cx="12" cy="12" r="10" />
      <Path d="M12 6v6l4 2" />
    </>
  ),
  You: (
    <>
      <Circle cx="12" cy="7" r="4" />
      <Path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    </>
  ),
};

export function TabIcon({
  name,
  color,
  focused,
}: {
  name: string;
  color: string;
  focused: boolean;
}) {
  return (
    <View style={[styles.tabIcon, focused && styles.tabIconOn]}>
      <Svg
        width={s(11)}
        height={s(11)}
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {TAB_ICONS[name]}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    paddingHorizontal: s(14),
    paddingTop: s(3),
    paddingBottom: s(5),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
    backgroundColor: colors.bg,
  },
  headerLeft: { width: s(20) },
  headerRight: { width: s(20), alignItems: 'flex-end' },
  headerCentre: { flex: 1, flexDirection: 'row', justifyContent: 'center', alignItems: 'baseline' },
  headerTitle: { fontSize: s(15), fontWeight: '700', letterSpacing: -0.3, color: colors.fg },
  headerDate: { ...type.headerDate, marginTop: s(1) },
  glyph: { fontSize: s(13), color: colors.dim },

  sticky: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(8),
    paddingHorizontal: s(14),
    paddingVertical: s(8),
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    shadowColor: '#20242B',
    shadowOpacity: 0.08,
    shadowRadius: s(6),
    shadowOffset: { width: 0, height: s(3) },
    elevation: 3,
    zIndex: 5,
  },
  stickyTime: {
    fontFamily: 'Menlo',
    fontSize: s(10.5),
    fontWeight: '600',
    color: colors.accent,
  },
  stickyLabel: { flex: 1, fontSize: s(11), color: colors.fg },
  stickyFree: { fontFamily: 'Menlo', fontSize: s(9.5), color: colors.dim },

  tabIcon: {
    width: s(15),
    height: s(15),
    borderRadius: s(5),
    alignItems: 'center',
    justifyContent: 'center',
    opacity: 0.55,
  },
  tabIconOn: { opacity: 1, backgroundColor: colors.accentSoft },
});
