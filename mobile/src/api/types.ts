/**
 * The wire contract, mirroring backend/models/feed.py FeedRow.
 *
 * `tier` and `priorityScore` exist only here and on the wire. They are computed
 * per request against the current clock and are deliberately absent from the
 * database, so nothing in the app should ever try to cache or persist them.
 */

export type Tier = 'urgent' | 'today' | 'can_wait' | 'noise';

export type TypeTag =
  | 'review'
  | 'approve'
  | 'reply'
  | 'assigned'
  | 'comment'
  | 'decide'
  | 'rsvp'
  | 'alert'
  | 'fyi';

export type Source = 'github' | 'slack' | 'google_docs' | 'linear' | 'calendar' | 'gmail';

export type FeedStatus = 'unread' | 'acted' | 'dismissed' | 'snoozed';

export interface FeedRow {
  id: string;
  user_id: string;
  source: Source;
  source_ref: string;

  tier: Tier;
  priority_score: number;
  rule_tier: Tier;
  llm_tier: Tier | null;
  tier_source: 'rule' | 'llm';
  type_tag: TypeTag;
  needs_llm: boolean;

  title: string;
  /** The AI one-liner. Null while classification is still pending. */
  summary: string | null;
  /** Why this tier, shown in the detail sheet. */
  reason: string | null;
  url: string;
  repo: string;
  context_chip: string | null;
  sender_name: string | null;
  sender_handle: string | null;

  deadline: string | null;
  occurred_at: string | null;
  created_at: string | null;
  snoozed_until: string | null;
  handled_at: string | null;

  is_blocking: boolean;
  status: FeedStatus;
  /** The full readable content: an email body, a Slack message, a description. */
  body: string | null;
}

export interface RefreshResult {
  ingested: number;
  classified: number;
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'expired' | 'error';

export interface SourceInfo {
  source: Source;
  label: string;
  status: ConnectionStatus;
  count: number;
  urgent: number;
  connected_account_id: string | null;
}

export interface MeetingOut {
  title: string;
  start: string;
  end: string;
  conference_url: string | null;
}

export interface StatLine {
  label: string;
  value: number;
  detail: string | null;
}

export interface SourceDashboard {
  source: Source;
  label: string;
  headline: StatLine[];
  breakdown: StatLine[];
  unavailable: string[];
}
