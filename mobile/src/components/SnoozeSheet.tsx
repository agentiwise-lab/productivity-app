/**
 * Snooze, on any source.
 *
 * The one action that works everywhere, and the only one the client used to
 * decide on the user's behalf: it hardcoded three hours. The endpoint has
 * always taken an arbitrary time, so the picker is entirely client-side.
 *
 * The copy speaks to the user, not about them: it tells them what snoozing does
 * for them rather than describing the feature in the third person.
 */

import React from 'react';
import { Modal, Pressable, StyleSheet, View } from 'react-native';
import { inset, radius, space, useTheme } from '../theme';
import { Separator, T } from './ui';

export interface SnoozeOption {
  label: string;
  when: string;
  at: Date;
}

/** This evening, tomorrow morning, next week. Three, and they cover it. */
export function snoozeOptions(now = new Date()): SnoozeOption[] {
  const evening = new Date(now);
  evening.setHours(18, 0, 0, 0);
  if (evening <= now) evening.setDate(evening.getDate() + 1);

  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(9, 0, 0, 0);

  const nextWeek = new Date(now);
  // The next Monday, which is what "next week" means to anyone with a job.
  nextWeek.setDate(nextWeek.getDate() + ((8 - nextWeek.getDay()) % 7 || 7));
  nextWeek.setHours(9, 0, 0, 0);

  return [
    { label: 'This evening', when: clock(evening), at: evening },
    { label: 'Tomorrow morning', when: `${day(tomorrow)} ${clock(tomorrow)}`, at: tomorrow },
    { label: 'Next week', when: `${day(nextWeek)} ${clock(nextWeek)}`, at: nextWeek },
  ];
}

export function SnoozeSheet({
  visible,
  onPick,
  onClose,
}: {
  visible: boolean;
  onPick: (at: Date) => void;
  onClose: () => void;
}) {
  const c = useTheme();
  if (!visible) return null;
  const options = snoozeOptions();

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={StyleSheet.absoluteFill} onPress={onClose}>
        <View style={[StyleSheet.absoluteFill, { backgroundColor: c.scrim }]} />
      </Pressable>
      <View style={{ flex: 1, justifyContent: 'flex-end' }} pointerEvents="box-none">
        <View
          style={{
            backgroundColor: c.raised,
            borderTopLeftRadius: radius.lg,
            borderTopRightRadius: radius.lg,
            paddingHorizontal: space.md,
            paddingBottom: inset.bottom,
          }}
        >
          <View
            style={{
              width: 36,
              height: 5,
              borderRadius: radius.pill,
              backgroundColor: c.border,
              alignSelf: 'center',
              marginTop: space.xs,
              marginBottom: space.md,
            }}
          />
          <T role="title">Remind me</T>
          <T role="secondary" tone="mid" style={{ marginTop: space.xs }}>
            This just hides it from you until then. Nobody else is told, and
            nothing is sent.
          </T>
          <View style={{ height: space.md }} />
          <Separator inset={0} />
          {options.map((option) => (
            <View key={option.label}>
              <Pressable
                onPress={() => onPick(option.at)}
                style={({ pressed }) => [
                  { flexDirection: 'row', alignItems: 'center', minHeight: 56 },
                  pressed ? { opacity: 0.7 } : null,
                ]}
              >
                <T role="body" style={{ flex: 1 }}>
                  {option.label}
                </T>
                <T role="secondary" tone="low" numeric>
                  {option.when}
                </T>
              </Pressable>
              <Separator inset={0} />
            </View>
          ))}
        </View>
      </View>
    </Modal>
  );
}

const clock = (date: Date) =>
  `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

const day = (date: Date) =>
  date.toLocaleDateString(undefined, { weekday: 'short' }).replace(/,/g, '');
