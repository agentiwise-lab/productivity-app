/**
 * The session, and the four things a signed-out user can do to end it.
 *
 * Tokens live in a ref, not in state: ApiClient reads the current access token
 * on every request through a getter, and a request in flight must see the token
 * a refresh just rotated in, not the one React last rendered. State holds only
 * what the UI switches on: whether we are loading, signed out, or in.
 *
 * Refresh is single-flight. A burst of 401s (every tab firing at once when a
 * token expires) must trigger one refresh, not one per request, or they race to
 * rotate the same token and all but the first look like theft.
 *
 * Dev mode is a deliberate bypass: the gate reports "signed in" immediately and
 * ApiClient keeps sending X-User-Id, so local work never sees a login screen.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

import { AUTH_MODE, DEV_USER_ID } from '../config';
import type { ApiClient } from '../api/client';
import { authApi, type TokenPair } from './authApi';
import { clearSession, loadSession, saveSession, saveTokens } from './tokenStore';

type Status = 'loading' | 'signedOut' | 'signedIn';

interface AuthValue {
  status: Status;
  email: string;
  /** True for one read after a fresh signup (register), never after login or a
   *  restored session. The name prompt keys off this so it appears once at
   *  signup rather than on every launch of a nameless account. */
  justSignedUp: boolean;
  acknowledgeSignup: () => void;
  sendOtp: (email: string) => Promise<void>;
  verifyOtp: (email: string, code: string) => Promise<void>;
  register: (email: string, code: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth used outside AuthProvider');
  return value;
}

export function AuthProvider({
  api,
  children,
}: {
  api: ApiClient;
  children: React.ReactNode;
}) {
  const [status, setStatus] = useState<Status>('loading');
  const [email, setEmail] = useState('');
  const [justSignedUp, setJustSignedUp] = useState(false);
  const tokens = useRef<{ access: string; refresh: string } | null>(null);
  const refreshing = useRef<Promise<boolean> | null>(null);

  const doRefresh = useCallback(async (): Promise<boolean> => {
    if (!tokens.current) return false;
    if (refreshing.current) return refreshing.current;
    refreshing.current = (async () => {
      try {
        const pair = await authApi.refresh(tokens.current!.refresh);
        tokens.current = { access: pair.access_token, refresh: pair.refresh_token };
        await saveTokens(pair.access_token, pair.refresh_token);
        return true;
      } catch {
        tokens.current = null;
        await clearSession();
        setStatus('signedOut');
        return false;
      } finally {
        refreshing.current = null;
      }
    })();
    return refreshing.current;
  }, []);

  // Wire ApiClient to read the live token and to refresh on a 401. In dev mode
  // we leave its X-User-Id header untouched.
  useEffect(() => {
    if (AUTH_MODE !== 'own') return;
    api.setAuth((): Record<string, string> =>
      tokens.current ? { Authorization: `Bearer ${tokens.current.access}` } : {},
    );
    api.setOnAuthError(doRefresh);
  }, [api, doRefresh]);

  // Restore a session from the keychain on launch.
  useEffect(() => {
    if (AUTH_MODE === 'dev') {
      setEmail(DEV_USER_ID);
      setStatus('signedIn');
      return;
    }
    (async () => {
      const session = await loadSession();
      if (session) {
        tokens.current = { access: session.accessToken, refresh: session.refreshToken };
        setEmail(session.email);
        setStatus('signedIn');
      } else {
        setStatus('signedOut');
      }
    })();
  }, []);

  const enter = useCallback(async (pair: TokenPair, emailValue: string) => {
    tokens.current = { access: pair.access_token, refresh: pair.refresh_token };
    await saveSession({
      accessToken: pair.access_token,
      refreshToken: pair.refresh_token,
      email: emailValue,
    });
    setEmail(emailValue);
    setStatus('signedIn');
  }, []);

  const sendOtp = useCallback((e: string) => authApi.sendOtp(e).then(() => undefined), []);
  const verifyOtp = useCallback(
    (e: string, code: string) => authApi.verifyOtp(e, code).then(() => undefined),
    [],
  );
  const register = useCallback(
    async (e: string, code: string, password: string) => {
      await enter(await authApi.register(e, code, password), e);
      // Signup is the one moment we prompt for a name; login and session-restore
      // never set this.
      setJustSignedUp(true);
    },
    [enter],
  );
  const acknowledgeSignup = useCallback(() => setJustSignedUp(false), []);
  const login = useCallback(
    async (e: string, password: string) => {
      await enter(await authApi.login(e, password), e);
    },
    [enter],
  );
  const signOut = useCallback(async () => {
    const refresh = tokens.current?.refresh;
    tokens.current = null;
    setStatus('signedOut');
    setEmail('');
    await clearSession();
    if (refresh) authApi.logout(refresh).catch(() => undefined); // best effort
  }, []);

  return (
    <AuthContext.Provider
      value={{
        status,
        email,
        justSignedUp,
        acknowledgeSignup,
        sendOtp,
        verifyOtp,
        register,
        login,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
