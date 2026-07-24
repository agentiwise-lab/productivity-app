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
import { Pressable, ScrollView, View } from 'react-native';
import Animated, {
  useAnimatedScrollHandler,
  useSharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { radius, space, useAppearance, useTheme, type Appearance } from '../theme';
import { CollapsedTitle, ScreenHeader } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Icon } from '../components/Icon';
import { Row } from '../components/ListRow';
import { Chip, SectionLabel, Segmented, Separator, T, Toggle } from '../components/ui';
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
  name?: string;
  notifyLevel: NotifyLevel;
  connections: SourceInfo[];
  onSetNotifyLevel: (level: NotifyLevel) => void;
  onConnect: (provider: Source) => void;
  onSignOut: () => void;
}

export function YouScreen({
  email,
  name,
  notifyLevel,
  connections,
  onSetNotifyLevel,
  onConnect,
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
        contentContainerStyle={{ paddingTop: insets.top, paddingBottom: space.xl }}
      >
        <ScreenHeader eyebrow={local ? email : "Signed in"} title={title} />

        <SectionLabel label="Notifications" />
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: space.sm,
            paddingHorizontal: space.md,
            minHeight: 72,
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

        <SectionLabel label="Appearance" />
        <View style={{ paddingHorizontal: space.md, paddingBottom: space.md }}>
          <Segmented options={APPEARANCES} value={appearance} onChange={setAppearance} />
        </View>

        <Separator inset={0} />

        <SectionLabel
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
            category="none"
            leading={<BrandMark source={info.source} size={32} />}
            title={info.label}
            subtitle={statusLine(info)}
            trailing={
              info.status === 'connected' ? (
                <View
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
                </View>
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
          <Icon name="chevron" size={16} color={c.low} weight={1.8} />
        </Pressable>
        <Separator inset={0} />
      </AnimatedScrollView>
      <CollapsedTitle title={title} scrollY={scrollY} />
    </View>
  );
}

function statusLine(info: SourceInfo): string {
  switch (info.status) {
    case 'connected':
      return info.urgent > 0
        ? `${info.urgent} need you of ${info.count}`
        : `${info.count} in the last 30 days`;
    case 'expired':
      return 'Sign-in expired. Connect again.';
    case 'error':
      return 'Could not read this connection.';
    default:
      return 'Never connected';
  }
}
