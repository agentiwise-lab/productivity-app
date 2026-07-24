/**
 * What each source's row says, and where.
 *
 * Every source phrases the same three questions differently: who or what is
 * this from, what is it, and what does it say. A GitHub item is a repo and a PR
 * title; a Gmail item is a sender and a subject and a body; a Slack DM is a
 * person and their message. Left to a single generic rule they came out wrong
 * in opposite directions: the mail showed "Inbox" where the sender belonged,
 * and the Slack DM showed its own message twice because the message was both
 * the title and, lacking anything else, the subtitle.
 *
 * These four functions are the single place that decides. The feed card has a
 * header, so it never repeats in its subtitle what the header already shows; a
 * list row has no header, so its subtitle carries the context instead.
 */

import type { FeedRow, TypeTag } from '../api/types';
import { decodeEntities, oneLine } from './subtext';

const SOURCE_NAME: Record<FeedRow['source'], string> = {
  github: 'GitHub',
  slack: 'Slack',
  gmail: 'Gmail',
  linear: 'Linear',
  calendar: 'Calendar',
  google_docs: 'Google Docs',
};

/** The kind of ask, in words, for the sources that carry no better context. */
const TYPE_PHRASE: Record<TypeTag, string> = {
  review: 'Review requested',
  approve: 'Approval requested',
  reply: 'Awaiting your reply',
  assigned: 'Assigned to you',
  comment: 'New comment',
  decide: 'Needs a decision',
  rsvp: 'Invitation',
  alert: 'Alert',
  fyi: 'For your information',
};

const clean = (value?: string | null): string | null => {
  const t = decodeEntities((value ?? '').trim());
  return t || null;
};

const isChannel = (chip?: string | null): boolean => !!chip && chip.startsWith('#');
const isGenericMailbox = (chip?: string | null): boolean =>
  !!chip && /^(inbox|dm|linear)$/i.test(chip.trim());

/**
 * The line under the source name on the feed card: what the item belongs to,
 * in the source's own terms.
 */
export function headerSubline(row: FeedRow): string | null {
  switch (row.source) {
    case 'github':
      return clean(row.repo) ?? TYPE_PHRASE[row.type_tag];
    case 'gmail':
      return clean(row.sender_name) ?? clean(row.sender_handle);
    case 'slack':
      // A channel names itself; a DM names the person, never the word "DM".
      return isChannel(row.context_chip)
        ? clean(row.context_chip)
        : clean(row.sender_name) ?? clean(row.sender_handle);
    case 'linear':
      return TYPE_PHRASE[row.type_tag];
    case 'calendar':
      return clean(row.context_chip) ?? TYPE_PHRASE[row.type_tag];
    default:
      return clean(row.context_chip) ?? clean(row.sender_name);
  }
}

/**
 * The headline line: the subject, the issue, the PR, or the message.
 *
 * Mail with no subject leads with its message rather than the literal string
 * "(no subject)", which was drawing as large as everything else on screen.
 */
export function primaryLine(row: FeedRow): string {
  const title = clean(row.title);
  if (row.source === 'gmail') {
    const missing = !title || /^\(no subject\)$/i.test(title);
    if (missing) return oneLine(row.body) ?? clean(row.sender_name) ?? 'Message';
  }
  return title ?? 'Untitled';
}

/**
 * The subtitle on the feed card, which has a header. It carries only what the
 * header does not: the mail body under the subject, the issue description under
 * the issue. Slack returns nothing, because the message is already the title
 * and the sender is already the header.
 */
export function cardSubtitle(row: FeedRow): string | null {
  switch (row.source) {
    case 'slack':
      return null;
    case 'gmail': {
      const message = oneLine(row.body);
      return message && message !== primaryLine(row) ? message : null;
    }
    case 'linear':
      return oneLine(row.body);
    default:
      return clean(row.summary) ?? oneLine(row.body);
  }
}

/**
 * The subtitle in a list row, which has no header, so it carries the context
 * the card would have put in its header: the sender for a Slack message, the
 * repo for a GitHub item, the message for a mail.
 */
export function listSubtitle(row: FeedRow): string | null {
  switch (row.source) {
    case 'slack':
      return (
        clean(row.sender_name) ??
        clean(row.sender_handle) ??
        clean(row.context_chip)
      );
    case 'gmail':
      return oneLine(row.body) ?? clean(row.sender_name);
    case 'linear':
      return oneLine(row.body) ?? TYPE_PHRASE[row.type_tag];
    case 'github':
      return clean(row.repo) ?? clean(row.summary) ?? oneLine(row.body);
    default:
      return clean(row.summary) ?? oneLine(row.body);
  }
}

export function sourceName(row: FeedRow): string {
  return SOURCE_NAME[row.source];
}
