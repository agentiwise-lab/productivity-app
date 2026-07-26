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

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, AppState, Linking, Platform, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
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
import { streamEvents, type StreamHandle } from './src/api/stream';
import { SyncPill } from './src/components/SyncPill';
import { AuthProvider, useAuth } from './src/auth/AuthContext';
import { AuthGate } from './src/screens/auth/AuthGate';
import type {
  FeedRow,
  MeetingOut,
  Source,
  SourceDashboard,
  SourceInfo,
} from './src/api/types';
import { NamePrompt } from './src/components/NamePrompt';
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
          <AuthProvider api={api}>
            <Gate />
          </AuthProvider>
        </SafeAreaProvider>
      </AppearanceProvider>
    </GestureHandlerRootView>
  );
}

/**
 * The one decision above the whole app: are we in, out, or still finding out.
 * Signed in gets the five tabs; signed out gets the auth flow; loading gets a
 * bare canvas rather than a spinner, because restoring a token from the keychain
 * is a few milliseconds and a flash of spinner reads as slower than nothing.
 */
function Gate() {
  const { status } = useAuth();
  const c = useTheme();
  if (status === 'loading') return <View style={{ flex: 1, backgroundColor: c.canvas }} />;
  if (status === 'signedOut') return <AuthGate />;
  return <Shell />;
}

function Shell() {
  const c = useTheme();
  const { email: authEmail, signOut, justSignedUp, acknowledgeSignup } = useAuth();
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
  // Sources whose connect-backfill is in flight. A global pill above the footer
  // and a per-row cue both read this set. Promise-driven: a source clears when its
  // refresh resolves, no countdown, no held-gating (the reviews rejected those).
  const [syncingSources, setSyncingSources] = useState<Set<Source>>(new Set());

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
  const [name, setName] = useState<string | null>(null);
  const [nameModalOpen, setNameModalOpen] = useState(false);

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

  const loadProfile = useCallback(async () => {
    try {
      const profile = await api.me();
      setName(profile.name);
    } catch {
      // Non-fatal: the greeting stays generic until /me answers.
    }
  }, []);

  const saveName = useCallback(async (value: string) => {
    setNameModalOpen(false);
    try {
      const profile = await api.setName(value.trim());
      setName(profile.name);
    } catch {
      Alert.alert('Could not save', 'Your name did not save. Try again.');
    }
  }, []);

  // A cheap read of the stored feed (Redis, one hop). Returns the rows so the
  // cold-start path can tell an empty feed from a full one.
  const load = useCallback(async (): Promise<FeedRow[]> => {
    try {
      const result = await api.getFeed();
      setRows(result.rows);
      setStale(result.stale);
      setFetchedAt(result.fetchedAt);
      return result.rows;
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'auth') {
        Alert.alert('Signed out', error.message);
      }
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * The heavy path: poll every provider and re-classify, then re-read the feed.
   * Reserved for connect and manual pull (the north star) — never a timer.
   * Single-flight: concurrent connects and a pull-during-connect coalesce into
   * one sweep rather than N overlapping full-provider polls.
   */
  const refreshing = useRef(false);
  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    try {
      await Promise.all([load(), loadSources(), loadDay(), loadProfile()]);
      try {
        await api.refresh();
      } catch {
        // A failed pull is not a failed screen: the rows above still stand.
        return;
      }
      await Promise.all([load(), loadSources()]);
    } finally {
      refreshing.current = false;
    }
  }, [load, loadSources, loadDay, loadProfile]);

  // Cold start is a cheap read, not a heavy sweep (north star). The feed is
  // served from Redis; only if it is genuinely empty (a >24h-cold cache, or a
  // brand-new account) do we fall back to one refresh, so a returning user sees
  // their feed instantly instead of watching every provider get polled.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void (async () => {
      const [rows] = await Promise.all([
        load(),
        loadSources(),
        loadDay(),
        loadProfile(),
      ]);
      if (rows.length === 0) void refresh();
    })();
  }, [load, loadSources, loadDay, loadProfile, refresh]);

  // The name prompt is a signup step, not a per-launch nag: open it once when a
  // fresh signup lands, and never on login or a restored session.
  useEffect(() => {
    if (justSignedUp) {
      setNameModalOpen(true);
      acknowledgeSignup();
    }
  }, [justSignedUp, acknowledgeSignup]);

  // Returning to the app re-reads connections. Web OAuth has no deep-link back:
  // Composio lands the user on its own "taking you back" tab, and the connect
  // poll can miss the moment the account goes active. When the user switches
  // back to the app we re-fetch, and because the backend reconciles on this read
  // a just-finished connect shows as connected without a manual pull-to-refresh.
  useEffect(() => {
    // Foreground is a cheap read: the stored feed (Redis) plus connections and
    // the day. This is what surfaces a webhook item that landed while the app was
    // backgrounded, without polling providers.
    const reread = () => {
      void loadSources();
      void load();
      void loadDay();
    };
    if (Platform.OS === 'web') {
      const onVisible = () => {
        if (typeof document === 'undefined' || document.visibilityState === 'visible') {
          reread();
        }
      };
      window.addEventListener('visibilitychange', onVisible);
      window.addEventListener('focus', reread);
      return () => {
        window.removeEventListener('visibilitychange', onVisible);
        window.removeEventListener('focus', reread);
      };
    }
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') reread();
    });
    return () => sub.remove();
  }, [loadSources, load, loadDay]);

  // Live feed stream: while the app is open, a webhook item landing on the
  // backend publishes a "changed" signal over this SSE connection, and we do one
  // cheap GET /feed to append it — event-driven, no polling, no provider sweep.
  // Self-reconnecting: a dropped connection reopens, and a cheap load on reconnect
  // catches anything missed while briefly disconnected.
  useEffect(() => {
    let handle: StreamHandle | null = null;
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const open = () => {
      if (cancelled) return;
      const { url, headers } = api.feedStream();
      handle = streamEvents({
        url,
        headers,
        onBatch: () => {},
        onEvent: (name) => {
          if (name === 'changed') void load();
        },
        onDone: () => {
          if (!cancelled) retry = setTimeout(open, 3000);
        },
        onError: () => {
          if (!cancelled) retry = setTimeout(open, 5000);
        },
        onUnauthorized: () => api.reauth(),
      });
    };
    open();
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
      handle?.cancel();
    };
  }, [load]);

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

  const connectSource = useCallback(
    async (provider: Source) => {
      const label = SOURCE_LABELS[provider];
      try {
        const { url } = await api.connectUrl(provider);
        if (!url) throw new Error('no url');

        // The in-app browser returns to us when the OAuth flow reaches our
        // scheme, or when the user closes it. Either way we then ask the backend
        // whether the account went active, because Composio does the token
        // exchange server-side and the redirect alone does not prove success.
        // Matches the "scheme" in app.json. When the OAuth flow lands here the
        // in-app browser closes and returns control to us.
        const returnUrl = 'productivityapp://composio-callback';
        await WebBrowser.openAuthSessionAsync(url, returnUrl);

        for (let attempt = 0; attempt < 15; attempt++) {
          try {
            const info = await api.connectionStatus(provider);
            if (info.status === 'connected') {
              await loadSources();
              haptics.commit();
              // Pull the just-connected source's existing items into the feed
              // now, rather than leaving it empty until a manual pull-to-refresh.
              // The pill shows until the backfill resolves — the completion signal
              // is the promise, not a countdown.
              setSyncingSources((s) => new Set(s).add(provider));
              void refresh().finally(() =>
                setSyncingSources((s) => {
                  const next = new Set(s);
                  next.delete(provider);
                  return next;
                }),
              );
              return;
            }
          } catch {
            // keep polling; a transient read is not a failed connection
          }
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
        await loadSources();
        Alert.alert(
          `Connect ${label}`,
          "We couldn't confirm the connection yet. It may just need a moment; pull to refresh.",
        );
      } catch {
        Alert.alert(`Connect ${label}`, 'Could not start the connection. Please try again.');
      }
    },
    [loadSources, refresh],
  );

  const disconnectSource = useCallback(
    async (provider: Source) => {
      try {
        await api.disconnect(provider);
      } catch {
        // Even a failed call clears our side; the next status read reconciles.
      }
      await loadSources();
    },
    [loadSources],
  );

  const onSignOut = useCallback(() => {
    void signOut();
  }, [signOut]);

  return (
    <>
      <StatusBar style={c.mode === 'dark' ? 'light' : 'dark'} />
      <NavigationContainer theme={navTheme}>
        <Tab.Navigator
          tabBar={(props) => <TabBar {...props} />}
          screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: c.canvas } }}
        >
          <Tab.Screen name="Day" options={{ title: 'Day' }}>
            {({ navigation }) => (
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
                // The empty-state button reads "Open You": it sends the user to
                // the You tab to pick a source, not straight into a GitHub OAuth.
                onConnect={() => navigation.navigate('You')}
                name={name}
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
                onRefresh={refresh}
              />
            )}
          </Tab.Screen>
          <Tab.Screen name="Later" options={{ title: 'Later' }}>
            {() => (
              <LaterScreen api={api} sources={sources} onOpenRow={openRow} />
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
                email={authEmail || DEV_USER_ID}
                name={name}
                notifyLevel={notifyLevel}
                connections={sources}
                syncingSources={syncingSources}
                onSetNotifyLevel={setNotifyLevel}
                onConnect={connectSource}
                onDisconnect={disconnectSource}
                onEditName={() => setNameModalOpen(true)}
                onSignOut={onSignOut}
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
        <NamePrompt
          visible={nameModalOpen}
          initialValue={name ?? ''}
          onSave={saveName}
          onCancel={() => setNameModalOpen(false)}
          subtitle="This is how the app greets you. You can change it anytime in You."
        />
        <Grain />
        {/* Global sync indicator: one pill above the footer while any connected
            source is backfilling, on whatever tab the user is looking at. */}
        <SyncPill sources={syncingSources} />
      </NavigationContainer>
    </>
  );
}
