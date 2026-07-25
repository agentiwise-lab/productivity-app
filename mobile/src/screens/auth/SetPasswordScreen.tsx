/**
 * Step three: choose a password. The confirm field catches a typo before it
 * becomes a lockout, and the minimum length matches the backend's so the button
 * does not offer a submit the server will reject.
 */

import React, { useState } from 'react';

import { BigButton } from '../../components/ui';
import { AuthShell, Field } from './AuthKit';

const MIN = 8;

export function SetPasswordScreen({
  email,
  onSubmit,
  loading,
  error,
}: {
  email: string;
  onSubmit: (password: string) => void;
  loading: boolean;
  error?: string | null;
}) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');

  const tooShort = password.length < MIN;
  const mismatch = confirm.length > 0 && password !== confirm;
  const canSubmit = !tooShort && !mismatch && password === confirm;
  const submit = () => {
    if (canSubmit) onSubmit(password);
  };

  const localError =
    mismatch
      ? "Passwords don't match."
      : password.length > 0 && tooShort
        ? `At least ${MIN} characters.`
        : null;

  return (
    <AuthShell
      title="Set a password"
      subtitle={`This is how you'll sign in as ${email}.`}
      error={error ?? localError}
    >
      <Field
        value={password}
        onChangeText={setPassword}
        placeholder="New password"
        secureTextEntry
        autoFocus
      />
      <Field
        value={confirm}
        onChangeText={setConfirm}
        placeholder="Confirm password"
        secureTextEntry
        onSubmitEditing={submit}
      />
      <BigButton
        label={loading ? 'Creating account…' : 'Create account'}
        variant="primary"
        onPress={submit}
        disabled={loading || !canSubmit}
      />
    </AuthShell>
  );
}
