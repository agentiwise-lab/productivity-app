/**
 * The detail sheet.
 *
 * Three regions, and the split is the point. The head (who, where, when, tier)
 * and the footer (what you can do) are fixed, and only the message scrolls
 * between them. Letting the whole sheet scroll pushes the actions off-screen
 * exactly when a long message makes you want them.
 *
 * The message itself is shown in full. A row that says only "dswh/glued_landing"
 * and offers a reply box is asking you to answer something you have not read.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  Modal,
  Pressable,
  TextInput,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { colors, s, text, type, tierLabel } from '../theme';
import { BrandMark } from './BrandMark';
import { ago, deadlineLabel } from '../lib/time';
import { actionsFor, overflowFor } from '../lib/actions';
import type { FeedRow } from '../api/types';

interface Props {
  row: FeedRow | null;
  busy: boolean;
  onClose: () => void;
  onAction: (row: FeedRow, action: string, body?: string) => void;
}

export function DetailSheet({ row, busy, onClose, onAction }: Props) {
  const [draft, setDraft] = useState('');
  if (!row) return null;

  const urgent = row.tier === 'urgent';
  const [primary, secondary] = actionsFor(row);
  const overflow = overflowFor(row);
  const canReply = ['reply', 'comment'].includes(primary.id);
  const when = deadlineLabel(row.deadline) ?? ago(row.occurred_at);
  const body = row.body?.trim() || row.title;

  const send = (action: string) => {
    onAction(row, action, draft.trim() || undefined);
    setDraft('');
  };

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      {/* The backdrop fills the screen behind the sheet rather than sitting
          above it in the flow. As a flex sibling it stole the height the sheet
          needed, and the message area collapsed to a sliver. */}
      <Pressable style={StyleSheet.absoluteFill} onPress={onClose}>
        <View style={styles.backdrop} />
      </Pressable>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.wrap}
        pointerEvents="box-none"
      >
        <View style={styles.sheet}>
          <View style={styles.grabber} />

          {/* Fixed head. */}
          <View style={styles.head}>
            <BrandMark source={row.source} size={s(24)} radius={s(7)} />
            <View style={styles.headText}>
              <Text style={styles.sender} numberOfLines={1}>
                {row.sender_name || row.sender_handle || row.context_chip || 'Unknown sender'}
              </Text>
              <Text style={styles.meta} numberOfLines={1}>
                {row.context_chip ? `${row.context_chip} · ` : ''}
                {when}
              </Text>
            </View>
            <View style={[styles.pill, urgent && styles.pillUrgent]}>
              <Text style={[styles.pillText, urgent && styles.pillTextUrgent]}>
                {tierLabel[row.tier]}
              </Text>
            </View>
          </View>

          <Text style={styles.subject} numberOfLines={2}>
            {row.title}
          </Text>

          {row.reason ? (
            <View style={[styles.why, urgent && styles.whyUrgent]}>
              <Text style={[styles.whyLabel, urgent && styles.whyLabelUrgent]}>
                Why this is {tierLabel[row.tier].toLowerCase()}
              </Text>
              <Text style={[styles.whyText, urgent && styles.whyTextUrgent]}>
                {row.reason}
              </Text>
            </View>
          ) : null}

          {/* The only scrolling region. */}
          <ScrollView style={styles.bodyScroll} contentContainerStyle={styles.bodyPad}>
            <Text style={styles.bodyText}>{body}</Text>
          </ScrollView>

          {/* Fixed footer. */}
          <View style={styles.footer}>
            {canReply ? (
              <TextInput
                value={draft}
                onChangeText={setDraft}
                placeholder={`Reply to ${row.sender_name ?? 'this'}...`}
                placeholderTextColor={colors.dim}
                multiline
                style={styles.input}
              />
            ) : null}

            <View style={styles.actions}>
              <Pressable
                disabled={busy}
                onPress={() => send(primary.id)}
                style={[styles.primary, urgent && styles.primaryUrgent, busy && styles.busy]}
              >
                <Text style={styles.primaryText}>
                  {busy ? 'Working...' : primary.label}
                </Text>
              </Pressable>
              <Pressable
                disabled={busy}
                onPress={() => send(secondary.id)}
                style={styles.secondary}
              >
                <Text style={styles.secondaryText}>{secondary.label}</Text>
              </Pressable>
            </View>

            <View style={styles.overflow}>
              {overflow.map((action) => (
                <Pressable
                  key={action.id}
                  disabled={busy}
                  onPress={() => send(action.id)}
                  style={styles.chip}
                >
                  <Text style={styles.chipText}>{action.label}</Text>
                </Pressable>
              ))}
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(32,36,43,0.32)' },
  wrap: { flex: 1, justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: s(18),
    borderTopRightRadius: s(18),
    // Tall by default: the sheet is where you read, so it should not open as a
    // letterbox that needs dragging before it is useful.
    height: '82%',
    overflow: 'hidden',
  },
  grabber: {
    alignSelf: 'center',
    width: s(26),
    height: s(3),
    borderRadius: s(2),
    backgroundColor: colors.line,
    marginTop: s(6),
    marginBottom: s(2),
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: s(8),
    paddingHorizontal: s(14),
    paddingTop: s(8),
  },
  headText: { flex: 1 },
  sender: { ...type.groupLabel, color: colors.fg },
  meta: { ...type.rowSub, marginTop: s(1) },
  pill: {
    backgroundColor: colors.accentSoft,
    borderRadius: 999,
    paddingHorizontal: s(8),
    paddingVertical: s(3),
  },
  pillUrgent: { backgroundColor: colors.urgentSoft },
  pillText: { ...type.tag, color: colors.accent },
  pillTextUrgent: { color: colors.urgent },
  subject: {
    ...type.cardHeading,
    color: colors.fg,
    paddingHorizontal: s(14),
    paddingTop: s(10),
  },
  why: {
    marginHorizontal: s(14),
    marginTop: s(9),
    backgroundColor: colors.accentSoft,
    borderRadius: s(9),
    paddingHorizontal: s(10),
    paddingVertical: s(7),
  },
  whyUrgent: { backgroundColor: colors.urgentSoft },
  whyLabel: { ...type.tag, color: colors.accent },
  whyLabelUrgent: { color: colors.urgent },
  whyText: { ...text.small, color: colors.accent, marginTop: s(2) },
  whyTextUrgent: { color: colors.urgent },
  bodyScroll: {
    flex: 1,
    marginTop: s(10),
    marginHorizontal: s(14),
    backgroundColor: colors.surface,
    borderRadius: s(11),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  bodyPad: { padding: s(12) },
  bodyText: { ...text.body, color: colors.fg },
  footer: {
    paddingHorizontal: s(14),
    paddingTop: s(10),
    paddingBottom: s(20),
    gap: s(8),
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
    backgroundColor: colors.bg,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: s(9),
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    paddingHorizontal: s(10),
    paddingVertical: s(8),
    minHeight: s(38),
    maxHeight: s(70),
    ...text.body,
    color: colors.fg,
  },
  actions: { flexDirection: 'row', gap: s(6) },
  primary: {
    flex: 1,
    backgroundColor: colors.accent,
    borderRadius: s(9),
    paddingVertical: s(9),
    alignItems: 'center',
  },
  primaryUrgent: { backgroundColor: colors.urgent },
  busy: { opacity: 0.6 },
  primaryText: { ...type.button, fontWeight: '600', color: colors.onAccent },
  secondary: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    borderRadius: s(9),
    paddingVertical: s(9),
    alignItems: 'center',
  },
  secondaryText: { ...type.button, fontWeight: '600', color: colors.accent },
  overflow: { flexDirection: 'row', flexWrap: 'wrap', gap: s(6) },
  chip: {
    paddingHorizontal: s(10),
    paddingVertical: s(5),
    borderRadius: 999,
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  chipText: { ...type.chipLabel, color: colors.dim },
});
