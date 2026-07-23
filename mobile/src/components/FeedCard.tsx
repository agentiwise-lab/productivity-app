/**
 * The swipeable feed card, matching the mockup's .fcard.
 *
 * Every element in plan 6.1 is here and none is conditional on space: source
 * roundel, type tag, urgency styling, time, sender, title, the AI one-liner,
 * and two actions. The card is 216 of a 272pt phone, about four fifths, so the
 * next one always peeks and the swipe is obvious without being explained.
 */

import React, { useRef } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Animated,
  PanResponder,
} from 'react-native';
import { colors, s, type, roundel } from '../theme';
import { ago, deadlineLabel } from '../lib/time';
import { BrandMark } from './BrandMark';
import { actionsFor } from '../lib/actions';
import type { FeedRow } from '../api/types';

export const CARD_WIDTH = s(216);
export const CARD_GAP = s(9);

const TAG_LABEL: Record<string, string> = {
  review: 'Review',
  approve: 'Approve',
  reply: 'Reply',
  assigned: 'Assigned',
  comment: 'Comment',
  decide: 'Decide',
  rsvp: 'RSVP',
  alert: 'Alert',
  fyi: 'FYI',
};

/** Past this, a horizontal drag is a decision rather than a scroll. */
const SWIPE_THRESHOLD = 96;

export function FeedCard({
  row,
  onPress,
  onAction,
  dimmed = false,
}: {
  row: FeedRow;
  onPress: (row: FeedRow) => void;
  onAction: (row: FeedRow, action: string) => void;
  dimmed?: boolean;
}) {
  const pan = useRef(new Animated.ValueXY()).current;

  /**
   * Swipe right to snooze, left to dismiss.
   *
   * The gesture only claims a drag that is clearly horizontal and clearly
   * deliberate: the card strip scrolls horizontally too, and stealing an
   * ordinary flick would make the feed impossible to browse.
   */
  const responder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_event, gesture) =>
        Math.abs(gesture.dx) > 18 && Math.abs(gesture.dx) > Math.abs(gesture.dy) * 2,
      onPanResponderMove: Animated.event([null, { dx: pan.x }], {
        useNativeDriver: false,
      }),
      onPanResponderRelease: (_event, gesture) => {
        if (Math.abs(gesture.dx) < SWIPE_THRESHOLD) {
          Animated.spring(pan, {
            toValue: { x: 0, y: 0 },
            useNativeDriver: false,
            bounciness: 6,
          }).start();
          return;
        }
        const action = gesture.dx > 0 ? 'snooze' : 'dismiss';
        Animated.timing(pan, {
          toValue: { x: gesture.dx > 0 ? 400 : -400, y: 0 },
          duration: 160,
          useNativeDriver: false,
        }).start(() => {
          pan.setValue({ x: 0, y: 0 });
          onAction(row, action);
        });
      },
    }),
  ).current;

  const urgent = row.tier === 'urgent';
  const today = row.tier === 'today';
  const [primary, secondary] = actionsFor(row);
  const when = deadlineLabel(row.deadline) ?? ago(row.occurred_at);

  return (
    <Animated.View
      {...responder.panHandlers}
      style={[
        styles.swipeWrap,
        {
          transform: [{ translateX: pan.x }],
          opacity: pan.x.interpolate({
            inputRange: [-260, 0, 260],
            outputRange: [0.25, 1, 0.25],
            extrapolate: 'clamp',
          }),
        },
      ]}
    >
    <Pressable
      onPress={() => onPress(row)}
      style={[styles.card, dimmed && styles.dimmed]}
    >
      <View style={styles.top}>
        <BrandMark source={row.source} size={s(24)} radius={s(7)} />
        <View
          style={[styles.tag, urgent && styles.tagUrgent, today && styles.tagToday]}
        >
          <Text
            style={[
              styles.tagText,
              urgent && styles.tagTextUrgent,
              today && styles.tagTextToday,
            ]}
          >
            {TAG_LABEL[row.type_tag] ?? row.type_tag}
          </Text>
        </View>
        <Text style={styles.ago}>{when}</Text>
      </View>

      <Text style={styles.heading} numberOfLines={2}>
        {row.sender_name ? `${row.sender_name}: ` : ''}
        {row.title}
      </Text>

      {/* The AI one-liner. Absent while classification is still pending, and
          omitted rather than replaced with a placeholder that would read like
          a summary the model never wrote. */}
      {row.summary ? (
        <Text style={styles.why} numberOfLines={2}>
          {row.summary}
        </Text>
      ) : null}

      <View style={styles.spacer} />

      <View style={styles.buttons}>
        <Pressable
          onPress={() => onAction(row, primary.id)}
          style={[styles.button, styles.buttonPrimary]}
        >
          <Text style={styles.buttonPrimaryText}>{primary.label}</Text>
        </Pressable>
        <Pressable onPress={() => onAction(row, secondary.id)} style={styles.button}>
          <Text style={styles.buttonText}>{secondary.label}</Text>
        </Pressable>
      </View>
    </Pressable>
    </Animated.View>
  );
}

/** The pagination dots under the card strip. */
export function Dots({ count, active }: { count: number; active: number }) {
  return (
    <View style={styles.dots}>
      {Array.from({ length: Math.min(count, 8) }, (_, index) => (
        <View key={index} style={[styles.dot, index === active && styles.dotOn]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  swipeWrap: { width: CARD_WIDTH },
  // Fixed so a card with no summary is not shorter than its neighbours: a
  // strip of uneven cards reads as broken rather than varied.
  cardHeight: {},
  card: {
    width: CARD_WIDTH,
    height: s(132),
    justifyContent: 'flex-start',
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(15),
    padding: s(12),
    shadowColor: '#20242B',
    shadowOpacity: 0.05,
    shadowRadius: s(10),
    shadowOffset: { width: 0, height: s(3) },
    elevation: 1,
  },
  dimmed: { opacity: 0.5 },
  top: { flexDirection: 'row', alignItems: 'center', gap: s(7), marginBottom: s(8) },
  tag: {
    borderRadius: s(4),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    paddingHorizontal: s(5),
    paddingVertical: s(2),
  },
  tagUrgent: { borderColor: colors.urgent, backgroundColor: colors.urgentSoft },
  tagToday: { borderColor: colors.accent, backgroundColor: colors.accentSoft },
  tagText: { ...type.tag, color: colors.dim },
  tagTextUrgent: { color: colors.urgent },
  tagTextToday: { color: colors.accent },
  ago: { ...type.ago, marginLeft: 'auto' },
  heading: { ...type.cardHeading, color: colors.fg, marginBottom: s(6) },
  why: { ...type.why },
  spacer: { flex: 1 },
  buttons: { flexDirection: 'row', gap: s(6) },
  button: {
    flex: 1,
    alignItems: 'center',
    borderRadius: s(9),
    paddingVertical: s(7),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  buttonPrimary: { backgroundColor: colors.accent, borderColor: colors.accent },
  buttonText: { ...type.button, color: colors.fg },
  buttonPrimaryText: { ...type.button, color: colors.onAccent, fontWeight: '600' },
  dots: {
    flexDirection: 'row',
    gap: s(4),
    justifyContent: 'center',
    paddingTop: s(9),
    paddingBottom: s(2),
  },
  dot: { width: s(5), height: s(5), borderRadius: s(2.5), backgroundColor: colors.line },
  dotOn: { width: s(14), borderRadius: s(3), backgroundColor: colors.accent },
});
