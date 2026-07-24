/**
 * Later: what arrived from a source and did not need you.
 *
 * Read live and stored nowhere. It used to be 360 saved rows, which meant
 * keeping a month of newsletters in the database to render a list that is
 * different tomorrow anyway. Now it asks the provider what is currently unread,
 * unanswered or open, so it cannot drift from what you see in Gmail itself.
 *
 * The rows stream in. Pulling every unread message takes most of a minute, and
 * a list that appears only at the end reads as broken, so batches are appended
 * as they land and the count climbs while you look at it.
 *
 * One source at a time, chosen from the strip. "Everything" is deliberately not
 * an option: it would be four slow fetches to build a list nobody reads to the
 * end of.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, s, type } from '../theme';
import { Header } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { streamEvents, type StreamHandle } from '../api/stream';
import { ago } from '../lib/time';
import type { ApiClient } from '../api/client';
import type { LaterRow, Source } from '../api/types';

/** Only the sources that have a "did not need you" pile worth reading. */
const SOURCES: { id: Source; label: string }[] = [
  { id: 'gmail', label: 'Gmail' },
  { id: 'slack', label: 'Slack' },
  { id: 'linear', label: 'Linear' },
  { id: 'github', label: 'GitHub' },
];

const LOADING_NOTE: Partial<Record<Source, string>> = {
  gmail: 'Reading everything unread in the last 30 days.',
  slack: 'Reading messages you were not addressed in.',
  linear: 'Reading issues nobody is waiting on.',
  github: 'Reading notifications you have not opened.',
};

export function LaterScreen({ api }: { api: ApiClient }) {
  const [source, setSource] = useState<Source>('gmail');
  const [rows, setRows] = useState<LaterRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const handle = useRef<StreamHandle | null>(null);

  const load = useCallback(
    (next: Source) => {
      // Leaving one source mid-stream must not let its rows land in the next.
      handle.current?.cancel();
      setRows([]);
      setError(null);
      setLoading(true);

      const { url, headers } = api.laterStream(next);
      handle.current = streamEvents<LaterRow>({
        url,
        headers,
        onBatch: (batch) => setRows((current) => [...current, ...batch]),
        onDone: () => setLoading(false),
        onError: (message) => {
          setError(message);
          setLoading(false);
        },
      });
    },
    [api],
  );

  useEffect(() => {
    load(source);
    return () => handle.current?.cancel();
  }, [source, load]);

  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Header title="Later" subtitle="Last 30 days" />

      {/* Icons rather than words, along the full width and scrollable, so the
          strip stays one line however many sources there are. */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.strip}
      >
        {SOURCES.map((entry) => {
          const active = entry.id === source;
          return (
            <Pressable
              key={entry.id}
              onPress={() => setSource(entry.id)}
              style={[styles.pill, active && styles.pillOn]}
            >
              <BrandMark source={entry.id} size={s(16)} radius={s(5)} />
              {active ? <Text style={styles.pillText}>{entry.label}</Text> : null}
            </Pressable>
          );
        })}
      </ScrollView>

      <ScrollView contentContainerStyle={styles.body}>
        {rows.map((row) => (
          <Pressable
            key={row.source_ref}
            onPress={() => row.url && void Linking.openURL(row.url)}
            style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
          >
            <BrandMark source={row.source} size={s(24)} radius={s(7)} />
            <View style={styles.rowBody}>
              <Text style={styles.rowTitle} numberOfLines={1}>
                {row.sender_name ? `${row.sender_name}: ` : ''}
                {row.title}
              </Text>
              {row.summary ? (
                <Text style={styles.rowSub} numberOfLines={1}>
                  {row.summary}
                </Text>
              ) : null}
            </View>
            <Text style={styles.rowMeta}>{ago(row.occurred_at)}</Text>
          </Pressable>
        ))}

        {loading ? (
          <View style={styles.loading}>
            <ActivityIndicator color={colors.accent} />
            <Text style={styles.loadingNote}>
              {rows.length > 0
                ? `${rows.length} so far`
                : LOADING_NOTE[source] ?? 'Reading from the source.'}
            </Text>
          </View>
        ) : null}

        {!loading && error ? <Text style={styles.error}>{error}</Text> : null}

        {!loading && !error && rows.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Nothing waiting here</Text>
            <Text style={styles.emptyBody}>
              Everything from this source either needed you, and is on Home, or
              you have already dealt with it.
            </Text>
          </View>
        ) : null}

        {!loading && rows.length > 0 ? (
          <Text style={styles.footnote}>
            {rows.length} from {SOURCES.find((e) => e.id === source)?.label}.
            Read live, never stored.
          </Text>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  strip: {
    flexDirection: 'row',
    gap: s(6),
    paddingHorizontal: s(13),
    paddingTop: s(9),
    paddingBottom: s(3),
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(6),
    paddingHorizontal: s(9),
    paddingVertical: s(6),
    borderRadius: s(9),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    backgroundColor: colors.surface,
  },
  pillOn: { backgroundColor: colors.accentSoft, borderColor: colors.accent },
  pillText: { ...type.chipLabel, color: colors.fg },

  body: { paddingTop: s(6), paddingBottom: s(30) },
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
  rowBody: { flex: 1, gap: s(2) },
  rowTitle: { ...type.rowTitle, fontWeight: '600', color: colors.fg },
  rowSub: { ...type.rowSub },
  rowMeta: { ...type.ago },

  loading: { alignItems: 'center', gap: s(7), paddingTop: s(18) },
  loadingNote: { ...type.rowSub, textAlign: 'center', paddingHorizontal: s(30) },
  error: { ...type.rowSub, color: colors.urgent, textAlign: 'center', paddingTop: s(20) },

  empty: { paddingHorizontal: s(20), paddingTop: s(30), gap: s(6) },
  emptyTitle: { ...type.rowTitle, fontWeight: '700', color: colors.fg, fontSize: s(13) },
  emptyBody: { ...type.rowSub },

  footnote: { ...type.rowSub, textAlign: 'center', paddingTop: s(14) },
});
