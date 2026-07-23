/**
 * Runtime configuration.
 *
 * The API base URL must be the Mac's LAN address, not localhost: the app runs
 * on a phone, where localhost is the phone. This is the single most common way
 * to lose an hour on an Expo Go setup, so it is stated here rather than left to
 * be rediscovered.
 *
 * Set it in mobile/.env as EXPO_PUBLIC_API_URL, or edit the fallback below.
 */

export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.1.10:8000';

/**
 * Dev mode sends X-User-Id and the backend must be running with AUTH_MODE=dev.
 * Supabase mode sends the session JWT. There is no silent fallback between
 * them: a trusted header reaching production is exactly what plan 6.5 forbids.
 */
export const AUTH_MODE: 'dev' | 'supabase' =
  (process.env.EXPO_PUBLIC_AUTH_MODE as 'dev' | 'supabase') ?? 'dev';

export const DEV_USER_ID = process.env.EXPO_PUBLIC_DEV_USER_ID ?? 'me';
