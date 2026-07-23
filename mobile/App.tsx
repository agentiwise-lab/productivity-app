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
import { Alert, Linking, StatusBar, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { colors, s, type } from './src/theme';
import { API_URL, AUTH_MODE, DEV_USER_ID } from './src/config';
import { ApiClient, ApiError } from './src/api/client';
import type {
  FeedRow,
  MeetingOut,
  Source,
  SourceDashboard,
  SourceInfo,
} from './src/api/types';
import { HomeScreen } from './src/screens/HomeScreen';
import { SourcesScreen } from './src/screens/SourcesScreen';
import { SourceDetailScreen } from './src/screens/SourceDetailScreen';
import { LaterScreen } from './src/screens/LaterScreen';
import { YouScreen, type NotifyLevel } from './src/screens/YouScreen';
import { DetailSheet } from './src/components/DetailSheet';
import { TabIcon } from './src/components/Chrome';
import type { Meeting } from './src/components/YourDayCard';

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

  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [dashboard, setDashboard] = useState<SourceDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const connectedCount = useMemo(
    () => sources.filter((info) => info.status === 'connected').length,
    [sources],
  );

  const loadSources = useCallback(async () => {
    try {
      setSources(await api.connections());
    } catch {
      // Sources still renders its full skeleton; only the statuses are missing.
    } finally {
      setLoadingSources(false);
    }
  }, []);

  const loadDay = useCallback(async () => {
    try {
      const day: MeetingOut[] = await api.day();
      setMeetings(
        day.map((m) => ({
          title: m.title,
          start: new Date(m.start),
          end: new Date(m.end),
        })),
      );
    } catch {
      // An unreadable calendar leaves the ruler empty rather than inventing a
      // schedule, which would make the free-time figure a lie.
    }
  }, []);

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

  /**
   * Paint first, then fetch. Pulling five providers takes seconds, and making
   * the user watch a skeleton for all of them before seeing anything is the
   * difference between an app that feels instant and one that feels broken.
   * The cached feed and the connection list render immediately; the pull
   * happens behind them and the rows update when it lands.
   */
  const refresh = useCallback(async () => {
    await Promise.all([load(), loadSources(), loadDay()]);
    try {
      await api.refresh();
    } catch {
      // A failed pull is not a failed screen: the rows above still stand.
      return;
    }
    await Promise.all([load(), loadSources()]);
  }, [load, loadSources, loadDay]);

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

  const openSource = useCallback(async (info: SourceInfo) => {
    setDashboardLoading(true);
    setDashboard({
      source: info.source,
      label: info.label,
      headline: [],
      breakdown: [],
      breakdown_title: '',
      unavailable: [],
    });
    try {
      setDashboard(await api.sourceDashboard(info.source));
    } catch {
      setDashboard(null);
      Alert.alert("Couldn't load", `${info.label} did not answer. Try again.`);
    } finally {
      setDashboardLoading(false);
    }
  }, []);

  const connectSource = useCallback(async (info: SourceInfo) => {
    try {
      const { url } = await api.connectUrl(info.source);
      if (url) {
        void Linking.openURL(url);
        return;
      }
    } catch {
      // fall through to the explanation below
    }
    Alert.alert(
      `Connect ${info.label}`,
      'Managed sign-in is not wired up in this build. The accounts in this demo were connected in Composio directly.',
    );
  }, []);

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
            tabBarIcon: ({ color, focused }) => (
              <TabIcon name={route.name} color={color} focused={focused} />
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
                connectedCount={connectedCount}
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
                sources={sources}
                loadingStatus={loadingSources}
                onOpen={openSource}
                onConnect={connectSource}
              />
            )}
          </Tab.Screen>
          <Tab.Screen name="Later">
            {() => <LaterScreen rows={rows} onOpen={setSelected} />}
          </Tab.Screen>
          <Tab.Screen name="You">
            {() => (
              <YouScreen
                email={DEV_USER_ID}
                notifyLevel={notifyLevel}
                connections={sources}
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

        {dashboard ? (
          <View style={styles.fullScreen}>
            <SourceDetailScreen
              dashboard={dashboard}
              loading={dashboardLoading}
              onBack={() => setDashboard(null)}
            />
          </View>
        ) : null}

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
    borderTopWidth: StyleSheet.hairlineWidth,
    // Icon, label and the home indicator all need room. Too short and the
    // labels are clipped away entirely, leaving four unexplained glyphs.
    height: s(50),
    paddingTop: s(5),
    paddingBottom: s(8),
  },
  tabLabel: { ...type.tabLabel, marginTop: s(2) },
  // Covers the tab bar too: a source dashboard is a place you go, not a
  // panel that shares the screen with the thing you left.
  fullScreen: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: colors.bg, zIndex: 20 },
});
