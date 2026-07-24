/**
 * One source's dashboard: what has been going on here.
 *
 * The header carries the source's own brand mark rather than its name in text,
 * so it reads the way the rest of the app does. Headline tiles first, then a
 * breakdown whose meaning is named per source: repositories for GitHub,
 * projects for Linear, most-frequent meetings for Calendar, top senders for
 * Gmail, busiest channels for Slack.
 *
 * A breakdown row is tappable only when it has somewhere to go. A repository
 * opens on GitHub and a sender opens that Gmail search; a Calendar frequency
 * line is a summary and stays inert, which the missing chevron signals.
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  Linking,
  Animated,
  Easing,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type } from '../theme';
import { BrandMark } from '../components/BrandMark';
import type { Source, SourceDashboard, StatLine } from '../api/types';

/**
 * What a board is doing while it loads, in the source's own terms.
 *
 * A dashboard is counted live at the provider, so it is genuinely slow: Slack
 * asks about every channel it can see. Four grey rectangles said none of that,
 * so a board that was working looked like a board that was broken.
 */
const LOADING_NOTE: Partial<Record<Source, string>> = {
  slack: 'Counting messages across every channel and DM. This one takes a moment.',
  github: 'Reading commits and pull requests across your repositories.',
  linear: 'Reading your issues and their states.',
  gmail: 'Grouping the last 30 days by sender.',
  calendar: 'Reading the last 30 days of meetings.',
};

/** A slow pulse, so the screen is visibly alive rather than merely empty. */
function usePulse() {
  const value = useRef(new Animated.Value(0.4)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(value, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(value, {
          toValue: 0.4,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [value]);
  return value;
}

function LoadingBoard({ source }: { source?: Source }) {
  const pulse = usePulse();
  return (
    <ScrollView contentContainerStyle={styles.body}>
      <View style={styles.tiles}>
        {[0, 1, 2, 3, 4, 5].map((n) => (
          <Animated.View key={n} style={[styles.tileSkeleton, { opacity: pulse }]} />
        ))}
      </View>
      <Text style={styles.loadingNote}>
        {(source && LOADING_NOTE[source]) ?? 'Counting the last 30 days.'}
      </Text>
      {[0, 1, 2, 3, 4].map((n) => (
        <Animated.View key={n} style={[styles.rowSkeleton, { opacity: pulse }]} />
      ))}
    </ScrollView>
  );
}

export function SourceDetailScreen({
  dashboard,
  loading,
  onBack,
}: {
  dashboard: SourceDashboard | null;
  loading: boolean;
  onBack: () => void;
}) {
  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <View style={styles.header}>
        <Pressable onPress={onBack} hitSlop={14} style={styles.back}>
          <Text style={styles.backText}>‹</Text>
        </Pressable>
        <View style={styles.headerCentre}>
          {dashboard ? (
            <BrandMark source={dashboard.source} size={s(22)} radius={s(7)} />
          ) : null}
          <View>
            <Text style={styles.title}>{dashboard?.label ?? 'Source'}</Text>
            <Text style={styles.subtitle}>Last 30 days</Text>
          </View>
        </View>
        <View style={styles.back} />
      </View>

      {loading || !dashboard ? (
        <LoadingBoard source={dashboard?.source} />
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          <View style={styles.tiles}>
            {dashboard.headline.map((stat) => (
              <View key={stat.label} style={styles.tile}>
                <Text style={styles.tileValue} numberOfLines={1}>
                  {stat.value_label ?? stat.value}
                </Text>
                <Text style={styles.tileLabel} numberOfLines={1}>
                  {stat.label}
                </Text>
                {stat.detail ? (
                  <Text style={styles.tileDetail}>{stat.detail}</Text>
                ) : null}
              </View>
            ))}
          </View>

          {dashboard.breakdown.length > 0 ? (
            <>
              <Text style={styles.divider}>{dashboard.breakdown_title}</Text>
              {dashboard.breakdown.map((line, index) => (
                <Row key={`${line.label}-${index}`} line={line} source={dashboard.source} />
              ))}
            </>
          ) : (
            <Text style={styles.quiet}>
              Nothing recorded here in the last 30 days.
            </Text>
          )}

          {dashboard.unavailable.length > 0 ? (
            <Text style={styles.unavailable}>
              Couldn't load: {dashboard.unavailable.join(', ')}.
            </Text>
          ) : null}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function Row({ line, source }: { line: StatLine; source: SourceDashboard['source'] }) {
  const tappable = !!line.url;
  const body = (
    <>
      <BrandMark source={source} size={s(22)} radius={s(6)} />
      <View style={styles.rowBody}>
        <Text style={styles.rowTitle} numberOfLines={1}>
          {line.label}
        </Text>
        {line.detail ? <Text style={styles.rowSub}>{line.detail}</Text> : null}
      </View>
      {line.value_label !== '' ? (
        <Text style={styles.rowValue}>
          {line.value_label ?? line.value}
        </Text>
      ) : null}
      {tappable ? <Text style={styles.chevron}>{'›'}</Text> : null}
    </>
  );
  if (!tappable) return <View style={styles.row}>{body}</View>;
  return (
    <Pressable
      onPress={() => line.url && Linking.openURL(line.url)}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
    >
      {body}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: s(10),
    paddingTop: s(4),
    paddingBottom: s(7),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  back: { width: s(26), alignItems: 'center' },
  backText: { fontSize: s(22), color: colors.accent, lineHeight: s(24) },
  headerCentre: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: s(7) },
  title: { fontSize: s(14), fontWeight: '700', color: colors.fg, lineHeight: s(15) },
  subtitle: { fontFamily: 'Menlo', fontSize: s(8), letterSpacing: 0.5, color: colors.dim },
  body: { paddingBottom: s(30) },
  pad: { padding: s(13) },
  tiles: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: s(6),
    paddingHorizontal: s(13),
    paddingTop: s(11),
  },
  tile: {
    // Two per row. Three was too narrow for labels like "Messages" or
    // "Remaining", which wrapped their last letter onto a second line. No
    // flexGrow, so a lone fifth tile stays half-width rather than stretching
    // across the whole row.
    flexGrow: 0,
    flexBasis: '48.5%',
    minHeight: s(54),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(11),
    paddingHorizontal: s(10),
    paddingVertical: s(9),
    justifyContent: 'center',
  },
  tileSkeleton: {
    flexGrow: 0,
    flexBasis: '48.5%',
    height: s(56),
    borderRadius: s(11),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  rowSkeleton: {
    height: s(44),
    marginHorizontal: s(13),
    marginBottom: s(7),
    borderRadius: s(12),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  loadingNote: {
    ...type.rowSub,
    paddingHorizontal: s(16),
    paddingTop: s(14),
    paddingBottom: s(10),
  },
  tileValue: { fontFamily: 'Menlo', fontSize: s(17), fontWeight: '600', color: colors.fg },
  tileLabel: { ...type.rowTitle, fontWeight: '600', color: colors.fg, marginTop: s(3) },
  // (labels are single-line via numberOfLines on the element)
  tileDetail: { ...type.rowSub, fontSize: s(9.5), marginTop: s(1) },
  divider: {
    ...type.divider,
    paddingHorizontal: s(16),
    paddingTop: s(18),
    paddingBottom: s(6),
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(10),
    marginHorizontal: s(13),
    marginBottom: s(7),
    paddingHorizontal: s(12),
    paddingVertical: s(11),
    backgroundColor: colors.surface,
    borderRadius: s(12),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  rowPressed: { opacity: 0.6 },
  rowBody: { flex: 1 },
  rowTitle: { ...type.rowTitle, fontWeight: '600', color: colors.fg },
  rowSub: { ...type.rowSub, marginTop: s(1) },
  rowValue: { ...type.groupCount, color: colors.fg },
  chevron: { fontSize: s(15), color: colors.dim, marginLeft: s(1) },
  quiet: { ...type.rowSub, padding: s(16) },
  unavailable: { ...type.rowSub, color: colors.urgent, padding: s(16) },
});
