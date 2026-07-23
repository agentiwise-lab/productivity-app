/**
 * The detail sheet: the quoted original, why this tier, and the reply field.
 *
 * "Why this is urgent" is the model's own stated reason, shown verbatim. If the
 * app is going to reorder someone's day it has to be able to say why, in one
 * line, without the user having to trust it blindly. When the reason is missing
 * the block is omitted rather than filled with something plausible.
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
import { colors, space, radius, type, tierLabel } from '../theme';
import { BrandMark } from '../components/BrandMark';
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

  const send = (action: string) => {
    onAction(row, action, draft.trim() || undefined);
    setDraft('');
  };

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.sheetWrap}
      >
        <View style={styles.sheet}>
          <View style={styles.grabber} />

          <ScrollView contentContainerStyle={styles.body}>
            <View style={styles.head}>
              <BrandMark source={row.source} size={28} />
              <View style={styles.headText}>
                <Text style={styles.sender}>
                  {row.sender_name ?? row.sender_handle ?? 'Unknown'}
                </Text>
                <Text style={styles.meta}>
                  {row.context_chip ? `${row.context_chip} · ` : ''}
                  {deadlineLabel(row.deadline) ?? ago(row.occurred_at)}
                </Text>
              </View>
              <View
                style={[styles.tierPill, urgent && styles.tierPillUrgent]}
              >
                <Text style={[styles.tierText, urgent && styles.tierTextUrgent]}>
                  {tierLabel[row.tier]}
                </Text>
              </View>
            </View>

            <View style={styles.quote}>
              <Text style={styles.quoteText}>{row.title}</Text>
            </View>

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
                  style={styles.overflowBtn}
                >
                  <Text style={styles.overflowText}>{action.label}</Text>
                </Pressable>
              ))}
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(32,36,43,0.35)' },
  sheetWrap: { justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: radius.lg + 6,
    borderTopRightRadius: radius.lg + 6,
    maxHeight: '86%',
  },
  grabber: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.line,
    marginTop: space.sm,
  },
  body: { padding: space.lg, gap: space.lg, paddingBottom: space.xxl },
  head: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  headText: { flex: 1, gap: 2 },
  sender: { ...type.h2, color: colors.fg },
  meta: { ...type.small, color: colors.dim },
  tierPill: {
    backgroundColor: colors.accentSoft,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: 4,
  },
  tierPillUrgent: { backgroundColor: colors.urgentSoft },
  tierText: { ...type.small, fontWeight: '700', color: colors.accent },
  tierTextUrgent: { color: colors.urgent },
  quote: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderLeftWidth: 3,
    borderLeftColor: colors.line,
    padding: space.lg,
  },
  quoteText: { ...type.body, color: colors.fg },
  why: {
    backgroundColor: colors.accentSoft,
    borderRadius: radius.md,
    padding: space.md,
    gap: 2,
  },
  whyUrgent: { backgroundColor: colors.urgentSoft },
  whyLabel: { ...type.mono, color: colors.accent },
  whyLabelUrgent: { color: colors.urgent },
  whyText: { ...type.body, color: colors.accent },
  whyTextUrgent: { color: colors.urgent },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.line,
    padding: space.md,
    minHeight: 76,
    ...type.body,
    color: colors.fg,
  },
  actions: { flexDirection: 'row', gap: space.sm },
  primary: {
    flex: 1,
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: space.md,
    alignItems: 'center',
  },
  primaryUrgent: { backgroundColor: colors.urgent },
  busy: { opacity: 0.6 },
  primaryText: { ...type.body, fontWeight: '600', color: '#FFFFFF' },
  secondary: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.md,
    paddingVertical: space.md,
    alignItems: 'center',
  },
  secondaryText: { ...type.body, fontWeight: '600', color: colors.accent },
  overflow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  overflowBtn: {
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
  },
  overflowText: { ...type.small, fontWeight: '600', color: colors.dim },
});
