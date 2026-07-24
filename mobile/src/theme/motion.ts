/**
 * Springs, never a duration and a bezier.
 *
 * A duration curve describes where something should be at time t. A spring
 * describes what the thing is, which is why it can be interrupted halfway and
 * still behave: a card the finger reverses mid-flight does not have to be
 * cancelled and restarted, it simply changes direction.
 */

import type { WithSpringConfig } from 'react-native-reanimated';

/** Anything the finger is currently holding, or has just let go of. */
export const gesture: WithSpringConfig = {
  damping: 22,
  stiffness: 260,
  mass: 0.9,
  overshootClamping: false,
};

/** A sheet arriving or leaving. Slower, and it must not overshoot past the
 *  screen edge, which reads as a bounce rather than a settle. */
export const sheet: WithSpringConfig = {
  damping: 30,
  stiffness: 220,
  mass: 1,
  overshootClamping: true,
};

/** A control changing state under a tap: a chip, a toggle, a segment. */
export const control: WithSpringConfig = {
  damping: 18,
  stiffness: 340,
  mass: 0.6,
};

/** Press feedback. The one place a scale is allowed. */
export const pressScale = 0.97;
