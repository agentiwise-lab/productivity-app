/**
 * Relative time, phrased the way a person would say it.
 *
 * Deadlines and ages read differently and must not be confused: "18m" means it
 * has been waiting eighteen minutes, "in 3h" means you have three hours left.
 * Showing one where the other belongs inverts the urgency the card is claiming.
 */

export function ago(iso: string | null, now: Date = new Date()): string {
  if (!iso) return '';
  const minutes = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return 'now';
  if (minutes < 60) return `${Math.floor(minutes)}m`;
  const hours = minutes / 60;
  if (hours < 24) return `${Math.floor(hours)}h`;
  const days = hours / 24;
  if (days < 7) return `${Math.floor(days)}d`;
  return `${Math.floor(days / 7)}w`;
}

export function deadlineLabel(iso: string | null, now: Date = new Date()): string | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - now.getTime();
  if (ms <= 0) return 'overdue';
  const hours = ms / 3600000;
  if (hours < 1) return `in ${Math.max(1, Math.floor(ms / 60000))}m`;
  if (hours < 24) return `in ${Math.floor(hours)}h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'tomorrow' : `in ${days}d`;
}

/**
 * A calendar row's time reads to its START, not its end: a meeting that has
 * begun says "now", one still ahead counts down to when it starts. Counting to
 * the end (the old behaviour) made a 30-minute meeting starting now read "in
 * 30m", as if it had not started.
 */
export function meetingLabel(
  startIso: string | null,
  endIso: string | null,
  now: Date = new Date(),
): string | null {
  if (!startIso) return null;
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : start;
  const t = now.getTime();
  if (t >= end) return 'ended';
  if (t >= start) return 'now';
  return deadlineLabel(startIso, now);
}

export function clockTime(date: Date | null): string {
  if (!date) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
