/**
 * You: notification level, connected accounts, and the AI disclosure.
 *
 * The disclosure is not buried in a policy link. Classifying a Slack message
 * means sending its text to a third party, which is the core privacy fact of
 * this product, so it is stated on the settings screen next to the switch that
 * turns it off per source.
 */

import React from 'react';
import { View, Text, Pressable, ScrollView, Switch, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, space, radius, type } from '../theme';
import { BrandMark } from '../components/BrandMark';
import type { Source } from '../api/types';
import type { Connection } from './SourcesScreen';

export type NotifyLevel = 'urgent' | 'urgent_today' | 'off';

const LEVELS: { id: NotifyLevel; label: string; detail: string }[] = [
  { id: 'urgent', label: 'Urgent only', detail: 'Someone is waiting on you now.' },
  { id: 'urgent_today', label: 'Urgent and today', detail: 'Anything due before tonight.' },
  { id: 'off', label: 'Nothing', detail: 'Check the app when you want to.' },
];

interface Props {
  email: string;
  notifyLevel: NotifyLevel;
  connections: Connection[];
  aiOptOut: Partial<Record<Source, boolean>>;
  onSetNotifyLevel: (level: NotifyLevel) => void;
  onToggleAi: (provider: Source, optOut: boolean) => void;
  onReconnect: (provider: Source) => void;
  onSignOut: () => void;
}

export function YouScreen({
  email,
  notifyLevel,
  connections,
  aiOptOut,
  onSetNotifyLevel,
  onToggleAi,
  onReconnect,
  onSignOut,
}: Props) {
  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <Text style={styles.title}>You</Text>
      <ScrollView contentContainerStyle={styles.body}>
        <Text style={styles.email}>{email}</Text>

        <Section title="Notifications">
          {LEVELS.map((level) => {
            const active = level.id === notifyLevel;
            return (
              <Pressable
                key={level.id}
                onPress={() => onSetNotifyLevel(level.id)}
                style={[styles.option, active && styles.optionActive]}
              >
                <View style={styles.optionText}>
                  <Text style={[styles.optionLabel, active && styles.optionLabelActive]}>
                    {level.label}
                  </Text>
                  <Text style={[styles.optionDetail, active && styles.optionDetailActive]}>
                    {level.detail}
                  </Text>
                </View>
                {active ? <View style={styles.tick} /> : null}
              </Pressable>
            );
          })}
        </Section>

        <Section title="Connected">
          {connections.map((connection) => (
            <Pressable
              key={connection.provider}
              onPress={() => onReconnect(connection.provider)}
              style={styles.connection}
            >
              <BrandMark source={connection.provider} size={24} />
              <Text style={styles.connectionLabel}>{connection.label}</Text>
              <View style={styles.spacer} />
              <Text
                style={
                  connection.status === 'active' ? styles.ok : styles.bad
                }
              >
                {connection.status === 'active' ? 'Connected' : 'Reconnect'}
              </Text>
            </Pressable>
          ))}
        </Section>

        <Section title="AI summaries">
          <Text style={styles.disclosure}>
            To decide what is urgent, message text is sent to OpenRouter, a
            third-party model provider. Turn this off for a source and that
            source falls back to rules only, which still works but is blunter.
          </Text>
          {connections.map((connection) => (
            <View key={connection.provider} style={styles.connection}>
              <BrandMark source={connection.provider} size={24} />
              <Text style={styles.connectionLabel}>{connection.label}</Text>
              <View style={styles.spacer} />
              <Switch
                value={!aiOptOut[connection.provider]}
                onValueChange={(on) => onToggleAi(connection.provider, !on)}
                trackColor={{ true: colors.accent, false: colors.line }}
                // Left to the platform, the thumb comes out green and is the
                // only colour on screen that belongs to no part of the palette.
                thumbColor={colors.surface}
                ios_backgroundColor={colors.line}
              />
            </View>
          ))}
        </Section>

        <Pressable onPress={onSignOut} style={styles.signOut}>
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.card}>{children}</View>
    </View>
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
  body: { padding: space.lg, paddingBottom: space.xxl, gap: space.xl },
  email: { ...type.body, color: colors.dim },
  section: { gap: space.sm },
  sectionTitle: { ...type.small, fontWeight: '600', color: colors.dim, letterSpacing: 0.4 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.line,
    overflow: 'hidden',
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: space.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  optionActive: { backgroundColor: colors.accentSoft },
  optionText: { flex: 1, gap: 2 },
  optionLabel: { ...type.body, fontWeight: '600', color: colors.fg },
  optionLabelActive: { color: colors.accent },
  optionDetail: { ...type.small, color: colors.dim },
  optionDetailActive: { color: colors.accent },
  tick: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.accent },
  connection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    padding: space.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  connectionLabel: { ...type.body, color: colors.fg },
  spacer: { flex: 1 },
  ok: { ...type.small, color: colors.dim },
  bad: { ...type.small, fontWeight: '600', color: colors.urgent },
  disclosure: {
    ...type.small,
    color: colors.dim,
    padding: space.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  signOut: {
    alignItems: 'center',
    paddingVertical: space.lg,
  },
  signOutText: { ...type.body, fontWeight: '600', color: colors.urgent },
});
