/**
 * Shared furniture for the four auth screens, so they read as one flow.
 *
 * `AuthShell` centres the whole step — a branded ring graphic, the title, a line
 * under it, the body, an error slot and a footer — vertically and horizontally,
 * on a `maxWidth` column so it holds together on any width. `Field` is the one
 * text input, a tall bordered card. Everything reads from the palette, so it
 * follows the app's light/dark theme with no per-screen colour.
 */

import React from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  TextInput,
  View,
  type KeyboardTypeOptions,
} from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { fonts, type as roles, space, radius, topInset, useTheme } from '../../theme';
import { T } from '../../components/ui';

/**
 * The app's signature: a ring of the four category hues on a quiet track. It is
 * the same shape the Day screen wears, so the sign-in surface already feels like
 * the product rather than a generic form. Colours come from the palette, so it
 * inverts cleanly between themes.
 */
function AuthGraphic() {
  const c = useTheme();
  const SIZE = 132;
  const R = 52;
  const STROKE = 13;
  const CENTRE = SIZE / 2;
  const circumference = 2 * Math.PI * R;
  const segment = circumference / 4;
  const gap = 7;
  const hues = [c.hue.urgent, c.hue.byEod, c.hue.canWait, c.hue.later];
  return (
    <View style={{ width: SIZE, height: SIZE, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={SIZE} height={SIZE}>
        <Circle cx={CENTRE} cy={CENTRE} r={R} stroke={c.surface} strokeWidth={STROKE} fill="none" />
        {hues.map((hue, i) => (
          <Circle
            key={i}
            cx={CENTRE}
            cy={CENTRE}
            r={R}
            stroke={hue}
            strokeWidth={STROKE}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${segment - gap} ${circumference - (segment - gap)}`}
            strokeDashoffset={-segment * i}
            transform={`rotate(-90 ${CENTRE} ${CENTRE})`}
          />
        ))}
        <Circle cx={CENTRE} cy={CENTRE} r={5} fill={c.high} />
      </Svg>
    </View>
  );
}

export function AuthShell({
  title,
  subtitle,
  error,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  error?: string | null;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: c.canvas }}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{
          flexGrow: 1,
          justifyContent: 'center',
          paddingHorizontal: space.lg,
          paddingVertical: topInset(insets.top) + space.xl,
        }}
      >
        <View style={{ width: '100%', maxWidth: 420, alignSelf: 'center', alignItems: 'center' }}>
          <AuthGraphic />

          <T role="hero" style={{ textAlign: 'center', marginTop: space.lg }}>
            {title}
          </T>
          {subtitle ? (
            <T
              role="secondary"
              tone="mid"
              style={{ textAlign: 'center', marginTop: space.xs, marginBottom: space.xl }}
            >
              {subtitle}
            </T>
          ) : (
            <View style={{ height: space.xl }} />
          )}

          <View style={{ width: '100%' }}>{children}</View>

          {/* Fixed error slot, so the layout does not jump when it appears. */}
          <View style={{ minHeight: 22, marginTop: space.sm, alignItems: 'center' }}>
            {error ? (
              <T role="secondary" colour={c.hue.urgent} style={{ textAlign: 'center' }}>
                {error}
              </T>
            ) : null}
          </View>

          {footer ? (
            <View style={{ marginTop: space.md, alignItems: 'center' }}>{footer}</View>
          ) : null}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

export function Field({
  value,
  onChangeText,
  placeholder,
  keyboardType,
  secureTextEntry,
  autoFocus,
  autoCapitalize = 'none',
  maxLength,
  onSubmitEditing,
}: {
  value: string;
  onChangeText: (next: string) => void;
  placeholder: string;
  keyboardType?: KeyboardTypeOptions;
  secureTextEntry?: boolean;
  autoFocus?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  maxLength?: number;
  onSubmitEditing?: () => void;
}) {
  const c = useTheme();
  return (
    <View
      style={{
        borderWidth: 1,
        borderColor: c.border,
        borderRadius: radius.lg,
        paddingHorizontal: space.md,
        height: 58,
        justifyContent: 'center',
        backgroundColor: c.surface,
        marginBottom: space.sm,
      }}
    >
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={c.low}
        keyboardType={keyboardType}
        secureTextEntry={secureTextEntry}
        autoFocus={autoFocus}
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        maxLength={maxLength}
        onSubmitEditing={onSubmitEditing}
        returnKeyType="go"
        style={[
          { ...roles.title, fontFamily: fonts.sans, color: c.high, textAlign: 'center' },
          { outline: 'none' } as object,
        ]}
      />
    </View>
  );
}

export function LinkText({ label, onPress }: { label: string; onPress: () => void }) {
  const c = useTheme();
  return (
    <Pressable onPress={onPress} hitSlop={8}>
      <T role="secondary" colour={c.high} medium>
        {label}
      </T>
    </Pressable>
  );
}
