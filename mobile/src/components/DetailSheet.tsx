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

import React, { useEffect, useState } from 'react';
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
import { needsComposer, overflowFor, railFor } from '../lib/actions';
import { headerSubline, primaryLine } from '../lib/rowText';
import { readable } from '../lib/subtext';
import { ago, deadlineLabel } from '../lib/time';
import type { FeedRow } from '../api/types';

interface Props {
  row: FeedRow | null;
  busy: boolean;
  /** Open straight into the composer, set when the sheet was opened by Reply. */
  startComposing?: boolean;
  onClose: () => void;
  onAction: (row: FeedRow, action: string, body?: string) => void;
}

export function DetailSheet({
  row,
  busy,
  startComposing = false,
  onClose,
  onAction,
}: Props) {
  const c = useTheme();
  const [draft, setDraft] = useState('');
  // Which action, if any, the composer is open for. Null means it is closed and
  // the buttons are showing. It opens only when a reply or comment button is
  // pressed, or when the sheet was opened by one.
  const [composing, setComposing] = useState<string | null>(null);

  useEffect(() => {
    if (!row) return;
    const composeId = railFor(row).find((a) => needsComposer(a.id))?.id ?? null;
    setComposing(startComposing ? composeId : null);
    setDraft('');
  }, [row?.id, startComposing]);

  if (!row) return null;

  const category = CATEGORY_OF_TIER[row.tier];
  const rail = railFor(row);
  const overflow = overflowFor(row);
  // Everything actionable except Open, which is a link at the top now, and
  // deduped so the primary and the overflow never draw the same button twice.
  const buttons = dedupe([...rail, ...overflow]).filter((a) => a.id !== 'open');
  const canOpen = !!row.url;
  const when = deadlineLabel(row.deadline) ?? ago(row.occurred_at);
  const above = headerSubline(row) ?? 'Unknown sender';
  const body = readable(row.body) || primaryLine(row);

  const send = (action: string) => {
    onAction(row, action, draft.trim() || undefined);
    setDraft('');
    setComposing(null);
  };

  const tap = (id: string) => {
    // A reply or a comment opens the composer rather than sending; a second tap
    // on the same one closes it again. Everything else acts at once.
    if (needsComposer(id)) {
      setComposing((current) => (current === id ? null : id));
      return;
    }
    send(id);
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
              <T role="secondary" tone="low" numeric lines={1}>
                {when}
              </T>
            </View>
            {/* Open is a quiet link here, not a full-width button below: it
                leaves the app rather than doing anything to the item, so it
                does not belong among the actions that decide it. */}
            {canOpen ? (
              <Pressable
                onPress={() => onAction(row, 'open')}
                hitSlop={10}
                accessibilityLabel="Open"
                style={({ pressed }) => [
                  {
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: space.xxs,
                    paddingVertical: space.xxs,
                    paddingHorizontal: space.xs,
                    borderRadius: radius.sm,
                    borderWidth: 1,
                    borderColor: c.border,
                  },
                  pressed ? { opacity: 0.6 } : null,
                ]}
              >
                <T role="label" tone="mid">
                  Open
                </T>
                <Icon name="external" size={13} color={c.mid} />
              </Pressable>
            ) : null}
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
            {primaryLine(row)}
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

          {/* The only region that scrolls. Empty when the body would only
              repeat the title, which is the case for a mail whose subject was
              its message. */}
          <ScrollView
            style={{ flex: 1, marginTop: space.md }}
            contentContainerStyle={{ paddingBottom: space.md }}
          >
            {body && body !== primaryLine(row) ? (
              <T role="body" tone="mid">
                {body}
              </T>
            ) : null}
          </ScrollView>

          {/* Footer. */}
          <View style={{ gap: space.sm }}>
            {/* The composer, only when a reply or comment button opened it. */}
            {composing ? (
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
                  autoFocus
                  placeholder={
                    composing === 'comment'
                      ? 'Add a comment'
                      : row.sender_name
                        ? `Reply to ${row.sender_name}`
                        : 'Write a reply'
                  }
                  placeholderTextColor={c.low}
                  multiline
                  // The composer already sits inside a bordered card, so the
                  // browser's own focus ring drew a second rectangle inside the
                  // first. `outline` is a web-only prop react-native-web reads.
                  style={[
                    {
                      flex: 1,
                      ...roles.body,
                      fontFamily: fonts.sans,
                      color: c.high,
                      maxHeight: 96,
                    },
                    { outline: 'none' } as object,
                  ]}
                />
                <Pressable
                  // Inert until there is something to send: an empty reply is
                  // rejected server-side, so the button offers no round trip
                  // that can only fail, and it is never pre-selected.
                  disabled={busy || !draft.trim()}
                  onPress={() => send(composing)}
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

            {/* The actions, none of them pre-selected. The white "active" fill
                means one thing only: the composer for this button is open. So a
                sheet opened to read shows a flat row, and a button lights up
                exactly when it is the one you are writing under. */}
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {buttons.map((action) => {
                const composerButton = needsComposer(action.id);
                const active = composing === action.id;
                return (
                  <BigButton
                    key={action.id}
                    label={busy && !composerButton ? 'Working...' : action.label}
                    variant={active ? 'primary' : 'secondary'}
                    disabled={busy}
                    onPress={() => tap(action.id)}
                    style={{ flexGrow: 1, flexBasis: buttons.length > 2 ? '30%' : 0 }}
                  />
                );
              })}
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

/** First occurrence of each action id wins, so the same button is never drawn
 *  twice when the rail and the overflow overlap. */
function dedupe<T extends { id: string }>(actions: T[]): T[] {
  const seen = new Set<string>();
  return actions.filter((action) =>
    seen.has(action.id) ? false : (seen.add(action.id), true),
  );
}
