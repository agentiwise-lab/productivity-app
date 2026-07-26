/**
 * You: notifications, appearance, connections.
 *
 * The AI section is gone. Summarising and ranking is what the product *is*, so
 * asking permission per source framed the core behaviour as an optional extra
 * and invited the user to turn the product off inside the product.
 *
 * There is no "Fix" button either. A connection is either live, or it needs
 * connecting, and a third word for the middle case was three words for two
 * states.
 */

import React, { useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, View } from 'react-native';
import Animated, {
  useAnimatedScrollHandler,
  useSharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { radius, space, topInset, useAppearance, useTheme, type Appearance } from '../theme';
import { CollapsedTitle, ScreenHeader } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Icon } from '../components/Icon';
import { Row } from '../components/ListRow';
import { Chip, Segmented, Separator, T, Toggle } from '../components/ui';
import type { Source, SourceInfo } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

/**
 * Four levels on the wire, three controls on the screen: the toggle expresses
 * `off`, so the segmented control never has to offer it.
 *
 * `urgent_today` keeps its wire value. Renaming a persisted enum because its
 * label changed is a migration that buys nothing.
 */
export type NotifyLevel = 'urgent' | 'urgent_today' | 'all' | 'off';

const LEVELS: { value: Exclude<NotifyLevel, 'off'>; label: string }[] = [
  { value: 'urgent', label: 'Urgent' },
  { value: 'urgent_today', label: '+ By EOD' },
  { value: 'all', label: 'All' },
];

const APPEARANCES: { value: Appearance; label: string }[] = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'system', label: 'System' },
];

interface Props {
  email: string;
  name?: string | null;
  notifyLevel: NotifyLevel;
  connections: SourceInfo[];
  /** The source currently pulling its first data after a connect, if any. */
  syncingSource?: Source | null;
  syncingSecs?: number;
  onSetNotifyLevel: (level: NotifyLevel) => void;
  onConnect: (provider: Source) => void;
  onDisconnect: (provider: Source) => void;
  onEditName: () => void;
  onSignOut: () => void;
}

export function YouScreen({
  email,
  name,
  notifyLevel,
  connections,
  syncingSource = null,
  syncingSecs = 0,
  onSetNotifyLevel,
  onConnect,
  onDisconnect,
  onEditName,
  onSignOut,
}: Props) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const { appearance, setAppearance } = useAppearance();
  const [lastLevel, setLastLevel] = useState<Exclude<NotifyLevel, 'off'>>(
    notifyLevel === 'off' ? 'urgent' : notifyLevel,
  );
  const scrollY = useSharedValue(0);
  const onScroll = useAnimatedScrollHandler((event) => {
    scrollY.value = event.contentOffset.y;
  });

  const on = notifyLevel !== 'off';
  // What the segmented control shows. When notifications are off the control
  // is not rendered at all, so it falls back to whatever was last chosen
  // rather than to a level the user never picked.
  const level: Exclude<NotifyLevel, 'off'> = on ? notifyLevel : lastLevel;
  // Dev builds authenticate with a bare user id, and a UUID rendered at 34pt
  // as though it were a person's name is the screen showing its plumbing.
  const local = email.includes('@') ? email.split('@')[0] : '';
  const title = name || local || 'You';
  const needsAction = connections.filter(
    (info) => info.status === 'expired' || info.status === 'error',
  ).length;

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas }}>
      <AnimatedScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentContainerStyle={{ paddingTop: topInset(insets.top), paddingBottom: space.xl }}
      >
        {/* The name is the title; editing it is an inline chip on the same row,
            so the screen no longer repeats "Name" over the obvious. */}
        <ScreenHeader
          title={title}
          right={
            <Chip
              label={name ? 'Edit' : 'Add your name'}
              variant="outline"
              onPress={onEditName}
            />
          }
        />

        <Separator inset={0} />

        {/* No "Notifications" label over a row that opens "Notify me": the
            heading and the control were saying the same word twice. */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: space.sm,
            paddingHorizontal: space.md,
            minHeight: 72,
            marginTop: space.sm,
          }}
        >
          <View style={{ flex: 1 }}>
            <T role="heading">Notify me</T>
            <T role="secondary" tone="mid">
              {on
                ? `${LEVELS.find((entry) => entry.value === level)?.label ?? ''} only`
                : 'Off'}
            </T>
          </View>
          <Toggle
            value={on}
            onChange={(next) => onSetNotifyLevel(next ? lastLevel : 'off')}
          />
        </View>

        {/* The level appears only when notifications are on. A disabled row of
            three options is three controls explaining they do nothing. */}
        {on ? (
          <View style={{ paddingHorizontal: space.md, paddingBottom: space.md }}>
            <Segmented
              options={LEVELS}
              value={level}
              onChange={(next) => {
                setLastLevel(next);
                onSetNotifyLevel(next);
              }}
            />
          </View>
        ) : null}

        <Separator inset={0} />

        {/* The section headings read like "Notify me", not as small uppercase
            labels: every heading on the screen is one 17pt weight, so the eye
            groups them as peers. They sit close under the separator rather than
            a full 32pt below it. */}
        <SectionHeading label="Appearance" />
        {/* The heading sits close under the line (its own small top padding),
            and the breathing room goes here instead, between the heading and
            the selector, without making the section any taller overall. */}
        <View style={{ paddingHorizontal: space.md, paddingTop: space.xs, paddingBottom: space.md }}>
          <Segmented options={APPEARANCES} value={appearance} onChange={setAppearance} />
        </View>

        <Separator inset={0} />

        <SectionHeading
          label="Connections"
          right={
            needsAction > 0 ? (
              // The bubble counts only what needs action, so an optional source
              // that was never connected never badges.
              <View
                style={{
                  minWidth: 20,
                  height: 20,
                  paddingHorizontal: space.xs,
                  borderRadius: radius.pill,
                  backgroundColor: c.hue.urgent,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <T role="label" colour={c.onSolid} numeric>
                  {String(needsAction)}
                </T>
              </View>
            ) : null
          }
        />

        {connections.map((info) => (
          <Row
            key={info.source}
            category={null}
            leading={<BrandMark source={info.source} size={32} />}
            title={info.label}
            subtitle={statusLine(info)}
            trailing={
              syncingSource === info.source ? (
                // Reassurance that the just-connected source is pulling its
                // data, with a short countdown, instead of a blocking loader.
                <View
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: space.xs,
                    paddingHorizontal: space.sm,
                    height: 28,
                    borderRadius: radius.pill,
                    backgroundColor: c.overlay,
                  }}
                >
                  <ActivityIndicator size="small" color={c.hue.later} />
                  <T role="label" tone="mid">
                    {syncingSecs > 0 ? `Syncing… ${syncingSecs}s` : 'Syncing…'}
                  </T>
                </View>
              ) : info.status === 'connected' ? (
                <Pressable
                  onPress={() =>
                    Alert.alert(
                      `Disconnect ${info.label}?`,
                      'This app will lose access until you connect it again.',
                      [
                        { text: 'Cancel', style: 'cancel' },
                        {
                          text: 'Disconnect',
                          style: 'destructive',
                          onPress: () => onDisconnect(info.source),
                        },
                      ],
                    )
                  }
                  hitSlop={8}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: space.xs }}
                >
                  <View
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 999,
                      backgroundColor: c.mid,
                    }}
                  />
                  <T role="label" tone="low">
                    Live
                  </T>
                </Pressable>
              ) : (
                <Chip
                  label="Connect"
                  variant="outline"
                  onPress={() => onConnect(info.source)}
                />
              )
            }
          />
        ))}

        <Pressable
          onPress={onSignOut}
          style={({ pressed }) => [
            {
              flexDirection: 'row',
              alignItems: 'center',
              paddingHorizontal: space.md,
              minHeight: 56,
              marginTop: space.lg,
            },
            pressed ? { opacity: 0.7 } : null,
          ]}
        >
          <T role="body" tone="mid" style={{ flex: 1 }}>
            Sign out
          </T>
          <Icon name="chevron" size={16} color={c.low} />
        </Pressable>
        <Separator inset={0} />
      </AnimatedScrollView>
      <CollapsedTitle title={title} scrollY={scrollY} />
    </View>
  );
}

/** A section heading in the same 17pt weight as "Notify me", with room on the
 *  right for a badge, set close under the separator above it. */
function SectionHeading({
  label,
  right,
}: {
  label: string;
  right?: React.ReactNode;
}) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.xs,
        paddingHorizontal: space.md,
        // Close under the separator above it, not a full step below.
        paddingTop: space.xs,
        paddingBottom: space.xs,
      }}
    >
      <T role="heading" style={{ flex: 1 }}>
        {label}
      </T>
      {right}
    </View>
  );
}

/**
 * Whether the connection is working, and nothing else.
 *
 * A connected source used to report "0 in the last 30 days" here, which is a
 * volume figure standing in a list about plumbing: it reads as a fault when it
 * is a quiet month, and Activity is where volume belongs anyway. A live
 * connection therefore says nothing at all, and the `Live` marker beside it is
 * the whole message.
 */
function statusLine(info: SourceInfo): string | undefined {
  switch (info.status) {
    case 'connected':
      return undefined;
    case 'expired':
      return 'Sign-in expired. Connect again.';
    case 'error':
      return 'Could not read this connection.';
    default:
      return 'Not connected';
  }
}
