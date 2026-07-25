/**
 * The unauthenticated calls: how a user gets a token in the first place.
 *
 * Kept apart from ApiClient because none of these carry a Bearer header, and
 * ApiClient's whole job is to attach one and to refresh it. These are plain
 * POSTs whose only shared behaviour is turning the backend's typed error detail
 * into a message the screens can show.
 */

import { API_URL } from '../config';

export type Purpose = 'signup' | 'reset';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export class AuthApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
  }
}

async function post<T>(path: string, body: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new AuthApiError("Can't reach the server. Check your connection.", null);
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new AuthApiError(messageOf(data), response.status);
  }
  return data as T;
}

/** FastAPI puts our message in `detail`; a 422 puts field errors in a list. */
function messageOf(data: unknown): string {
  const detail = (data as { detail?: unknown })?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    return first?.msg ?? 'Something went wrong.';
  }
  return 'Something went wrong.';
}

export const authApi = {
  sendOtp: (email: string, purpose: Purpose = 'signup') =>
    post<{ message: string }>('/auth/otp/send', { email, purpose }),

  verifyOtp: (email: string, code: string, purpose: Purpose = 'signup') =>
    post<{ message: string }>('/auth/otp/verify', { email, code, purpose }),

  register: (email: string, code: string, password: string) =>
    post<TokenPair>('/auth/register', { email, code, password }),

  login: (email: string, password: string) =>
    post<TokenPair>('/auth/login', { email, password }),

  refresh: (refresh_token: string) =>
    post<TokenPair>('/auth/refresh', { refresh_token }),

  logout: (refresh_token: string) => post<void>('/auth/logout', { refresh_token }),
};
