/**
 * The flow, as a small state machine.
 *
 * A four-screen linear path (email -> code -> password) plus a side door to
 * login does not need a navigation stack; it needs one `step` and the email and
 * code carried between the screens. The gate owns that state, calls the context
 * actions, and turns their typed errors into the line each screen shows.
 *
 * On a successful register or login the context flips to `signedIn` and this
 * whole tree unmounts, so there is no "success" screen to write: the app itself
 * is the success state.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '../../auth/AuthContext';
import { WelcomeEmailScreen } from './WelcomeEmailScreen';
import { OtpScreen } from './OtpScreen';
import { SetPasswordScreen } from './SetPasswordScreen';
import { LoginScreen } from './LoginScreen';

type Step = 'welcome' | 'otp' | 'password' | 'login';

const RESEND_COOLDOWN = 60;

export function AuthGate() {
  const auth = useAuth();
  const [step, setStep] = useState<Step>('welcome');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current);
  }, []);

  const startCooldown = useCallback(() => {
    setCooldown(RESEND_COOLDOWN);
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => {
      setCooldown((s) => {
        if (s <= 1 && timer.current) clearInterval(timer.current);
        return Math.max(0, s - 1);
      });
    }, 1000);
  }, []);

  const run = useCallback(async (fn: () => Promise<void>) => {
    setError(null);
    setLoading(true);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }, []);

  const goTo = (next: Step) => {
    setError(null);
    setStep(next);
  };

  switch (step) {
    case 'welcome':
      return (
        <WelcomeEmailScreen
          loading={loading}
          error={error}
          onGoToLogin={() => goTo('login')}
          onSubmit={(value) =>
            run(async () => {
              await auth.sendOtp(value);
              setEmail(value);
              startCooldown();
              goTo('otp');
            })
          }
        />
      );
    case 'otp':
      return (
        <OtpScreen
          email={email}
          loading={loading}
          error={error}
          cooldownSec={cooldown}
          onResend={() => run(async () => {
            await auth.sendOtp(email);
            startCooldown();
          })}
          onVerify={(value) =>
            run(async () => {
              await auth.verifyOtp(email, value);
              setCode(value);
              goTo('password');
            })
          }
        />
      );
    case 'password':
      return (
        <SetPasswordScreen
          email={email}
          loading={loading}
          error={error}
          onSubmit={(password) =>
            // Success flips the context to signedIn and unmounts this tree.
            run(() => auth.register(email, code, password))
          }
        />
      );
    case 'login':
      return (
        <LoginScreen
          loading={loading}
          error={error}
          onGoToSignup={() => goTo('welcome')}
          onSubmit={(value, password) => run(() => auth.login(value, password))}
        />
      );
  }
}
