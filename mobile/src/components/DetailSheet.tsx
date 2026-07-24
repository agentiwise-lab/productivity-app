/**
 * The detail sheet: where the decision is actually made.
 *
 * The regions and the split between them are unchanged, because the split is
 * the point. The head (who, where, when, category) and the footer (what you can
 * do) are fixed, and only the message scrolls between them. Letting the whole
 * sheet scroll pushes the actions off screen exactly when a long message makes
 * you want them.
 *
 * The category wash at the top is the one place the sheet is coloured. The
 * primary button is the neutral `high` fill and never a hue: a green button
 * under a green "By EOD" chip is the same colour claiming two different things.
 */

import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import {
  CATEGORY_LABEL,
  CATEGORY_OF_TIER,
  fonts,
  inset,
  radius,
  space,
  type as roles,
  useTheme,
} from '../theme';
import { BrandMark } from './BrandMark';
import { Icon } from './Icon';
import { BigButton, Chip, T, Wash } from './ui';
import { canCompose, overflowFor, railFor } from '../lib/actions';
import { readable } from '../lib/subtext';
import { ago, deadlineLabel } from '../lib/time';
import type { FeedRow } from '../api/types';

interface Props {
  row: FeedRow | null;
  busy: boolean;
  onClose: () => void;
  onAction: (row: FeedRow, action: string, body?: string) => void;
}

export function DetailSheet({ row, busy, onClose, onAction }: Props) {
  const c = useTheme();
  const [draft, setDraft] = useState('');
  if (!row) return null;

  const category = CATEGORY_OF_TIER[row.tier];
  const rail = railFor(row);
  const [primary, secondary] = rail;
  const overflow = overflowFor(row);
  const compose = canCompose(row);
  const when = deadlineLabel(row.deadline) ?? ago(row.occurred_at);
  const above =
    row.sender_name || row.sender_handle || row.context_chip || 'Unknown sender';
  const body = readable(row.body) || row.title;

  const send = (action: string) => {
    onAction(row, action, draft.trim() || undefined);
    setDraft('');
  };

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={StyleSheet.absoluteFill} onPress={onClose}>
        <View style={[StyleSheet.absoluteFill, { backgroundColor: c.scrim }]} />
      </Pressable>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1, justifyContent: 'flex-end' }}
        pointerEvents="box-none"
      >
        <View
          style={{
            height: '82%',
            backgroundColor: c.raised,
            borderTopLeftRadius: radius.lg,
            borderTopRightRadius: radius.lg,
            paddingHorizontal: space.md,
            paddingBottom: inset.bottom,
            overflow: 'hidden',
          }}
        >
          <Wash category={category} height={220} direction="vertical" alpha={0.2} />

          <View
            style={{
              width: 36,
              height: 5,
              borderRadius: radius.pill,
              backgroundColor: c.border,
              alignSelf: 'center',
              marginTop: space.xs,
              marginBottom: space.md,
            }}
          />

          {/* Head. */}
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
            <BrandMark source={row.source} size={32} />
            <View style={{ flex: 1, minWidth: 0 }}>
              <T role="body" medium lines={1}>
                {above}
              </T>
              {/* The chip only when it says something the name above does not.
                  Linear sets `context_chip` to "Linear" and has no sender, so
                  the head read "Linear" and then "Linear ·" underneath it. */}
              <T role="secondary" tone="low" numeric lines={1}>
                {row.context_chip && row.context_chip !== above
                  ? `${row.context_chip} · `
                  : ''}
                {when}
              </T>
            </View>
            {CATEGORY_LABEL[category] ? (
              <Chip
                label={CATEGORY_LABEL[category]}
                variant="solid"
                category={category}
              />
            ) : null}
          </View>

          {/* Subject. */}
          <T role="title" lines={2} style={{ marginTop: space.md }}>
            {row.title}
          </T>

          {/* Why this category. */}
          {row.reason ? (
            <View
              style={{
                marginTop: space.md,
                borderRadius: radius.md,
                padding: space.sm,
                backgroundColor: c.lift,
              }}
            >
              <T role="label" tone="mid">
                Why this is {(CATEGORY_LABEL[category] || 'here').toLowerCase()}
              </T>
              <T role="body" style={{ marginTop: space.xxs }}>
                {row.reason}
              </T>
            </View>
          ) : null}

          {/* The only region that scrolls. */}
          <ScrollView
            style={{ flex: 1, marginTop: space.md }}
            contentContainerStyle={{ paddingBottom: space.md }}
          >
            <T role="body" tone="mid">
              {body}
            </T>
          </ScrollView>

          {/* Footer. */}
          <View style={{ gap: space.sm }}>
            {compose ? (
              <View
                style={{
                  borderWidth: 1,
                  borderColor: c.border,
                  borderRadius: radius.md,
                  padding: space.sm,
                  backgroundColor: c.surface,
                  flexDirection: 'row',
                  alignItems: 'flex-end',
                  gap: space.sm,
                }}
              >
                <TextInput
                  value={draft}
                  onChangeText={setDraft}
                  // Named where there is a person to name. A Linear issue has
                  // no sender, and "Reply to this" read as a sentence that had
                  // lost its last word.
                  placeholder={
                    row.sender_name
                      ? `Reply to ${row.sender_name}`
                      : primary?.id === 'comment'
                        ? 'Add a comment'
                        : 'Write a reply'
                  }
                  placeholderTextColor={c.low}
                  multiline
                  style={{
                    flex: 1,
                    ...roles.body,
                    fontFamily: fonts.sans,
                    color: c.high,
                    maxHeight: 96,
                  }}
                />
                <Pressable
                  // An empty reply is rejected server-side, so the button is
                  // inert until there is something to send rather than
                  // offering a round trip that can only fail.
                  disabled={busy || !draft.trim()}
                  onPress={() => send(primary?.id ?? 'reply')}
                  accessibilityLabel="Send"
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: radius.pill,
                    backgroundColor: c.high,
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: draft.trim() ? 1 : 0.4,
                  }}
                >
                  <Icon name="send" size={20} color={c.canvas} />
                </Pressable>
              </View>
            ) : null}

            <View style={{ flexDirection: 'row', gap: space.sm }}>
              {primary ? (
                <BigButton
                  label={busy ? 'Working...' : primary.label}
                  variant="primary"
                  disabled={busy}
                  onPress={() => send(primary.id)}
                  style={{ flex: 1 }}
                />
              ) : null}
              {secondary ? (
                <BigButton
                  label={secondary.label}
                  disabled={busy}
                  onPress={() => send(secondary.id)}
                  style={{ flex: 1 }}
                />
              ) : null}
            </View>

            {overflow.length > 0 ? (
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.xs }}>
                {overflow.map((action) => (
                  <Chip
                    key={action.id}
                    label={action.label}
                    variant="outline"
                    onPress={() => send(action.id)}
                  />
                ))}
              </View>
            ) : null}
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
