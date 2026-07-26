/**
 * What a card offers, and why it is never more than that.
 *
 * The previous matrix promised six actions the backend raised `UnknownAction`
 * on, so the app drew buttons that could only fail. Four of them now exist:
 * request changes and assign on GitHub, comment on Linear, and accept and
 * decline on Calendar. Two do not, and their buttons are therefore absent,
 * because a button that fails is worse than one that is not there.
 *
 * The table below is the single source of truth for which actions exist, and
 * the rail is built from it rather than from a wish. When an action lands in
 * the backend, flip its entry here and the button appears. Nothing else has to
 * change.
 */

import type { FeedRow, Source } from '../api/types';
import type { GlyphName } from '../components/Icon';

export interface Action {
  id: string;
  label: string;
  glyph: GlyphName;
}

const OPEN: Action = { id: 'open', label: 'Open', glyph: 'external' };
const REPLY: Action = { id: 'reply', label: 'Reply', glyph: 'reply' };
const COMMENT: Action = { id: 'comment', label: 'Comment', glyph: 'chat' };
const APPROVE: Action = { id: 'approve', label: 'Approve', glyph: 'check' };
const REQUEST_CHANGES: Action = {
  id: 'request_changes',
  label: 'Changes',
  glyph: 'changes',
};
const ASSIGN: Action = { id: 'assign_to_me', label: 'Assign', glyph: 'assign' };
const ACCEPT: Action = { id: 'accept', label: 'Accept', glyph: 'check' };
const DECLINE: Action = { id: 'decline', label: 'Decline', glyph: 'decline' };
const SNOOZE: Action = { id: 'snooze', label: 'Snooze', glyph: 'snooze' };
const MARK_READ: Action = { id: 'mark_read', label: 'Read', glyph: 'checks' };
const BRING_BACK: Action = { id: 'bring_back', label: 'Bring back', glyph: 'up' };

/**
 * Which source-and-action pairs the backend actually performs.
 *
 * `open`, `snooze` and `mark_read` work everywhere: the first never leaves the
 * client, the second touches nothing upstream, and the third falls back to
 * dismissing locally where the provider has no read state to move.
 */
const IMPLEMENTED: Record<Source, Set<string>> = {
  github: new Set(['comment', 'approve', 'request_changes', 'assign_to_me']),
  slack: new Set(['reply', 'mark_read']),
  linear: new Set(['comment']),
  calendar: new Set(['accept', 'decline']),
  // Replying to a Docs comment needs the Drive comments API, which is an
  // integration this build does not have. Until it exists, Docs opens and
  // nothing else: a button that fails is worse than one that is absent.
  google_docs: new Set<string>(),
  // Reply threads the response into the same conversation via
  // GMAIL_REPLY_TO_THREAD, and mark_read clears UNREAD. Both are wired in the
  // backend action service, so a mail item is a first-class reply target.
  gmail: new Set(['reply', 'mark_read']),
};

/**
 * Actions that need something typed before they can be sent: a reply body, a
 * comment, a reason for requesting changes. Pressing one on the rail opens the
 * sheet with the composer rather than firing an empty send that the backend
 * can only reject. Firing empty was the whole "the button does nothing, then
 * the card jumps to the next one" report: the empty send failed and the
 * optimistic removal advanced the deck.
 */
const COMPOSER = new Set(['reply', 'comment', 'request_changes']);

export function needsComposer(actionId: string): boolean {
  return COMPOSER.has(actionId);
}

// `mark_read` is deliberately absent here: it only makes sense where a source
// has a read state to move, which is Slack and Gmail, and it is in each of
// their tables. Offering "Read" on a Linear issue or a GitHub PR was offering
// to mark-as-read a thing that has no unread state.
const EVERYWHERE = new Set(['open', 'snooze', 'bring_back']);

export function isImplemented(source: Source, actionId: string): boolean {
  return EVERYWHERE.has(actionId) || IMPLEMENTED[source].has(actionId);
}

export interface RailAction extends Action {
  /**
   * The one filled glyph on the card. Only urgent and by-EOD earn it: nothing
   * that can wait deserves the strongest affordance, which is what stops the
   * emphasis appearing on every screen and meaning nothing on any of them.
   */
  primary: boolean;
}

/** The vertical rail, bottom right. At most three, and often two. */
export function railFor(row: FeedRow): RailAction[] {
  const wanted = candidates(row).filter((a) => isImplemented(row.source, a.id));
  const pressing = row.tier === 'urgent' || row.tier === 'today';
  return wanted.slice(0, 3).map((action, index) => ({
    ...action,
    primary: index === 0 && pressing,
  }));
}

function candidates(row: FeedRow): Action[] {
  // "Bring back" only makes sense for something the user actually snoozed:
  // promoting it out of the snooze is the one action unique to that state.
  if (row.status === 'snoozed') {
    return [OPEN, BRING_BACK, MARK_READ];
  }
  // A Later / noise item was never snoozed and is often read live with no
  // stored id to act on, so the only reliable action is opening it.
  if (row.tier === 'noise') {
    return [OPEN];
  }

  switch (row.source) {
    case 'github':
      if (row.type_tag === 'review' || row.type_tag === 'approve') {
        return [APPROVE, COMMENT, REQUEST_CHANGES];
      }
      if (row.type_tag === 'assigned') return [ASSIGN, COMMENT, SNOOZE];
      return [COMMENT, OPEN, SNOOZE];
    case 'slack':
      return [REPLY, MARK_READ, SNOOZE];
    case 'gmail':
      // Reply first and always, because answering the mail is the point of
      // the item and the reason it reached you rather than Later.
      return [REPLY, OPEN, SNOOZE];
    case 'calendar':
      return [ACCEPT, DECLINE, OPEN];
    case 'google_docs':
      return [REPLY, OPEN, SNOOZE];
    case 'linear':
      return [COMMENT, OPEN, SNOOZE];
    default:
      return [OPEN, SNOOZE, MARK_READ];
  }
}

/** Everything the rail did not have room for, as chips in the detail sheet. */
export function overflowFor(row: FeedRow): Action[] {
  const taken = new Set(railFor(row).map((a) => a.id));
  return [OPEN, SNOOZE, MARK_READ, DECLINE, REQUEST_CHANGES]
    .filter((action) => isImplemented(row.source, action.id))
    .filter((action) => !taken.has(action.id))
    .filter((action) => action.id !== 'decline' || row.source === 'calendar');
}

/** Whether the sheet shows a composer, which is a real send rather than a form. */
export function canCompose(row: FeedRow): boolean {
  return railFor(row).some((a) => a.id === 'reply' || a.id === 'comment');
}
