/**
 * App root: owns the feed, hands it to five screens.
 *
 * One fetch feeds every tab. Your day, Feed, Activity and Later are four
 * readings of the same ranked array rather than four queries, which is what
 * makes it impossible for them to disagree about what is urgent.
 *
 * Acting is optimistic: the row leaves the list the moment you reply, because
 * an item you have dealt with sitting there for a network round trip is the
 * app failing at its one job. If the call fails the row comes back and says so.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Linking, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useFonts } from 'expo-font';
import {
  Geist_400Regular,
  Geist_500Medium,
  Geist_600SemiBold,
} from '@expo-google-fonts/geist';
import { GeistMono_400Regular } from '@expo-google-fonts/geist-mono';

import { AppearanceProvider, haptics, useTheme } from './src/theme';
import { API_URL, AUTH_MODE, DEV_USER_ID } from './src/config';
import { ApiClient, ApiError } from './src/api/client';
import type {
  FeedRow,
  MeetingOut,
  Source,
  SourceDashboard,
  SourceInfo,
} from './src/api/types';
import { YourDayScreen } from './src/screens/YourDayScreen';
import { FeedScreen } from './src/screens/FeedScreen';
import { ActivityScreen } from './src/screens/ActivityScreen';
import { SourceDetailScreen } from './src/screens/SourceDetailScreen';
import { LaterScreen } from './src/screens/LaterScreen';
import { YouScreen, type NotifyLevel } from './src/screens/YouScreen';
import { DetailSheet } from './src/components/DetailSheet';
import { SnoozeSheet } from './src/components/SnoozeSheet';
import { TabBar } from './src/components/TabBar';
import { Grain } from './src/components/Grain';
import type { Meeting } from './src/components/YourDayCard';

const Tab = createBottomTabNavigator();

const api = new ApiClient(API_URL, (): Record<string, string> =>
  AUTH_MODE === 'dev' ? { 'X-User-Id': DEV_USER_ID } : {},
);

const SOURCE_LABELS: Record<Source, string> = {
  github: 'GitHub',
  slack: 'Slack',
  calendar: 'Google Calendar',
  google_docs: 'Google Docs',
  linear: 'Linear',
  gmail: 'Gmail',
};

/**
 * Every source the product supports, in the order they are shown.
 *
 * This is the list, not whatever the API happened to return. Sources used to
 * start empty and fill in from `/connections`, so when that call failed the
 * screen was blank and Your day claimed there was nothing connected: a network
 * error was indistinguishable from a user who had never set anything up.
 */
const ALL_SOURCES: Source[] = [
  'github',
  'slack',
  'calendar',
  'linear',
  'gmail',
  'google_docs',
];

const SOURCE_SKELETON: SourceInfo[] = ALL_SOURCES.map((source) => ({
  source,
  label: SOURCE_LABELS[source],
  status: 'disconnected',
  count: 0,
  urgent: 0,
  connected_account_id: null,
}));

function mergeSources(live: SourceInfo[]): SourceInfo[] {
  const byId = new Map(live.map((info) => [info.source, info]));
  return SOURCE_SKELETON.map((row) => byId.get(row.source) ?? row);
}

export default function App() {
  // Each weight is its own family. Asking for a weight a family did not ship
  // fails silently on iOS: it renders the regular cut and says nothing.
  const [fontsReady] = useFonts({
    Geist_400Regular,
    Geist_500Medium,
    Geist_600SemiBold,
    GeistMono_400Regular,
    // The mockup draws every display and label string at `font-stretch: 88%`,
    // a width axis React Native cannot address on a variable font. Archivo's
    // SemiCondensed named instance is 87.5%, so the static cut is vendored
    // rather than approximated: at regular width the same strings ran 10 to 13
    // per cent wider, which is most of what read as heavy on screen.
    Archivo_SemiCondensed_600SemiBold: require('./assets/fonts/Archivo-SemiCondensed-SemiBold.ttf'),
  });

  if (!fontsReady) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AppearanceProvider>
        <SafeAreaProvider>
          <Shell />
        </SafeAreaProvider>
      </AppearanceProvider>
    </GestureHandlerRootView>
  );
}

function Shell() {
  const c = useTheme();
  const [rows, setRows] = useState<FeedRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const [selected, setSelected] = useState<FeedRow | null>(null);
  // Whether the sheet should open straight into its composer. True only when the
  // sheet was opened by tapping Reply or Comment, so opening it to read does not
  // shove a keyboard up at you.
  const [composeOnOpen, setComposeOnOpen] = useState(false);
  const [snoozing, setSnoozing] = useState<FeedRow | null>(null);
  const [busy, setBusy] = useState(false);
  const [notifyLevel, setNotifyLevel] = useState<NotifyLevel>('urgent');

  const [sources, setSources] = useState<SourceInfo[]>(SOURCE_SKELETON);
  const [sourcesFailed, setSourcesFailed] = useState(false);
  const [loadingSources, setLoadingSources] = useState(true);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  // The calendar loads on its own track, separate from the feed. Day used the
  // feed's loading flag, so the moment the feed arrived it decided the calendar
  // was empty and flashed "no meetings" before the calendar had answered.
  const [dayLoading, setDayLoading] = useState(true);
  const [dashboard, setDashboard] = useState<SourceDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  useEffect(() => {
    haptics.prepare();
  }, []);

  const navTheme = useMemo(
    () => ({
      ...DefaultTheme,
      dark: c.mode === 'dark',
      colors: { ...DefaultTheme.colors, background: c.canvas, card: c.surface },
    }),
    [c],
  );

  const connectedCount = useMemo(
    () => sources.filter((info) => info.status === 'connected').length,
    [sources],
  );

  const loadSources = useCallback(async () => {
    try {
      setSources(mergeSources(await api.connections()));
      setSourcesFailed(false);
    } catch {
      // The list still renders in full; every row says the status could not be
      // read. "Not connected yet" would be a claim we cannot make.
      setSources(SOURCE_SKELETON.map((row) => ({ ...row, status: 'error' as const })));
      setSourcesFailed(true);
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
      // An unreadable calendar leaves the ring empty rather than inventing a
      // schedule, which would make the free-time figure a lie.
    } finally {
      setDayLoading(false);
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

  // Open the sheet to read (compose=false) or straight into the composer.
  const openRow = useCallback((row: FeedRow, compose = false) => {
    setComposeOnOpen(compose);
    setSelected(row);
  }, []);

  const act = useCallback(
    async (row: FeedRow, action: string, body?: string) => {
      if (action === 'open') {
        void Linking.openURL(row.url);
        return;
      }
      // Snooze is the one action that asks a question first, because "later"
      // is the user's word and the client had been picking three hours for
      // them without asking.
      if (action === 'snooze') {
        setSelected(null);
        setSnoozing(row);
        return;
      }

      const previous = rows;
      setRows((current) => current.filter((item) => item.id !== row.id));
      setSelected(null);
      setBusy(true);
      try {
        if (action === 'mark_read' || action === 'dismiss') {
          await api.dismiss(row.id);
        } else if (action === 'bring_back') {
          // Promoting a snoozed item back to the live queue is a snooze that
          // has already expired, which is exactly what the endpoint models.
          await api.snooze(row.id, new Date());
          await load();
        } else {
          await api.act(row.id, action, body ?? '');
        }
      } catch (error) {
        setRows(previous);
        haptics.refused();
        Alert.alert(
          'That did not go through',
          error instanceof ApiError ? error.message : 'Try again.',
        );
      } finally {
        setBusy(false);
      }
    },
    [rows, load],
  );

  const applySnooze = useCallback(
    async (at: Date) => {
      const row = snoozing;
      setSnoozing(null);
      if (!row) return;
      const previous = rows;
      setRows((current) => current.filter((item) => item.id !== row.id));
      try {
        await api.snooze(row.id, at);
      } catch (error) {
        setRows(previous);
        haptics.refused();
        Alert.alert(
          'That did not go through',
          error instanceof ApiError ? error.message : 'Try again.',
        );
      }
    },
    [snoozing, rows],
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
      Alert.alert('Could not load', `${info.label} did not answer. Try again.`);
    } finally {
      setDashboardLoading(false);
    }
  }, []);

  const connectSource = useCallback(async (provider: Source) => {
    const label = SOURCE_LABELS[provider];
    try {
      const { url } = await api.connectUrl(provider);
      if (url) {
        void Linking.openURL(url);
        return;
      }
    } catch {
      // fall through to the explanation below
    }
    Alert.alert(
      `Connect ${label}`,
      'Managed sign-in is not wired up in this build. The accounts in this demo were connected in Composio directly.',
    );
  }, []);

  const notImplemented = useCallback(() => {
    Alert.alert('Not yet', 'Signing out lands with managed accounts.');
  }, []);

  return (
    <>
      <StatusBar style={c.mode === 'dark' ? 'light' : 'dark'} />
      <NavigationContainer theme={navTheme}>
        <Tab.Navigator
          tabBar={(props) => <TabBar {...props} />}
          screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: c.canvas } }}
        >
          <Tab.Screen name="Day" options={{ title: 'Day' }}>
            {() => (
              <YourDayScreen
                rows={rows}
                loading={loading}
                dayLoading={dayLoading}
                stale={stale}
                fetchedAt={fetchedAt}
                meetings={meetings}
                connectedCount={connectedCount}
                sourcesUnknown={sourcesFailed}
                sourcesLoading={loadingSources}
                onRefresh={refresh}
                onOpen={openRow}
                onConnect={() => connectSource('github')}
              />
            )}
          </Tab.Screen>
          {/* The route stays "Feed" so its glyph and navigation keep resolving;
              only the label the user reads changes. These are things to act on,
              not a feed to scroll. */}
          <Tab.Screen name="Feed" options={{ title: 'To-dos' }}>
            {() => (
              <FeedScreen
                rows={rows}
                loading={loading}
                onAction={act}
                onOpen={openRow}
              />
            )}
          </Tab.Screen>
          <Tab.Screen name="Later" options={{ title: 'Later' }}>
            {() => (
              <LaterScreen api={api} onOpen={(url) => void Linking.openURL(url)} />
            )}
          </Tab.Screen>
          <Tab.Screen name="Activity" options={{ title: 'Activity' }}>
            {() => (
              <ActivityScreen
                sources={sources}
                api={api}
                loadingStatus={loadingSources}
                onOpen={openSource}
              />
            )}
          </Tab.Screen>
          <Tab.Screen name="You" options={{ title: 'You' }}>
            {() => (
              <YouScreen
                email={DEV_USER_ID}
                notifyLevel={notifyLevel}
                connections={sources}
                onSetNotifyLevel={setNotifyLevel}
                onConnect={connectSource}
                onSignOut={notImplemented}
              />
            )}
          </Tab.Screen>
        </Tab.Navigator>

        {dashboard ? (
          // Covers the tab bar too: a board is a place you go, not a panel
          // that shares the screen with the thing you left.
          <View
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: c.canvas,
              zIndex: 20,
            }}
          >
            <SourceDetailScreen
              dashboard={dashboard}
              loading={dashboardLoading}
              onBack={() => setDashboard(null)}
              onRefresh={() => {
                const info = sources.find((s) => s.source === dashboard.source);
                if (info) void openSource(info);
              }}
            />
          </View>
        ) : null}

        <DetailSheet
          row={selected}
          busy={busy}
          startComposing={composeOnOpen}
          onClose={() => setSelected(null)}
          onAction={act}
        />
        <SnoozeSheet
          visible={snoozing !== null}
          onPick={applySnooze}
          onClose={() => setSnoozing(null)}
        />
        <Grain />
      </NavigationContainer>
    </>
  );
}
