'use client';

import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Link from 'next/link';
import { useState } from 'react';

import { errorMessage } from '@base/api/client';
import { AuthPage } from '@base/components/auth-page';
import { useRequestPasswordResetMutation } from '@base/store/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [requestReset, { isLoading }] = useRequestPasswordResetMutation();

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const result = await requestReset({ email }).unwrap();
      setMessage(result.detail);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <AuthPage
      footer={(
        <Button component={Link} href="/login" size="small" color="inherit">
          Zurück zur Anmeldung
        </Button>
      )}
    >
      <Card>
        <CardContent sx={{ p: { xs: 3, sm: 3.5 } }}>
          <Stack component="form" onSubmit={submit} spacing={2} sx={{ minHeight: 300 }}>
            <Stack spacing={0.5}>
              <Typography variant="h1">Passwort zurücksetzen</Typography>
              <Typography variant="body2" color="text.secondary">
                Wir senden dir einen einmal verwendbaren Link.
              </Typography>
            </Stack>

            {message ? <Alert severity="success">{message}</Alert> : null}
            {error ? <Alert severity="error">{error}</Alert> : null}

            {!message ? (
              <>
                <TextField
                  label="E-Mail"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  required
                  disabled={isLoading}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={isLoading}
                  startIcon={isLoading ? <CircularProgress color="inherit" size={16} /> : undefined}
                >
                  {isLoading ? 'E-Mail wird versendet …' : 'Reset-Link senden'}
                </Button>
              </>
            ) : null}

          </Stack>
        </CardContent>
      </Card>
    </AuthPage>
  );
}
