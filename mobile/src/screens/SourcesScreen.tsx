/**
 * Sources: one row per connected tool, with what it is currently asking of you.
 *
 * A broken connection gets a red dot and a reconnect prompt rather than being
 * left to look like a quiet source. Plan 6.4 is explicit that a source going
 * silent because we lost access must never be indistinguishable from a source
 * with nothing to say.
 */

import React, { useMemo } from 'react';
import { View, Text, Pressable, SectionList, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, space, radius, type } from '../theme';
import { BrandMark } from '../components/BrandMark';
import { FeedCard } from '../components/FeedCard';
import type { FeedRow, Source } from '../api/types';

export interface Connection {
  provider: Source;
  label: string;
  status: 'active' | 'expired' | 'revoked' | 'error';
}

interface Props {
  rows: FeedRow[];
  connections: Connection[];
  onOpen: (row: FeedRow) => void;
  onAction: (row: FeedRow, action: string) => void;
  onReconnect: (provider: Source) => void;
}

export function SourcesScreen({
  rows,
  connections,
  onOpen,
  onAction,
  onReconnect,
}: Props) {
  const sections = useMemo(
    () =>
      connections.map((connection) => {
        const mine = rows.filter(
          (row) => row.source === connection.provider && row.tier !== 'noise',
        );
        return { connection, title: connection.label, data: mine };
      }),
    [rows, connections],
  );

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Text style={styles.title}>Sources</Text>
      <SectionList
        sections={sections}
        keyExtractor={(row) => row.id}
        contentContainerStyle={styles.body}
        stickySectionHeadersEnabled={false}
        renderSectionHeader={({ section }) => (
          <SourceHeader
            connection={section.connection}
            count={section.data.length}
            onReconnect={onReconnect}
          />
        )}
        renderSectionFooter={({ section }) =>
          section.data.length === 0 && section.connection.status === 'active' ? (
            <Text style={styles.quiet}>Nothing needs you here.</Text>
          ) : null
        }
        renderItem={({ item }) => (
          <View style={styles.row}>
            <FeedCard row={item} onPress={onOpen} onAction={onAction} />
          </View>
        )}
        ListEmptyComponent={
          <Text style={styles.quiet}>No tools connected yet.</Text>
        }
      />
    </SafeAreaView>
  );
}

function SourceHeader({
  connection,
  count,
  onReconnect,
}: {
  connection: Connection;
  count: number;
  onReconnect: (provider: Source) => void;
}) {
  const broken = connection.status !== 'active';
  return (
    <Pressable
      disabled={!broken}
      onPress={() => onReconnect(connection.provider)}
      style={styles.header}
    >
      <BrandMark source={connection.provider} size={24} />
      <Text style={styles.headerLabel}>{connection.label}</Text>
      {broken ? <View style={styles.dot} /> : null}
      <View style={styles.spacer} />
      <Text style={broken ? styles.headerBad : styles.headerCount}>
        {broken ? 'Reconnect' : count}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  title: {
    ...type.h1,
    color: colors.fg,
    paddingHorizontal: space.lg,
    paddingTop: space.sm,
    paddingBottom: space.sm,
  },
  body: { paddingBottom: space.xxl },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingTop: space.xl,
    paddingBottom: space.sm,
  },
  headerLabel: { ...type.h2, color: colors.fg },
  headerCount: { ...type.body, color: colors.dim },
  headerBad: { ...type.small, fontWeight: '600', color: colors.urgent },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.urgent },
  spacer: { flex: 1 },
  row: { paddingHorizontal: space.lg, paddingBottom: space.md },
  quiet: {
    ...type.small,
    color: colors.dim,
    paddingHorizontal: space.lg,
    paddingBottom: space.md,
  },
});
