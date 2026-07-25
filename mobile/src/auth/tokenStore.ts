/**
 * Where the session lives on the device.
 *
 * Access and refresh tokens go in the OS keychain via expo-secure-store, not in
 * AsyncStorage: AsyncStorage is plaintext on disk, and a refresh token is a
 * 30-day credential. The two are stored under separate keys so a rotation can
 * replace the access token without touching the refresh token, and clear() wipes
 * both on sign-out.
 */

import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'auth.access.v1';
const REFRESH_KEY = 'auth.refresh.v1';
const EMAIL_KEY = 'auth.email.v1';

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
  email: string;
}

export async function loadSession(): Promise<StoredSession | null> {
  const [accessToken, refreshToken, email] = await Promise.all([
    SecureStore.getItemAsync(ACCESS_KEY),
    SecureStore.getItemAsync(REFRESH_KEY),
    SecureStore.getItemAsync(EMAIL_KEY),
  ]);
  if (!accessToken || !refreshToken) return null;
  return { accessToken, refreshToken, email: email ?? '' };
}

export async function saveSession(session: StoredSession): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_KEY, session.accessToken),
    SecureStore.setItemAsync(REFRESH_KEY, session.refreshToken),
    SecureStore.setItemAsync(EMAIL_KEY, session.email),
  ]);
}

/** Replace just the token pair after a refresh, keeping the stored email. */
export async function saveTokens(accessToken: string, refreshToken: string): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_KEY, accessToken),
    SecureStore.setItemAsync(REFRESH_KEY, refreshToken),
  ]);
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_KEY),
    SecureStore.deleteItemAsync(REFRESH_KEY),
    SecureStore.deleteItemAsync(EMAIL_KEY),
  ]);
}
