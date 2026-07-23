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

export function clockTime(date: Date | null): string {
  if (!date) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
