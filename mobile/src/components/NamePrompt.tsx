/**
 * A one-field modal for the display name, shared by two callers: the You tab's
 * "edit" affordance, and the automatic prompt shown once after signup when no
 * name is set yet. Keeping it a component rather than an Alert.prompt is what
 * lets it work on web, where the app is also driven.
 */

import React, { useEffect, useState } from 'react';
import { Modal, Pressable, TextInput, View } from 'react-native';
import { radius, space, useTheme } from '../theme';
import { T } from './ui';

interface Props {
  visible: boolean;
  initialValue: string;
  onSave: (name: string) => void;
  onCancel: () => void;
  title?: string;
  subtitle?: string;
}

export function NamePrompt({
  visible,
  initialValue,
  onSave,
  onCancel,
  title = 'Your name',
  subtitle,
}: Props) {
  const c = useTheme();
  const [value, setValue] = useState(initialValue);

  // Reset the field to the current name each time the sheet opens, so an edit
  // starts from what is set rather than from a stale keystroke.
  useEffect(() => {
    if (visible) setValue(initialValue);
  }, [visible, initialValue]);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onCancel}
    >
      <Pressable
        onPress={onCancel}
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
          <T role="heading">{title}</T>
          {subtitle ? (
            <T role="secondary" tone="mid">
              {subtitle}
            </T>
          ) : null}
          <TextInput
            value={value}
            onChangeText={setValue}
            placeholder="e.g. Vicky"
            placeholderTextColor={c.mid}
            autoFocus
            maxLength={80}
            returnKeyType="done"
            onSubmitEditing={() => onSave(value)}
            style={{
              borderWidth: 1,
              borderColor: c.border,
              borderRadius: radius.md,
              paddingHorizontal: space.sm,
              paddingVertical: space.sm,
              color: c.high,
              fontSize: 16,
              backgroundColor: c.surface,
            }}
          />
          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'flex-end',
              alignItems: 'center',
              gap: space.md,
            }}
          >
            <Pressable onPress={onCancel} hitSlop={8} style={{ padding: space.xs }}>
              <T role="label" tone="mid">
                Cancel
              </T>
            </Pressable>
            <Pressable
              onPress={() => onSave(value)}
              hitSlop={8}
              style={{
                backgroundColor: c.high,
                borderRadius: radius.pill,
                paddingVertical: space.xs,
                paddingHorizontal: space.md,
              }}
            >
              <T role="label" colour={c.canvas}>
                Save
              </T>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
