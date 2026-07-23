/**
 * App root: owns the feed, hands it to four screens.
 *
 * One fetch feeds every tab. Home, Sources and Later are three readings of the
 * same ranked array rather than three queries, which is what makes it
 * impossible for them to disagree about what is urgent.
 *
 * Acting is optimistic: the row leaves the list the moment you reply, because
 * an item you have dealt with sitting there for a network round trip is the
 * app failing at its one job. If the call fails the row comes back and says so.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Linking, StatusBar, StyleSheet } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { colors, type } from './src/theme';
import { API_URL, AUTH_MODE, DEV_USER_ID } from './src/config';
import { ApiClient, ApiError } from './src/api/client';
import type { FeedRow, Source } from './src/api/types';
import { HomeScreen } from './src/screens/HomeScreen';
import { SourcesScreen, type Connection } from './src/screens/SourcesScreen';
import { LaterScreen } from './src/screens/LaterScreen';
import { YouScreen, type NotifyLevel } from './src/screens/YouScreen';
import { DetailSheet } from './src/components/DetailSheet';
import { TabIcon } from './src/components/TabIcon';
import type { Meeting } from './src/components/YourDay';

const Tab = createBottomTabNavigator();

const navTheme = {
  ...DefaultTheme,
  colors: { ...DefaultTheme.colors, background: colors.bg, card: colors.surface },
};

const api = new ApiClient(API_URL, (): Record<string, string> =>
  AUTH_MODE === 'dev' ? { 'X-User-Id': DEV_USER_ID } : {},
);

const SOURCE_LABELS: Partial<Record<Source, string>> = {
  github: 'GitHub',
  slack: 'Slack',
  calendar: 'Google Calendar',
  google_docs: 'Google Docs',
  linear: 'Linear',
  gmail: 'Gmail',
};

export default function App() {
  const [rows, setRows] = useState<FeedRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const [selected, setSelected] = useState<FeedRow | null>(null);
  const [busy, setBusy] = useState(false);
  const [notifyLevel, setNotifyLevel] = useState<NotifyLevel>('urgent');
  const [aiOptOut, setAiOptOut] = useState<Partial<Record<Source, boolean>>>({});

  // Calendar is phase 5. Until then Your day shows an honestly empty schedule
  // rather than invented meetings, so the free-time figure stays truthful.
  const meetings: Meeting[] = useMemo(() => [], []);

  const connections: Connection[] = useMemo(() => {
    const seen = new Set(rows.map((row) => row.source));
    return Array.from(seen).map((provider) => ({
      provider,
      label: SOURCE_LABELS[provider] ?? provider,
      status: 'active' as const,
    }));
  }, [rows]);

  const load = useCallback(async () => {
    try {
      const result = await api.getFeed();
      setRows(result.rows);
      setStale(result.stale);
      setFetchedAt(result.fetchedAt);
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'auth') {
        Alert.alert('Signed out', error.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      await api.refresh();
    } catch {
      // A failed pull is not a failed screen. Fall through to load(), which
      // serves the cache when the network is the thing that broke.
    }
    await load();
  }, [load]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const act = useCallback(
    async (row: FeedRow, action: string, body?: string) => {
      if (action === 'open') {
        void Linking.openURL(row.url);
        return;
      }

      const previous = rows;
      setRows((current) => current.filter((item) => item.id !== row.id));
      setSelected(null);
      setBusy(true);
      try {
        if (action === 'snooze') {
          await api.snooze(row.id, new Date(Date.now() + 3 * 3600 * 1000));
        } else if (action === 'mark_read' || action === 'dismiss') {
          await api.dismiss(row.id);
        } else {
          await api.act(row.id, body ?? '');
        }
      } catch (error) {
        setRows(previous);
        Alert.alert(
          "That didn't go through",
          error instanceof ApiError ? error.message : 'Try again.',
        );
      } finally {
        setBusy(false);
      }
    },
    [rows],
  );

  const notImplemented = useCallback(() => {
    Alert.alert('Not yet', 'Connecting new tools lands with the next phase.');
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" backgroundColor={colors.bg} />
      <NavigationContainer theme={navTheme}>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            headerShown: false,
            tabBarActiveTintColor: colors.accent,
            tabBarInactiveTintColor: colors.dim,
            tabBarStyle: styles.tabBar,
            tabBarLabelStyle: styles.tabLabel,
            tabBarIcon: ({ color }) => (
              <TabIcon name={route.name.toLowerCase() as never} color={color} />
            ),
          })}
        >
          <Tab.Screen name="Home">
            {() => (
              <HomeScreen
                rows={rows}
                loading={loading}
                stale={stale}
                fetchedAt={fetchedAt}
                meetings={meetings}
                connected={connections.length > 0 || rows.length > 0}
                onRefresh={refresh}
                onOpen={setSelected}
                onAction={act}
                onConnect={notImplemented}
              />
            )}
          </Tab.Screen>
          <Tab.Screen name="Sources">
            {() => (
              <SourcesScreen
                rows={rows}
                connections={connections}
                onOpen={setSelected}
                onAction={act}
                onReconnect={notImplemented}
              />
            )}
          </Tab.Screen>
          <Tab.Screen name="Later">
            {() => <LaterScreen rows={rows} onOpen={setSelected} onAction={act} />}
          </Tab.Screen>
          <Tab.Screen name="You">
            {() => (
              <YouScreen
                email={DEV_USER_ID}
                notifyLevel={notifyLevel}
                connections={connections}
                aiOptOut={aiOptOut}
                onSetNotifyLevel={setNotifyLevel}
                onToggleAi={(provider, optOut) =>
                  setAiOptOut((current) => ({ ...current, [provider]: optOut }))
                }
                onReconnect={notImplemented}
                onSignOut={notImplemented}
              />
            )}
          </Tab.Screen>
        </Tab.Navigator>

        <DetailSheet
          row={selected}
          busy={busy}
          onClose={() => setSelected(null)}
          onAction={act}
        />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.surface,
    borderTopColor: colors.line,
    // Tall enough for icon plus label plus the home indicator. At 62 the
    // labels were clipped by the bar's own bottom edge.
    height: 76,
    paddingTop: 8,
    paddingBottom: 14,
  },
  tabLabel: { ...type.small, fontSize: 10, fontWeight: '600', marginTop: 2 },
});
