/**
 * The action matrix from plan 6.2, in one place.
 *
 * Two actions reach the card and the rest live in the detail sheet, because a
 * card offering five choices is a card that gets read instead of acted on. Which
 * two depends on the source and the type tag: "Approve" on a review request and
 * "Reply" on a Slack DM are the same slot.
 *
 * Merge is deliberately absent. Reacting is deferred past the MVP.
 */

import type { FeedRow } from '../api/types';

export interface Action {
  id: string;
  label: string;
}

const OPEN: Action = { id: 'open', label: 'Open' };
const REPLY: Action = { id: 'reply', label: 'Reply' };
const COMMENT: Action = { id: 'comment', label: 'Comment' };
const APPROVE: Action = { id: 'approve', label: 'Approve' };
const SNOOZE: Action = { id: 'snooze', label: 'Snooze' };
const MARK_READ: Action = { id: 'mark_read', label: 'Mark read' };
const ACCEPT: Action = { id: 'accept', label: 'Accept' };

/** [primary, secondary] for the card. */
export function actionsFor(row: FeedRow): [Action, Action] {
  switch (row.source) {
    case 'github':
      if (row.type_tag === 'review' || row.type_tag === 'approve') {
        return [APPROVE, COMMENT];
      }
      return [COMMENT, SNOOZE];
    case 'slack':
      return [REPLY, MARK_READ];
    case 'google_docs':
      return [REPLY, OPEN];
    case 'calendar':
      return [ACCEPT, OPEN];
    case 'linear':
      return [COMMENT, OPEN];
    default:
      return [OPEN, SNOOZE];
  }
}

/** Everything else, for the detail sheet. */
export function overflowFor(row: FeedRow): Action[] {
  const [primary, secondary] = actionsFor(row);
  const taken = new Set([primary.id, secondary.id]);
  const rest: Action[] = [OPEN, SNOOZE, MARK_READ];
  if (row.source === 'github' && row.type_tag === 'review') {
    rest.unshift({ id: 'request_changes', label: 'Request changes' });
  }
  if (row.source === 'github' && row.type_tag === 'assigned') {
    rest.unshift({ id: 'assign_to_me', label: 'Assign to me' });
  }
  if (row.source === 'calendar') {
    rest.unshift({ id: 'decline', label: 'Decline' });
  }
  return rest.filter((action) => !taken.has(action.id));
}
