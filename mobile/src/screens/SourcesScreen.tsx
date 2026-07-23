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
  if (info.count === 0) return 'No urgent tasks';
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

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Header title="Sources" subtitle="Last 30 days" rightGlyph="+" />
      <ScrollView contentContainerStyle={styles.body}>
        {sources.map((info) => {
          const broken = info.status === 'expired' || info.status === 'error';
          const off = info.status === 'disconnected';
          return (
            <Pressable
              key={info.source}
              onPress={() => (off || broken ? onConnect(info) : onOpen(info))}
              style={styles.row}
            >
              <View
                style={[
                  styles.dot,
                  info.status === 'connected' && styles.dotOk,
                  broken && styles.dotBad,
                ]}
              />
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
                <>
                  <Text style={styles.count}>{info.count}</Text>
                  {/* Into the source's own dashboard. The count says what
                      needs you; the page behind it says what has been going
                      on, which the feed deliberately does not. */}
                  <Text style={styles.chevron}>{'\u203A'}</Text>
                </>
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
  body: { paddingTop: s(4), paddingBottom: s(30) },
  /** Green when live, ochre when broken, hollow when never connected. */
  dot: {
    width: s(6),
    height: s(6),
    borderRadius: s(3),
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: 'transparent',
  },
  dotOk: { backgroundColor: '#3F8F5F', borderColor: '#3F8F5F' },
  dotBad: { backgroundColor: colors.urgent, borderColor: colors.urgent },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(10),
    marginHorizontal: s(13),
    marginTop: s(7),
    paddingHorizontal: s(12),
    paddingVertical: s(11),
    backgroundColor: colors.surface,
    borderRadius: s(12),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  rowBody: { flex: 1 },
  rowTitle: { ...type.rowTitle, fontWeight: '600', color: colors.fg },
  rowTitleOff: { color: colors.dim },
  rowSub: { ...type.rowSub, marginTop: s(1) },
  rowSubBad: { color: colors.urgent },
  count: { ...type.groupCount, color: colors.fg },
  chevron: { fontSize: s(15), color: colors.dim, marginLeft: s(2) },
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
