/**
 * The time ruler. Combination B plus D from the explorations, which is what was
 * approved: a real proportional strip of the working day, not three numbers in
 * boxes.
 *
 * The three figures are defined in plan 6.1 and are not interchangeable:
 *   meetings left = calendar events remaining today
 *   free          = unscheduled minutes between now and end of working hours
 *   due today     = the user's own items with a deadline of today
 *
 * Free time is derived from the meetings, never stored, so it cannot disagree
 * with the ruler drawn directly above it.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, space, radius, type } from '../theme';

export interface Meeting {
  title: string;
  start: Date;
  end: Date;
}

interface Props {
  meetings: Meeting[];
  dueToday: number;
  workStartHour?: number;
  workEndHour?: number;
  now?: Date;
  compact?: boolean;
}

function minutesInto(date: Date, startHour: number): number {
  return (date.getHours() - startHour) * 60 + date.getMinutes();
}

export function YourDay({
  meetings,
  dueToday,
  workStartHour = 9,
  workEndHour = 18,
  now = new Date(),
  compact = false,
}: Props) {
  const span = (workEndHour - workStartHour) * 60;
  const nowMin = Math.min(Math.max(minutesInto(now, workStartHour), 0), span);

  const remaining = meetings.filter((m) => m.end > now);
  const bookedAhead = remaining.reduce(
    (total, m) => total + (m.end.getTime() - Math.max(m.start.getTime(), now.getTime())) / 60000,
    0,
  );
  const freeMinutes = Math.max(0, span - nowMin - bookedAhead);
  const freeLabel =
    freeMinutes >= 60
      ? `${Math.floor(freeMinutes / 60)}h ${Math.round(freeMinutes % 60)}m`
      : `${Math.round(freeMinutes)}m`;

  if (compact) {
    return (
      <View style={styles.compact}>
        <Text style={styles.compactText}>
          {remaining.length} left · {freeLabel} free · {dueToday} due
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.ruler}>
        {meetings.map((meeting, index) => {
          const left = Math.max(0, minutesInto(meeting.start, workStartHour));
          const width = Math.max(
            6,
            (meeting.end.getTime() - meeting.start.getTime()) / 60000,
          );
          const past = meeting.end <= now;
          return (
            <View
              key={index}
              style={[
                styles.block,
                past && styles.blockPast,
                { left: `${(left / span) * 100}%`, width: `${(width / span) * 100}%` },
              ]}
            />
          );
        })}
        <View style={[styles.nowLine, { left: `${(nowMin / span) * 100}%` }]} />
      </View>

      <View style={styles.scale}>
        <Text style={styles.scaleText}>{workStartHour}:00</Text>
        <View style={styles.spacer} />
        <Text style={styles.scaleText}>{workEndHour}:00</Text>
      </View>

      <View style={styles.stats}>
        <Stat value={String(remaining.length)} label="meetings left" />
        <View style={styles.divider} />
        <Stat value={freeLabel} label="free" />
        <View style={styles.divider} />
        <Stat value={String(dueToday)} label="due today" />
      </View>
    </View>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: space.sm, paddingHorizontal: space.lg, paddingTop: space.sm },
  ruler: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.line,
    overflow: 'hidden',
  },
  block: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    backgroundColor: colors.accent,
    borderRadius: radius.pill,
  },
  blockPast: { backgroundColor: '#BEC5CC' },
  nowLine: {
    position: 'absolute',
    top: -3,
    bottom: -3,
    width: 2,
    backgroundColor: colors.urgent,
    borderRadius: 1,
  },
  scale: { flexDirection: 'row' },
  scaleText: { ...type.small, fontSize: 10, color: colors.dim },
  spacer: { flex: 1 },
  stats: { flexDirection: 'row', alignItems: 'center', paddingTop: space.xs },
  stat: { flex: 1 },
  statValue: { ...type.h2, color: colors.fg },
  statLabel: { ...type.small, fontSize: 11, color: colors.dim },
  divider: {
    width: 1,
    height: 22,
    backgroundColor: colors.line,
    // Without this the rule sits flush against the next figure and reads as a
    // stray mark on the digit rather than a separator.
    marginRight: space.md,
  },
  compact: {
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    backgroundColor: colors.bg,
  },
  compactText: { ...type.small, color: colors.dim },
});
