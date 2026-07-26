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
import Svg, { Rect } from 'react-native-svg';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { fonts, type as roles, space, radius, topInset, useTheme } from '../../theme';
import { T } from '../../components/ui';

/**
 * Two offset rounded cards — the app's own To-dos glyph, enlarged as a quiet
 * monochrome mark with a couple of content lines. Neutral, since this app keeps
 * hues for tiers only; it reads as the product, not a generic form.
 */
function AuthGraphic() {
  const c = useTheme();
  const S = 72;
  return (
    <View style={{ width: S, height: S, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={S} height={S} viewBox="0 0 72 72">
        {/* Back card, dim. */}
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
        {/* Front card fills with the canvas so it occludes the back where they
            overlap. */}
        <Rect
          x={14}
          y={19}
          width={32}
          height={44}
          rx={8}
          stroke={c.high}
          strokeWidth={2}
          fill={c.canvas}
        />
        {/* Two content lines on the front card. */}
        <Rect x={21} y={30} width={18} height={2.5} rx={1.25} fill={c.high} opacity={0.55} />
        <Rect x={21} y={38} width={12} height={2.5} rx={1.25} fill={c.high} opacity={0.3} />
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
          paddingHorizontal: 40,
          paddingVertical: topInset(insets.top) + space.xl,
        }}
      >
        <View style={{ width: '100%', maxWidth: 300, alignSelf: 'center', alignItems: 'center' }}>
          <AuthGraphic />

          <T role="display" style={{ textAlign: 'center', marginTop: space.md }}>
            {title}
          </T>
          {subtitle ? (
            <T
              role="secondary"
              tone="mid"
              style={{ textAlign: 'center', marginTop: space.xs, marginBottom: space.xxl }}
            >
              {subtitle}
            </T>
          ) : (
            <View style={{ height: space.xxl }} />
          )}

          <View style={{ width: '100%', maxWidth: 260, alignSelf: 'center' }}>{children}</View>

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
        borderRadius: radius.md,
        paddingHorizontal: space.md,
        height: 46,
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
          { ...roles.body, fontFamily: fonts.sans, color: c.high },
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
