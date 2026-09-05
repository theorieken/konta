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
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { errorMessage } from '@base/api/client';
import { AuthPage } from '@base/components/auth-page';
import { useConfirmPasswordResetMutation } from '@base/store/api';
import { signedIn } from '@base/store/authSlice';
import { useAppDispatch } from '@base/store/hooks';

export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [leaving, setLeaving] = useState(false);
  const [confirmReset, { isLoading }] = useConfirmPasswordResetMutation();
  const busy = isLoading || leaving;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    if (password !== confirmation) {
      setError('Die Passwörter stimmen nicht überein.');
      return;
    }
    try {
      const result = await confirmReset({ token, new_password: password }).unwrap();
      setLeaving(true);
      dispatch(signedIn(result));
      router.replace('/dashboard');
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
          <Stack component="form" onSubmit={submit} spacing={2} sx={{ minHeight: 330 }}>
            <Stack spacing={0.5}>
              <Typography variant="h1">Neues Passwort</Typography>
              <Typography variant="body2" color="text.secondary">
                Dieser Link kann nur einmal verwendet werden.
              </Typography>
            </Stack>

            {error ? <Alert severity="error">{error}</Alert> : null}

            <TextField
              label="Neues Passwort"
              type="password"
              autoComplete="new-password"
              autoFocus
              required
              disabled={busy}
              value={password}
              helperText="Mindestens 8 Zeichen"
              onChange={(event) => setPassword(event.target.value)}
            />
            <TextField
              label="Passwort wiederholen"
              type="password"
              autoComplete="new-password"
              required
              disabled={busy}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={busy || password.length < 8 || confirmation.length < 8}
              startIcon={busy ? <CircularProgress color="inherit" size={16} /> : undefined}
            >
              {busy ? 'Passwort wird gespeichert …' : 'Passwort speichern'}
            </Button>

          </Stack>
        </CardContent>
      </Card>
    </AuthPage>
  );
}
