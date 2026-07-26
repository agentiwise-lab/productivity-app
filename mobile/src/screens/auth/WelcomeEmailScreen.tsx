/**
 * Step one of signup: the email. One field, one button, and a way to the login
 * screen for people who already have an account.
 */

import React, { useState } from 'react';
import { View } from 'react-native';

import { space } from '../../theme';
import { BigButton, T } from '../../components/ui';
import { AuthShell, Field, LinkText } from './AuthKit';

export function WelcomeEmailScreen({
  onSubmit,
  onGoToLogin,
  loading,
  error,
}: {
  onSubmit: (email: string) => void;
  onGoToLogin: () => void;
  loading: boolean;
  error?: string | null;
}) {
  const [email, setEmail] = useState('');
  const submit = () => {
    if (email.trim()) onSubmit(email.trim());
  };

  return (
    <AuthShell
      title="Get started"
      subtitle="Enter your email and we'll send you a code."
      error={error}
      footer={
        <View style={{ flexDirection: 'row', gap: space.xs }}>
          <T role="secondary" tone="mid">
            Already have an account?
          </T>
          <LinkText label="Sign in" onPress={onGoToLogin} />
        </View>
      }
    >
      <Field
        value={email}
        onChangeText={setEmail}
        placeholder="you@example.com"
        keyboardType="email-address"
        autoFocus
        onSubmitEditing={submit}
      />
      <View style={{ height: space.lg }} />
      <BigButton
        label={loading ? 'Sending…' : 'Send code'}
        variant="primary"
        onPress={submit}
        disabled={loading || !email.trim()}
        style={{ height: 48 }}
      />
    </AuthShell>
  );
}
