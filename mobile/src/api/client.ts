/**
 * The one place that talks to the backend.
 *
 * Two behaviours here are product requirements rather than conveniences, both
 * from plan 6.4. Reads fall back to the last cached feed when the network is
 * gone, because an empty screen reads as "nothing needs you" when it means "we
 * could not ask". And every failure is typed, so the UI can say which of those
 * two things happened instead of showing the same blank state for both.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import type {
  FeedRow,
  MeetingOut,
  RefreshResult,
  SourceDashboard,
  SourceInfo,
} from './types';

const CACHE_KEY = 'feed.cache.v1';
const CACHE_AT_KEY = 'feed.cache.at.v1';
const TIMEOUT_MS = 12000;
/**
 * Source dashboards count every conversation live at the provider, so they are
 * slower than anything else by design. At the shared 12s budget Slack's board
 * was aborted mid-flight and the screen bounced back to Sources, which read as
 * "this page is broken" rather than "this page is slow".
 */
const DASHBOARD_TIMEOUT_MS = 60000;
/**
 * A refresh pulls every source, and Gmail alone pages through every unread
 * message in the window: about 40s on a mailbox with a few hundred. At the
 * shared budget the client aborted its own refresh every time, so the feed only
 * ever updated when something else happened to write to it.
 */
const REFRESH_TIMEOUT_MS = 180000;

export type FeedResult = {
  rows: FeedRow[];
  /** True when these came from disk because the request failed. */
  stale: boolean;
  /** When the rows were actually fetched. Shown as "last updated HH:MM". */
  fetchedAt: Date | null;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly kind: 'network' | 'auth' | 'server',
  ) {
    super(message);
  }
}

export class ApiClient {
  constructor(
    private baseUrl: string,
    private auth: () => Record<string, string>,
  ) {}

  setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/$/, '');
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    timeoutMs: number = TIMEOUT_MS,
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...this.auth(),
          ...(init.headers ?? {}),
        },
      });
      if (response.status === 401) {
        throw new ApiError('Your session expired. Sign in again.', 401, 'auth');
      }
      if (!response.ok) {
        throw new ApiError(`Request failed (${response.status})`, response.status, 'server');
      }
      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError("Can't reach the backend.", null, 'network');
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Never throws on a network failure: it degrades to the cache. It still
   * throws on auth, because a stale feed behind an expired session is worse
   * than being told to sign in.
   */
  async getFeed(): Promise<FeedResult> {
    try {
      const rows = await this.request<FeedRow[]>('/feed');
      const now = new Date();
      await AsyncStorage.multiSet([
        [CACHE_KEY, JSON.stringify(rows)],
        [CACHE_AT_KEY, now.toISOString()],
      ]);
      return { rows, stale: false, fetchedAt: now };
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'auth') throw error;
      const cached = await this.readCache();
      if (cached === null) throw error;
      return cached;
    }
  }

  private async readCache(): Promise<FeedResult | null> {
    const [[, raw], [, at]] = await AsyncStorage.multiGet([CACHE_KEY, CACHE_AT_KEY]);
    if (!raw) return null;
    try {
      return {
        rows: JSON.parse(raw) as FeedRow[],
        stale: true,
        fetchedAt: at ? new Date(at) : null,
      };
    } catch {
      return null;
    }
  }

  /** Every supported source with its live status. Never inferred from feed
   *  rows: that could not tell a quiet integration from an absent one. */
  connections(): Promise<SourceInfo[]> {
    return this.request<SourceInfo[]>('/connections');
  }

  /** Read live on every open. A cached schedule eventually becomes a lie. */
  day(): Promise<MeetingOut[]> {
    return this.request<MeetingOut[]>('/day');
  }

  sourceDashboard(provider: string): Promise<SourceDashboard> {
    return this.request<SourceDashboard>(
      `/sources/${provider}`,
      {},
      DASHBOARD_TIMEOUT_MS,
    );
  }

  connectUrl(provider: string): Promise<{ url: string }> {
    return this.request<{ url: string }>(`/connections/${provider}/link`, {
      method: 'POST',
    });
  }

  /** The Later stream is read with XHR, so the caller needs the URL and the
   *  auth headers rather than a parsed response. */
  laterStream(limit = 200): { url: string; headers: Record<string, string> } {
    return { url: `${this.baseUrl}/later?limit=${limit}`, headers: this.auth() };
  }

  refresh(): Promise<RefreshResult> {
    return this.request<RefreshResult>(
      '/feed/refresh',
      { method: 'POST' },
      REFRESH_TIMEOUT_MS,
    );
  }

  act(itemId: string, body: string) {
    return this.request<FeedRow>(`/feed/${itemId}/actions`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    });
  }

  snooze(itemId: string, until: Date) {
    return this.request<FeedRow>(`/feed/${itemId}/snooze`, {
      method: 'POST',
      body: JSON.stringify({ until: until.toISOString() }),
    });
  }

  dismiss(itemId: string) {
    return this.request<FeedRow>(`/feed/${itemId}/dismiss`, { method: 'POST' });
  }
}
