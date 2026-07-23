/**
 * "Your day", as a card with a proportional ruler. Matches the mockup's
 * .card / .ruler / .rfoot exactly.
 *
 * The ruler is the point: it shows the day at true proportion, so a wall of
 * meetings looks like a wall and a clear afternoon looks clear. Three numbers
 * in boxes could not do that, which is why the approved design is a strip.
 *
 * Free time is derived from the meetings drawn directly above it, never stored,
 * so the number and the picture cannot contradict each other.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, s, type } from '../theme';

export interface Meeting {
  title: string;
  start: Date;
  end: Date;
}

interface Props {
  meetings: Meeting[];
  now?: Date;
  workStartHour?: number;
  workEndHour?: number;
}

const pct = (value: number) =>
  `${Math.max(0, Math.min(100, value * 100))}%` as `${number}%`;

export function YourDayCard({
  meetings,
  now = new Date(),
  workStartHour = 9,
  workEndHour = 18,
}: Props) {
  const spanMinutes = (workEndHour - workStartHour) * 60;
  const into = (date: Date) =>
    (date.getHours() - workStartHour) * 60 + date.getMinutes();
  const nowFrac = Math.min(Math.max(into(now) / spanMinutes, 0), 1);

  const upcoming = meetings.filter((m) => m.end > now);
  const next = upcoming[0];

  const bookedAhead = upcoming.reduce(
    (total, m) =>
      total + (m.end.getTime() - Math.max(m.start.getTime(), now.getTime())) / 60000,
    0,
  );
  const freeMinutes = Math.max(0, spanMinutes - into(now) - bookedAhead);
  const freeLabel =
    freeMinutes >= 60
      ? `${Math.floor(freeMinutes / 60)}h ${Math.round(freeMinutes % 60)}m free`
      : `${Math.round(freeMinutes)}m free`;

  const clock = (date: Date) =>
    `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

  return (
    <View style={styles.card}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>Your day</Text>
        <Text style={styles.meta} numberOfLines={1}>
          {String(workStartHour).padStart(2, '0')}:00 to {workEndHour}:00
        </Text>
      </View>

      <View style={styles.ruler}>
        <View style={styles.trackClip}>
          <View style={styles.track} />
        {meetings.map((meeting, index) => {
          // Clamped to the working window. A meeting at 23:00 was drawn far
          // past the right edge and spilled out of the card, which is what
          // made the strip look broken rather than full.
          const rawLeft = into(meeting.start) / spanMinutes;
          const rawEnd = into(meeting.end) / spanMinutes;
          const left = Math.max(0, Math.min(rawLeft, 1));
          const width = Math.max(0.012, Math.min(rawEnd, 1) - left);
          if (rawEnd <= 0 || rawLeft >= 1) return null;
          const past = meeting.end <= now;
          return (
            <View
              key={index}
              style={[
                styles.block,
                past && styles.blockPast,
                { left: pct(left), width: pct(width) },
              ]}
            />
          );
        })}
          <View style={[styles.nowLine, { left: pct(nowFrac) }]} />
        </View>
        <Text style={[styles.tick, { left: 0 }]}>{workStartHour}</Text>
        {nowFrac > 0.08 && nowFrac < 0.9 ? (
          <Text style={[styles.tick, { left: pct(nowFrac - 0.04) }]}>now</Text>
        ) : null}
        <Text style={[styles.tick, { right: 0 }]}>{workEndHour}</Text>
      </View>

      <View style={styles.foot}>
        <Text style={[styles.meta, styles.footNext]} numberOfLines={1}>
          {next ? `next ${clock(next.start)} ${next.title}` : 'nothing left today'}
        </Text>
        <Text style={[styles.meta, styles.footFree]} numberOfLines={1}>
          {freeLabel}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: s(13),
    marginTop: s(9),
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(14),
    paddingHorizontal: s(12),
    paddingVertical: s(11),
    overflow: 'hidden',
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: s(6),
  },
  title: { ...type.cardTitle, color: colors.fg },
  meta: { ...type.cardMeta },
  ruler: { height: s(34), marginTop: s(2), marginBottom: s(8) },
  trackClip: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: s(24),
    overflow: 'hidden',
  },
  track: {
    position: 'absolute',
    top: s(12),
    left: 0,
    right: 0,
    height: s(6),
    borderRadius: s(3),
    backgroundColor: colors.accentSoft,
  },
  block: {
    position: 'absolute',
    top: s(8),
    height: s(14),
    borderRadius: s(4),
    backgroundColor: colors.accent,
  },
  blockPast: { backgroundColor: colors.dim, opacity: 0.38 },
  nowLine: {
    position: 'absolute',
    top: s(3),
    width: 2,
    height: s(24),
    backgroundColor: colors.urgent,
    borderRadius: 1,
  },
  tick: {
    position: 'absolute',
    top: s(24),
    fontFamily: 'Menlo',
    fontSize: s(8),
    color: colors.dim,
  },
  foot: { flexDirection: 'row', alignItems: 'baseline', gap: s(8) },
  footNext: { flex: 1 },
  footFree: { flexShrink: 0 },
});
