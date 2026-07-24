/**
 * Haptics mark a change of state, never motion.
 *
 * A buzz on every frame of a swipe is noise; a buzz at the moment the card
 * commits is information. Three of these exist and that is the whole set: if
 * something needs a fourth, it probably needs one of these three instead.
 *
 * `Heavy` is deliberately absent. It is reserved by convention for something
 * going wrong, and nothing in this app is heavy enough to earn it.
 */

import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

const enabled = Platform.OS === 'ios' || Platform.OS === 'android';

/**
 * iOS builds its feedback generator lazily, so the first buzz of a session
 * lands 100ms or so late, which reads as a dropped tap rather than a slow one.
 * Calling this on mount pays that cost while nobody is waiting.
 */
export function prepare() {
  if (!enabled) return;
  void Haptics.selectionAsync();
}

/** A selection moved: a tier cell, a segment, a source in the strip. */
export function select() {
  if (!enabled) return;
  void Haptics.selectionAsync();
}

/** Something committed: a card acted on, a sheet confirmed. */
export function commit() {
  if (!enabled) return;
  void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
}

/** The upstream refused. The only place a notification style is used. */
export function refused() {
  if (!enabled) return;
  void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
}
