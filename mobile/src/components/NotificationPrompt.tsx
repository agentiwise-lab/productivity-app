/**
 * Asking for notification permission, in our own words, before the OS asks in
 * its words.
 *
 * The OS prompt is a one-shot resource: on iOS a denial is close to permanent,
 * because undoing it means finding Settings and a switch nobody has a reason to
 * look for. So it is never the user's first contact with the idea. This card
 * makes the case, and only its affirmative button spends the prompt. "Not now"
 * costs nothing, because it leaves the OS permission unasked and the You tab
 * can offer it again.
 *
 * Shape and sizes come from `NamePrompt`, deliberately: that is the other modal
 * this app shows once, right after signup, and reusing it means this introduces
 * no new geometry. The primary action is the small pill, not a full-width
 * button, which inside a card of this width would read as a landing page rather
 * than as this app.
 *
 * The mark is `AuthGraphic` from the sign-in flow, so the thing asking for the
 * permission is visibly the thing that signed you in. It stays neutral: this
 * app keeps colour for tiers, and an icon in the urgent hue would claim a tier
 * the app itself does not have.
 */

import React from 'react';
import { Modal, Pressable, View } from 'react-native';
import Svg, { Rect } from 'react-native-svg';

import { radius, space, useTheme } from '../theme';
import { T } from './ui';

/** The two offset cards, at the size a modal wants rather than a screen's 72. */
function Mark({ size = 52 }: { size?: number }) {
  const c = useTheme();
  return (
    <Svg width={size} height={size} viewBox="0 0 72 72">
      <Rect
        x={26}
        y={13}
        width={32}
        height={44}
        rx={8}
        stroke={c.high}
        strokeOpacity={0.25}
        strokeWidth={2}
        fill="none"
      />
      {/* Filled with the card's own surface so it occludes the one behind it. */}
      <Rect
        x={14}
        y={19}
        width={32}
        height={44}
        rx={8}
        stroke={c.high}
        strokeWidth={2}
        fill={c.raised}
      />
      <Rect x={21} y={30} width={18} height={2.5} rx={1.25} fill={c.high} opacity={0.55} />
      <Rect x={21} y={38} width={12} height={2.5} rx={1.25} fill={c.high} opacity={0.3} />
    </Svg>
  );
}

interface Props {
  visible: boolean;
  /** Fires the OS prompt. The only place in the app that may. */
  onTurnOn: () => void;
  onDismiss: () => void;
}

export function NotificationPrompt({ visible, onTurnOn, onDismiss }: Props) {
  const c = useTheme();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onDismiss}
    >
      <Pressable
        onPress={onDismiss}
        style={{
          flex: 1,
          backgroundColor: c.scrim,
          justifyContent: 'center',
          padding: space.lg,
        }}
      >
        {/* Stop taps inside the card from dismissing it. */}
        <Pressable
          onPress={() => {}}
          style={{
            backgroundColor: c.raised,
            borderRadius: radius.lg,
            padding: space.lg,
            gap: space.md,
          }}
        >
          <Mark />

          {/* Three claims, each one the code actually keeps: the tier filter,
              the end-of-day bound, and the once-ever dedupe. A specific promise
              is the only kind worth granting a permission for. */}
          <T role="heading">We&apos;ll only buzz for what&apos;s urgent</T>
          <T role="secondary" tone="mid">
            Not every email. Not every Slack message. Just the things that need
            you before end of day. And never twice for the same thing.
          </T>

          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'flex-end',
              alignItems: 'center',
              gap: space.md,
            }}
          >
            <Pressable onPress={onDismiss} hitSlop={8} style={{ padding: space.xs }}>
              <T role="label" tone="mid">
                Not now
              </T>
            </Pressable>
            <Pressable
              onPress={onTurnOn}
              hitSlop={8}
              style={{
                backgroundColor: c.high,
                borderRadius: radius.pill,
                paddingVertical: space.xs,
                paddingHorizontal: space.md,
              }}
            >
              <T role="label" colour={c.canvas}>
                Turn them on
              </T>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
