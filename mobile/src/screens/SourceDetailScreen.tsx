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

import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type } from '../theme';
import { BrandMark } from '../components/BrandMark';
import type { SourceDashboard, StatLine } from '../api/types';

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
          <Text style={styles.title}>{dashboard?.label ?? 'Source'}</Text>
        </View>
        <View style={styles.back} />
      </View>

      {loading || !dashboard ? (
        <View style={styles.pad}>
          <View style={styles.tiles}>
            {[0, 1, 2, 3].map((n) => (
              <View key={n} style={styles.tileSkeleton} />
            ))}
          </View>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          <View style={styles.tiles}>
            {dashboard.headline.map((stat) => (
              <View key={stat.label} style={styles.tile}>
                <Text style={styles.tileValue}>
                  {stat.value_label ?? stat.value}
                </Text>
                <Text style={styles.tileLabel}>{stat.label}</Text>
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
      <Text style={styles.rowValue}>{line.value_label ?? line.value}</Text>
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
  title: { fontSize: s(15), fontWeight: '700', color: colors.fg },
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
    flexGrow: 1,
    flexBasis: '30%',
    minHeight: s(56),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(11),
    paddingHorizontal: s(10),
    paddingVertical: s(9),
    justifyContent: 'center',
  },
  tileSkeleton: {
    flexGrow: 1,
    flexBasis: '30%',
    height: s(56),
    borderRadius: s(11),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  tileValue: { fontFamily: 'Menlo', fontSize: s(17), fontWeight: '600', color: colors.fg },
  tileLabel: { ...type.rowTitle, fontWeight: '600', color: colors.fg, marginTop: s(3) },
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
