/**
 * Where the session lives on the device.
 *
 * Access and refresh tokens go in the OS keychain via expo-secure-store, not in
 * AsyncStorage: AsyncStorage is plaintext on disk, and a refresh token is a
 * 30-day credential. The two are stored under separate keys so a rotation can
 * replace the access token without touching the refresh token, and clear() wipes
 * both on sign-out.
 *
 * expo-secure-store is native-only (iOS Keychain / Android Keystore) and has no
 * web implementation. On web — a dev/preview surface, not a shipped target — we
 * fall back to localStorage. On device the tokens still live in the keychain.
 */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const ACCESS_KEY = 'auth.access.v1';
const REFRESH_KEY = 'auth.refresh.v1';
const EMAIL_KEY = 'auth.email.v1';

const isWeb = Platform.OS === 'web';

async function getItem(key: string): Promise<string | null> {
  if (isWeb) return globalThis.localStorage?.getItem(key) ?? null;
  return SecureStore.getItemAsync(key);
}

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function deleteItem(key: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
  email: string;
}

export async function loadSession(): Promise<StoredSession | null> {
  const [accessToken, refreshToken, email] = await Promise.all([
    getItem(ACCESS_KEY),
    getItem(REFRESH_KEY),
    getItem(EMAIL_KEY),
  ]);
  if (!accessToken || !refreshToken) return null;
  return { accessToken, refreshToken, email: email ?? '' };
}

export async function saveSession(session: StoredSession): Promise<void> {
  await Promise.all([
    setItem(ACCESS_KEY, session.accessToken),
    setItem(REFRESH_KEY, session.refreshToken),
    setItem(EMAIL_KEY, session.email),
  ]);
}

/** Replace just the token pair after a refresh, keeping the stored email. */
export async function saveTokens(accessToken: string, refreshToken: string): Promise<void> {
  await Promise.all([
    setItem(ACCESS_KEY, accessToken),
    setItem(REFRESH_KEY, refreshToken),
  ]);
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    deleteItem(ACCESS_KEY),
    deleteItem(REFRESH_KEY),
    deleteItem(EMAIL_KEY),
  ]);
}
