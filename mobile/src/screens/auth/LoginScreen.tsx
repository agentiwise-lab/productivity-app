/**
 * The returning-user path: email and password, straight to a session. A link
 * back to signup for anyone who landed here by mistake.
 */

import React, { useState } from 'react';
import { View } from 'react-native';

import { space } from '../../theme';
import { BigButton, T } from '../../components/ui';
import { AuthShell, Field, LinkText } from './AuthKit';

export function LoginScreen({
  onSubmit,
  onGoToSignup,
  loading,
  error,
}: {
  onSubmit: (email: string, password: string) => void;
  onGoToSignup: () => void;
  loading: boolean;
  error?: string | null;
}) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const canSubmit = email.trim().length > 0 && password.length > 0;
  const submit = () => {
    if (canSubmit) onSubmit(email.trim(), password);
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your account."
      error={error}
      footer={
        <View style={{ flexDirection: 'row', gap: space.xs }}>
          <T role="secondary" tone="mid">
            New here?
          </T>
          <LinkText label="Create an account" onPress={onGoToSignup} />
        </View>
      }
    >
      <Field
        value={email}
        onChangeText={setEmail}
        placeholder="you@example.com"
        keyboardType="email-address"
        autoFocus
      />
      <Field
        value={password}
        onChangeText={setPassword}
        placeholder="Password"
        secureTextEntry
        onSubmitEditing={submit}
      />
      <BigButton
        label={loading ? 'Signing in…' : 'Sign in'}
        variant="primary"
        onPress={submit}
        disabled={loading || !canSubmit}
      />
    </AuthShell>
  );
}
