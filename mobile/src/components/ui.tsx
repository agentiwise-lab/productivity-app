/**
 * The primitives every screen is assembled from.
 *
 * Each one is a single shape with a fixed geometry, transcribed from the
 * mockup. A chip is 28 tall with 12 of padding and a radius of 8, everywhere,
 * and there is no prop to make it smaller: a control that shrinks to fit its
 * container is how a system turns back into a pile of components.
 */

import React from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  maxScale,
  mono,
  radius,
  size,
  space,
  fonts,
  type as roles,
  useTheme,
  wash as washStops,
  type Category,
  type Palette,
} from '../theme';
import { Icon, type GlyphName } from './Icon';

/* ── text ──────────────────────────────────────────────────────────── */

type Role = keyof typeof roles;
type Tone = 'high' | 'mid' | 'low' | 'faint' | 'onSolid';

interface TProps {
  role?: Role;
  tone?: Tone;
  /** Machine values only: counts, times, ages, ids, refs. */
  numeric?: boolean;
  /** The one weight between body and heading, for a name inside a line. */
  medium?: boolean;
  colour?: string;
  lines?: number;
  style?: StyleProp<TextStyle>;
  children?: React.ReactNode;
}

export function T({
  role = 'body',
  tone = 'high',
  numeric,
  medium,
  colour,
  lines,
  style,
  children,
}: TProps) {
  const c = useTheme();
  const base = numeric && role in mono ? mono[role as keyof typeof mono] : roles[role];
  return (
    <Text
      numberOfLines={lines}
      // Body copy scales all the way. The three display roles clamp, past
      // which a 56pt hero stops fitting inside its own ring.
      maxFontSizeMultiplier={maxScale[role as keyof typeof maxScale]}
      allowFontScaling={role !== 'hero'}
      style={[
        base as TextStyle,
        medium ? { fontFamily: fonts.sansMedium } : null,
        { color: colour ?? c[tone] },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

/* ── chips ─────────────────────────────────────────────────────────── */

interface ChipProps {
  label: string;
  /** Solid fills with the category hue. Outline and ghost stay neutral. */
  variant?: 'solid' | 'outline' | 'ghost';
  category?: Category;
  glyph?: GlyphName;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

export function Chip({
  label,
  variant = 'outline',
  category,
  glyph,
  onPress,
  style,
}: ChipProps) {
  const c = useTheme();
  const solid = variant === 'solid';
  const fill = solid ? c.hue[category ?? 'none'] : undefined;
  const text = solid ? c.onSolid : variant === 'ghost' ? c.low : c.mid;

  const body = (
    <View
      style={[
        {
          height: size.chip,
          paddingHorizontal: variant === 'ghost' ? 0 : space.sm,
          borderRadius: radius.sm,
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.xs,
          alignSelf: 'flex-start',
        },
        solid ? { backgroundColor: fill } : null,
        variant === 'outline'
          ? { borderWidth: 1, borderColor: c.border }
          : null,
        style,
      ]}
    >
      {glyph ? <Icon name={glyph} size={14} color={text} /> : null}
      <T role="label" colour={text}>
        {label}
      </T>
    </View>
  );

  if (!onPress) return body;
  return (
    // 28 is legible but under the 44 minimum for a target, so the difference
    // is made up in hitSlop rather than by growing the shape.
    <Pressable onPress={onPress} hitSlop={8}>
      {body}
    </Pressable>
  );
}

/* ── segmented ─────────────────────────────────────────────────────── */

export function Segmented<Value extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: Value; label: string }[];
  value: Value;
  onChange: (next: Value) => void;
}) {
  const c = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        height: size.segmented,
        borderRadius: radius.pill,
        backgroundColor: c.overlay,
        padding: 2,
      }}
    >
      {options.map((option) => {
        const on = option.value === value;
        return (
          <Pressable
            key={option.value}
            onPress={() => onChange(option.value)}
            style={[
              {
                flex: 1,
                borderRadius: radius.pill,
                alignItems: 'center',
                justifyContent: 'center',
              },
              on
                ? {
                    backgroundColor: c.raised,
                    borderWidth: 1,
                    borderColor: c.border,
                  }
                : null,
            ]}
          >
            <T role="label" tone={on ? 'high' : 'low'}>
              {option.label}
            </T>
          </Pressable>
        );
      })}
    </View>
  );
}

/* ── toggle ────────────────────────────────────────────────────────── */

export function Toggle({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  const c = useTheme();
  return (
    <Pressable onPress={() => onChange(!value)} hitSlop={8}>
      <View
        style={[
          {
            width: 51,
            height: 31,
            borderRadius: radius.pill,
            padding: 2,
            backgroundColor: value ? c.high : c.overlay,
          },
          value ? null : { borderWidth: 1, borderColor: c.hairline },
        ]}
      >
        <View
          style={{
            width: 27,
            height: 27,
            borderRadius: radius.pill,
            backgroundColor: value ? c.canvas : c.faint,
            marginLeft: value ? 20 : 0,
          }}
        />
      </View>
    </Pressable>
  );
}

/* ── buttons ───────────────────────────────────────────────────────── */

export function BigButton({
  label,
  variant = 'secondary',
  onPress,
  disabled,
  style,
}: {
  label: string;
  /**
   * Primary is the neutral `high` fill, never a category hue. A hue on a
   * button competes with the same hue meaning "by EOD" two lines above it.
   */
  variant?: 'primary' | 'secondary';
  onPress?: () => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const c = useTheme();
  const primary = variant === 'primary';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        {
          height: size.bigButton,
          borderRadius: radius.md,
          alignItems: 'center',
          justifyContent: 'center',
        },
        primary
          ? { backgroundColor: c.high }
          : { borderWidth: 1, borderColor: c.border },
        pressed ? { opacity: 0.7 } : null,
        disabled ? { opacity: 0.5 } : null,
        style,
      ]}
    >
      <T role="body" medium colour={primary ? c.canvas : c.high}>
        {label}
      </T>
    </Pressable>
  );
}

/** The 44pt circle used for the two actions in a board's header. */
export function CircularAction({
  glyph,
  onPress,
  label,
  compact = false,
}: {
  glyph: GlyphName;
  onPress?: () => void;
  label: string;
  /** A smaller circle for a secondary control that must not dominate a row. */
  compact?: boolean;
}) {
  const c = useTheme();
  const dim = compact ? 34 : size.control;
  return (
    <Pressable
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={compact ? 10 : 0}
      style={({ pressed }) => [
        {
          width: dim,
          height: dim,
          borderRadius: radius.pill,
          backgroundColor: c.overlay,
          borderWidth: 1,
          borderColor: c.border,
          alignItems: 'center',
          justifyContent: 'center',
        },
        pressed ? { opacity: 0.7 } : null,
      ]}
    >
      <Icon name={glyph} size={compact ? 16 : 20} color={c.high} />
    </Pressable>
  );
}

/* ── structure ─────────────────────────────────────────────────────── */

export function SectionLabel({
  label,
  count,
  right,
  tight,
}: {
  label: string;
  count?: string | null;
  right?: React.ReactNode;
  /** 24 above instead of 32, where the label follows something it belongs to. */
  tight?: boolean;
}) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.xs,
        paddingHorizontal: space.md,
        marginTop: tight ? space.lg : space.xl,
        marginBottom: space.xs,
      }}
    >
      <T role="label" tone="low">
        {label}
      </T>
      <View style={{ flex: 1 }} />
      {count ? (
        <T role="secondary" tone="low" numeric>
          {count}
        </T>
      ) : null}
      {right}
    </View>
  );
}

/** Inset to the text origin, never full width, wherever rows are not cards. */
export function Separator({ inset = 48 }: { inset?: number }) {
  const c = useTheme();
  return (
    <View
      style={{
        height: StyleSheet.hairlineWidth,
        backgroundColor: c.hairline,
        marginLeft: inset,
      }}
    />
  );
}

/** The category wash: 120 wide behind a row, 220 tall at the top of a sheet. */
export function Wash({
  category,
  width,
  height,
  alpha = 0.16,
  direction = 'horizontal',
}: {
  category: Category;
  width?: number;
  height?: number;
  alpha?: number;
  /** Diagonal runs 135 degrees, which is what a summary card uses. */
  direction?: 'horizontal' | 'vertical' | 'diagonal';
}) {
  const c = useTheme();
  const horizontal = direction === 'horizontal';
  return (
    <LinearGradient
      colors={washStops(c, category, alpha) as unknown as [string, string]}
      start={{ x: 0, y: 0 }}
      end={
        direction === 'horizontal'
          ? { x: 1, y: 0 }
          : direction === 'vertical'
            ? { x: 0, y: 1 }
            : { x: 0.7, y: 0.7 }
      }
      pointerEvents="none"
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        ...(horizontal ? { bottom: 0, width } : { right: 0, height }),
      }}
    />
  );
}

/** Every screen's palette, for the handful of places a raw value is needed. */
export type { Palette };
