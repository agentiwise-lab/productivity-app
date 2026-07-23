/**
 * Sources: a menu of every integration, matching the mockup's Sources screen.
 *
 * Every supported source has a row whether or not it is connected. A list built
 * from whatever is in the feed cannot tell a quiet integration from one that
 * was never set up, and cannot show the user what they are missing.
 *
 * Status and counts are separate concerns: the skeleton renders immediately
 * with all six rows, and each row's status fills in when the connection check
 * returns. The list never appears empty while it is loading.
 */

import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type } from '../theme';
import { Header } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import type { SourceInfo } from '../api/types';

interface Props {
  sources: SourceInfo[];
  loadingStatus: boolean;
  onOpen: (source: SourceInfo) => void;
  onConnect: (source: SourceInfo) => void;
}

/** What this source is currently asking of you, in the source's own terms. */
function describe(info: SourceInfo, loading: boolean): string {
  if (loading) return 'Checking connection...';
  if (info.status === 'disconnected') return 'Not connected yet';
  if (info.status === 'expired') return 'Access expired, tap to reconnect';
  if (info.status === 'error') return "Couldn't check this connection";
  if (info.count === 0) return 'Nothing needs you';
  const parts = [`${info.count} need${info.count === 1 ? 's' : ''} you`];
  if (info.urgent > 0) parts.push(`${info.urgent} urgent`);
  return parts.join(' · ');
}

export function SourcesScreen({
  sources,
  loadingStatus,
  onOpen,
  onConnect,
}: Props) {
  const total = sources.reduce((sum, info) => sum + info.count, 0);
  const connected = sources.filter((info) => info.status === 'connected').length;

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Header title="Sources" subtitle="Tap one to go deeper" rightGlyph="+" />
      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.summary}>
          <Text style={styles.summaryValue}>{total}</Text>
          <Text style={styles.summaryLabel}>
            need you, across {connected} connected{' '}
            {connected === 1 ? 'source' : 'sources'}
          </Text>
        </View>

        {sources.map((info) => {
          const broken = info.status === 'expired' || info.status === 'error';
          const off = info.status === 'disconnected';
          return (
            <Pressable
              key={info.source}
              onPress={() => (off || broken ? onConnect(info) : onOpen(info))}
              style={styles.row}
            >
              <BrandMark source={info.source} size={s(24)} radius={s(7)} />
              <View style={styles.rowBody}>
                <Text style={[styles.rowTitle, off && styles.rowTitleOff]}>
                  {info.label}
                </Text>
                <Text style={[styles.rowSub, broken && styles.rowSubBad]}>
                  {describe(info, loadingStatus)}
                </Text>
              </View>
              {loadingStatus ? (
                <View style={styles.skeletonPill} />
              ) : off || broken ? (
                <Text style={[styles.action, broken && styles.actionBad]}>
                  {off ? 'Connect' : 'Fix'}
                </Text>
              ) : (
                <Text style={styles.count}>{info.count}</Text>
              )}
            </Pressable>
          );
        })}

        <Text style={styles.footnote}>
          Connecting an account opens the provider's own sign-in. Nothing is
          stored here beyond the connection itself.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  body: { paddingBottom: s(30) },
  summary: {
    marginHorizontal: s(13),
    marginTop: s(11),
    marginBottom: s(6),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(14),
    paddingHorizontal: s(12),
    paddingVertical: s(11),
  },
  summaryValue: { fontFamily: 'Menlo', fontSize: s(22), fontWeight: '600', color: colors.fg },
  summaryLabel: { ...type.rowSub, marginTop: s(2) },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(9),
    paddingHorizontal: s(16),
    paddingTop: s(9),
    paddingBottom: s(10),
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
  },
  rowBody: { flex: 1 },
  rowTitle: { ...type.rowTitle, fontWeight: '600', color: colors.fg },
  rowTitleOff: { color: colors.dim },
  rowSub: { ...type.rowSub, marginTop: s(1) },
  rowSubBad: { color: colors.urgent },
  count: { ...type.groupCount, color: colors.fg },
  action: { ...type.rowSub, fontWeight: '600', color: colors.accent },
  actionBad: { color: colors.urgent },
  skeletonPill: {
    width: s(34),
    height: s(11),
    borderRadius: s(6),
    backgroundColor: colors.line,
  },
  footnote: {
    ...type.rowSub,
    paddingHorizontal: s(16),
    paddingTop: s(16),
  },
});
