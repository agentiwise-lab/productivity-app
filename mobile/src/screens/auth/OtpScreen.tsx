/**
 * Step two: the six-digit code. Resend is disabled until the cooldown the
 * backend enforces has elapsed, so the button never invites a request that will
 * come back 429.
 */

import React, { useState } from 'react';
import { View } from 'react-native';

import { space } from '../../theme';
import { BigButton, T } from '../../components/ui';
import { AuthShell, Field, LinkText } from './AuthKit';

export function OtpScreen({
  email,
  onVerify,
  onResend,
  cooldownSec,
  loading,
  error,
}: {
  email: string;
  onVerify: (code: string) => void;
  onResend: () => void;
  cooldownSec: number;
  loading: boolean;
  error?: string | null;
}) {
  const [code, setCode] = useState('');
  const submit = () => {
    if (code.trim().length === 6) onVerify(code.trim());
  };

  return (
    <AuthShell
      title="Enter the code"
      subtitle={`We sent a 6-digit code to ${email}.`}
      error={error}
      footer={
        cooldownSec > 0 ? (
          <T role="secondary" tone="mid">
            Resend in {cooldownSec}s
          </T>
        ) : (
          <View style={{ flexDirection: 'row', gap: space.xs }}>
            <T role="secondary" tone="mid">
              Didn't get it?
            </T>
            <LinkText label="Resend" onPress={onResend} />
          </View>
        )
      }
    >
      <Field
        value={code}
        onChangeText={(next) => setCode(next.replace(/[^0-9]/g, ''))}
        placeholder="123456"
        keyboardType="number-pad"
        autoFocus
        maxLength={6}
        onSubmitEditing={submit}
      />
      <View style={{ height: space.lg }} />
      <BigButton
        label={loading ? 'Verifying…' : 'Verify'}
        variant="primary"
        onPress={submit}
        disabled={loading || code.trim().length !== 6}
        style={{ height: 48 }}
      />
    </AuthShell>
  );
}
