/**
 * "Your day": the whole day at true proportion, midnight to midnight.
 *
 * Full 24 hours rather than 9 to 18, because this app is not only for office
 * work and an 11pm meeting is still a meeting. A meeting that runs past
 * midnight is clipped at the edge rather than dropped, which is what used to
 * make a real 23:00 to 00:00 booking simply vanish from the strip.
 *
 * Three block colours carry three different facts: what is done, what is next,
 * and what is later. Free time is derived from the same meetings drawn above
 * it, so the picture and the number cannot disagree.
 */

import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, s, type } from '../theme';

export interface Meeting {
  title: string;
  start: Date;
  end: Date;
}

interface Props {
  meetings: Meeting[];
  now?: Date;
}

const DAY_MINUTES = 24 * 60;
const HOUR_MARKS = [0, 6, 12, 18, 24];

const pct = (value: number) =>
  `${Math.max(0, Math.min(100, value * 100))}%` as `${number}%`;

const clock = (date: Date) =>
  `${String(date.getHours()).padStart(2, '0')}:${String(
    date.getMinutes(),
  ).padStart(2, '0')}`;

export function YourDayCard({ meetings, now = new Date() }: Props) {
  const [shown, setShown] = useState<Meeting | null>(null);

  const into = (date: Date) => date.getHours() * 60 + date.getMinutes();
  const nowFrac = into(now) / DAY_MINUTES;

  const sorted = [...meetings].sort((a, b) => a.start.getTime() - b.start.getTime());
  const upcoming = sorted.filter((m) => m.end > now);
  const next = upcoming[0];

  const bookedAhead = upcoming.reduce(
    (total, m) =>
      total + (m.end.getTime() - Math.max(m.start.getTime(), now.getTime())) / 60000,
    0,
  );
  const leftInDay = Math.max(0, DAY_MINUTES - into(now));
  const freeMinutes = Math.max(0, leftInDay - bookedAhead);
  const freeLabel =
    freeMinutes >= 60
      ? `${Math.floor(freeMinutes / 60)}h ${Math.round(freeMinutes % 60)}m free`
      : `${Math.round(freeMinutes)}m free`;

  const caption = shown
    ? `${clock(shown.start)} to ${clock(shown.end)}  ${shown.title}`
    : next
      ? `${clock(next.start)}  ${next.title}`
      : 'Nothing left on the calendar today';

  return (
    <View style={styles.card}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>Your day</Text>
        <Text style={styles.meta} numberOfLines={1}>
          {upcoming.length} {upcoming.length === 1 ? 'meeting' : 'meetings'} left ·{' '}
          {freeLabel}
        </Text>
      </View>

      <View style={styles.ruler}>
        <View style={styles.track} />

        {HOUR_MARKS.slice(1, -1).map((hour) => (
          <View
            key={`grid-${hour}`}
            style={[styles.grid, { left: pct(hour / 24) }]}
          />
        ))}

        {sorted.map((meeting, index) => {
          const startFrac = into(meeting.start) / DAY_MINUTES;
          // A meeting ending after midnight reports an end-of-day earlier than
          // its start. Clamp it to the edge instead of computing a negative
          // width and drawing nothing at all.
          const crossesMidnight = meeting.end <= meeting.start;
          const endFrac = crossesMidnight ? 1 : into(meeting.end) / DAY_MINUTES;
          const width = Math.max(0.008, endFrac - startFrac);

          const past = meeting.end <= now;
          const isNext = next != null && meeting === next;

          return (
            <Pressable
              key={index}
              onPress={() => setShown(shown === meeting ? null : meeting)}
              style={[
                styles.block,
                past ? styles.blockPast : isNext ? styles.blockNext : styles.blockLater,
                { left: pct(startFrac), width: pct(width) },
              ]}
            />
          );
        })}

        <View style={[styles.nowLine, { left: pct(nowFrac) }]} />

        {HOUR_MARKS.map((hour) => (
          <Text
            key={`tick-${hour}`}
            style={[
              styles.tick,
              hour === 24
                ? { right: 0 }
                : hour === 0
                  ? { left: 0 }
                  : { left: pct(hour / 24), marginLeft: -s(4) },
            ]}
          >
            {String(hour).padStart(2, '0')}
          </Text>
        ))}
      </View>

      <View style={styles.foot}>
        <View
          style={[
            styles.dot,
            shown
              ? shown.end <= now
                ? styles.blockPast
                : styles.blockNext
              : styles.blockNext,
          ]}
        />
        <Text style={styles.caption} numberOfLines={2}>
          {caption}
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
    gap: s(2),
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: s(8),
  },
  title: { ...type.cardTitle, color: colors.fg },
  meta: { ...type.cardMeta, flexShrink: 1 },
  ruler: { height: s(32), marginTop: s(6), marginBottom: s(4) },
  track: {
    position: 'absolute',
    top: s(6),
    left: 0,
    right: 0,
    height: s(11),
    borderRadius: s(4),
    backgroundColor: colors.bg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  grid: {
    position: 'absolute',
    top: s(6),
    width: StyleSheet.hairlineWidth,
    height: s(11),
    backgroundColor: colors.line,
  },
  block: {
    position: 'absolute',
    top: s(7),
    height: s(9),
    borderRadius: s(3),
    minWidth: s(3),
  },
  /** Done. Present but spent. */
  blockPast: { backgroundColor: '#C3BFB7' },
  /** The one you are walking into. */
  blockNext: { backgroundColor: '#3F8F5F' },
  /** Later today. */
  blockLater: { backgroundColor: colors.accent },
  nowLine: {
    position: 'absolute',
    top: s(3),
    width: 2,
    height: s(17),
    backgroundColor: colors.urgent,
    borderRadius: 1,
  },
  tick: {
    position: 'absolute',
    top: s(20),
    fontFamily: 'Menlo',
    fontSize: s(7.5),
    color: colors.dim,
  },
  foot: { flexDirection: 'row', alignItems: 'flex-start', gap: s(6) },
  dot: { width: s(6), height: s(6), borderRadius: s(3), marginTop: s(3) },
  caption: { flex: 1, fontSize: s(10.5), lineHeight: s(10.5) * 1.35, color: colors.fg },
});
