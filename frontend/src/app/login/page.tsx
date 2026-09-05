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
import { useEffect, useState } from 'react';

import { APP_NAME, errorMessage } from '@base/api/client';
import { AuthPage } from '@base/components/auth-page';
import { useAuthStatusQuery, useLoginMutation } from '@base/store/api';
import { signedIn } from '@base/store/authSlice';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';

export default function LoginPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const ready = useAppSelector((state) => state.auth.ready);

  const { data: status } = useAuthStatusQuery(undefined, { skip: !ready });
  const [login, { isLoading }] = useLoginMutation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [leaving, setLeaving] = useState(false);
  const busy = isLoading || leaving;

  useEffect(() => {
    if (!status) return;
    if (status.needs_onboarding) router.replace('/onboarding');
    else if (status.authenticated) router.replace('/dashboard');
  }, [router, status]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const result = await login({ email, password }).unwrap();
      setLeaving(true);
      dispatch(signedIn(result));
      router.replace('/dashboard');
    } catch (caught) {
      setLeaving(false);
      setError(errorMessage(caught));
    }
  };

  return (
    <AuthPage
      maxWidth={360}
      footer={(
        <Button component={Link} href="/forgot-password" size="small" color="inherit">
          Passwort vergessen?
        </Button>
      )}
    >
      <Card>
        <CardContent sx={{ p: { xs: 3, sm: 3.5 } }}>
          <Stack component="form" onSubmit={submit} spacing={2} sx={{ minHeight: 330 }}>
            <Stack spacing={0.5}>
              <Typography variant="h1">{APP_NAME}</Typography>
              <Typography variant="body2" color="text.secondary">
                Melde dich an, um weiterzumachen.
              </Typography>
            </Stack>

            {error ? <Alert severity="error">{error}</Alert> : null}

            <TextField
              label="E-Mail"
              type="email"
              autoComplete="email"
              autoFocus
              required
              disabled={busy}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <TextField
              label="Passwort"
              type="password"
              autoComplete="current-password"
              required
              disabled={busy}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />

            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={busy}
              startIcon={busy ? <CircularProgress color="inherit" size={16} /> : undefined}
              aria-busy={busy}
            >
              {busy ? 'Anmeldung läuft …' : 'Anmelden'}
            </Button>

          </Stack>
        </CardContent>
      </Card>
    </AuthPage>
  );
}
