/**
 * Getting permission, getting a token, and telling the backend where to send.
 *
 * Everything that talks to `expo-notifications` lives here, so the rest of the
 * app deals in "is it on" and never in permission states.
 *
 * Three things in here are less obvious than they look:
 *
 * 1. **This runs on every launch, not once at signup.** An Expo token rotates
 *    on reinstall, on some restores, and whenever FCM or APNs re-registers the
 *    app. Registering once would leave a user silently unreachable months later
 *    with nothing in the UI to explain it. The backend write is an upsert, so
 *    calling it every launch is free.
 *
 * 2. **It never asks twice.** `requestPermissionsAsync` only fires when the OS
 *    says the answer is still undetermined. Asking again after a denial does
 *    nothing at all on iOS: the prompt has been spent, and the call returns the
 *    existing denial without showing anything.
 *
 * 3. **The Android channel is created before any notification arrives.** With
 *    no channel, Android files ours under the user-facing "Default" bucket and
 *    delivers them silently in the drawer rather than as a heads-up.
 */

import { Platform } from 'react-native';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';

import type { ApiClient } from '../api/client';

/**
 * The one channel. `MAX` importance is what makes an urgent item peek over
 * whatever is on screen instead of landing silently in the drawer; the message
 * itself also carries `priority: high`, and Android needs both.
 *
 * Its importance belongs to the user the moment it is created: Android will not
 * let an app raise it later, which is the right way round and worth knowing
 * before changing this value.
 */
export const CHANNEL_ID = 'urgent';

export type PushPermission = 'granted' | 'denied' | 'undetermined';

/** What the caller needs to know: whether we are reachable, and how to stop. */
export interface PushRegistration {
  permission: PushPermission;
  token: string | null;
}

/**
 * The EAS project id, which `getExpoPushTokenAsync` requires and throws
 * without.
 *
 * Both spellings are checked because `expoConfig` is null in some production
 * build contexts, and a crash inside the one function called on every launch is
 * not a thing to discover on somebody's phone.
 */
function projectId(): string | undefined {
  const fromConfig = (Constants as any)?.expoConfig?.extra?.eas?.projectId;
  const fromEas = (Constants as any)?.easConfig?.projectId;
  return fromConfig ?? fromEas;
}

async function ensureChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync(CHANNEL_ID, {
    name: 'Urgent',
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 250, 250, 250],
    lockscreenVisibility:
      Notifications.AndroidNotificationVisibility.PUBLIC,
  });
}

/** What the OS currently thinks, without asking the user anything. */
export async function currentPermission(): Promise<PushPermission> {
  if (!Device.isDevice) return 'denied';
  try {
    const { status } = await Notifications.getPermissionsAsync();
    return status as PushPermission;
  } catch {
    return 'undetermined';
  }
}

/**
 * Ask the OS, but only if it has not already answered.
 *
 * Call this from the priming card's affirmative button and from nowhere else.
 * The OS prompt is a one-shot resource on iOS and this is the only place it is
 * allowed to be spent.
 */
export async function requestPermission(): Promise<PushPermission> {
  if (!Device.isDevice) return 'denied';
  const existing = await currentPermission();
  if (existing !== 'undetermined') return existing;
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    return status as PushPermission;
  } catch {
    return 'denied';
  }
}

/**
 * Register this device with the backend, if the OS allows it.
 *
 * Never throws and never prompts. A phone that cannot be reached is a quiet
 * degradation, not a broken launch, so every failure path returns a token of
 * null and lets the caller carry on.
 *
 * Returns the token so the caller can hold onto it: unregistering at sign-out
 * needs one in hand, and re-deriving it then is both slower and able to fail
 * at the worst moment.
 */
export async function registerForPush(
  api: ApiClient,
): Promise<PushRegistration> {
  // A simulator has no push service behind it, so a token here would be a lie.
  if (!Device.isDevice) return { permission: 'denied', token: null };

  const permission = await currentPermission();
  if (permission !== 'granted') return { permission, token: null };

  try {
    await ensureChannel();
    const id = projectId();
    if (!id) return { permission, token: null };

    const { data: token } = await Notifications.getExpoPushTokenAsync({
      projectId: id,
    });
    await api.registerDevice(
      token,
      Platform.OS === 'ios' ? 'ios' : 'android',
    );
    return { permission, token };
  } catch {
    // A failed registration must not block the app. The next launch retries,
    // and the setting still reads as on because the user's preference and the
    // device's reachability are different facts.
    return { permission, token: null };
  }
}
