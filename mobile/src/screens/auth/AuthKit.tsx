/**
 * Shared furniture for the four auth screens, so they read as one flow.
 *
 * `AuthShell` fixes the layout every step shares: the title, an optional line
 * under it, the error slot, the body, and a footer link. `Field` is the one
 * text input, styled to match the composer in DetailSheet (bordered card,
 * no web focus ring) rather than inventing a second input look.
 */

import React from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  TextInput,
  View,
  type KeyboardTypeOptions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { fonts, type as roles, space, radius, topInset, useTheme } from '../../theme';
import { T } from '../../components/ui';

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
      <View
        style={{
          flex: 1,
          paddingHorizontal: space.lg,
          paddingTop: topInset(insets.top) + space.xxl,
        }}
      >
        <T role="hero" style={{ marginBottom: space.xs }}>
          {title}
        </T>
        {subtitle ? (
          <T role="secondary" tone="mid" style={{ marginBottom: space.lg }}>
            {subtitle}
          </T>
        ) : (
          <View style={{ height: space.lg }} />
        )}

        {children}

        {/* The error keeps a fixed slot so the layout does not jump when it
            appears. */}
        <View style={{ minHeight: 22, marginTop: space.sm }}>
          {error ? (
            <T role="secondary" colour={c.hue.urgent}>
              {error}
            </T>
          ) : null}
        </View>

        {footer ? <View style={{ marginTop: space.md }}>{footer}</View> : null}
      </View>
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
        height: 52,
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
