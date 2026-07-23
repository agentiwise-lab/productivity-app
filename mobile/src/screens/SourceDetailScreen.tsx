/**
 * One source's dashboard: what has been going on here.
 *
 * Deliberately a different question from the feed's "what needs me now". The
 * feed is short by design, and a source with two hundred quiet notifications
 * and one real ask should be able to say so. Headline figures first, then the
 * breakdown that means something for that particular source: repositories for
 * GitHub, senders for Gmail, meetings for Calendar.
 *
 * Anything that could not be loaded is named. A confident zero where a call
 * failed is worse than an admission.
 */

import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type } from '../theme';
import { BrandMark } from '../components/BrandMark';
import type { SourceDashboard } from '../api/types';

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
          <Text style={styles.title}>{dashboard?.label ?? 'Source'}</Text>
          <Text style={styles.subtitle}>Last 30 days</Text>
        </View>
        <View style={styles.back} />
      </View>

      {loading || !dashboard ? (
        <View style={styles.pad}>
          {[0, 1, 2].map((n) => (
            <View key={n} style={styles.skeleton} />
          ))}
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          <View style={styles.headline}>
            {dashboard.headline.map((stat) => (
              <View key={stat.label} style={styles.stat}>
                <Text style={styles.statValue}>{stat.value}</Text>
                <Text style={styles.statLabel}>{stat.label}</Text>
                {stat.detail ? (
                  <Text style={styles.statDetail}>{stat.detail}</Text>
                ) : null}
              </View>
            ))}
          </View>

          {dashboard.breakdown.length > 0 ? (
            <>
              <Text style={styles.divider}>Breakdown</Text>
              {dashboard.breakdown.map((line, index) => (
                <View key={`${line.label}-${index}`} style={styles.row}>
                  <BrandMark source={dashboard.source} size={s(20)} radius={s(6)} />
                  <View style={styles.rowBody}>
                    <Text style={styles.rowTitle} numberOfLines={1}>
                      {line.label}
                    </Text>
                    {line.detail ? (
                      <Text style={styles.rowSub}>{line.detail}</Text>
                    ) : null}
                  </View>
                  <Text style={styles.rowValue}>{line.value}</Text>
                </View>
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

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: s(10),
    paddingTop: s(6),
    paddingBottom: s(8),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  back: { width: s(24), alignItems: 'center' },
  backText: { fontSize: s(20), color: colors.accent, lineHeight: s(22) },
  headerCentre: { flex: 1, alignItems: 'center' },
  title: { fontSize: s(15), fontWeight: '700', color: colors.fg },
  subtitle: { ...type.headerDate, marginTop: s(1) },
  body: { paddingBottom: s(30) },
  pad: { padding: s(13), gap: s(9) },
  skeleton: {
    height: s(52),
    borderRadius: s(12),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  headline: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: s(6),
    paddingHorizontal: s(13),
    paddingTop: s(11),
  },
  stat: {
    flexGrow: 1,
    flexBasis: '46%',
    minHeight: s(58),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(11),
    paddingHorizontal: s(11),
    paddingVertical: s(10),
    justifyContent: 'center',
  },
  statValue: { fontFamily: 'Menlo', fontSize: s(20), fontWeight: '600', color: colors.fg },
  statLabel: { ...type.rowTitle, fontWeight: '600', color: colors.fg, marginTop: s(3) },
  statDetail: { ...type.rowSub, fontSize: s(9.5), marginTop: s(1) },
  divider: {
    ...type.divider,
    paddingHorizontal: s(16),
    paddingTop: s(18),
    paddingBottom: s(4),
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(9),
    paddingHorizontal: s(16),
    paddingVertical: s(9),
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
  },
  rowBody: { flex: 1 },
  rowTitle: { ...type.rowTitle, color: colors.fg },
  rowSub: { ...type.rowSub, marginTop: s(1) },
  rowValue: { ...type.groupCount, color: colors.fg },
  quiet: { ...type.rowSub, padding: s(16) },
  unavailable: { ...type.rowSub, color: colors.urgent, padding: s(16) },
});
