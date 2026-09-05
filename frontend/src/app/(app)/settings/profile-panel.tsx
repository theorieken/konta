'use client';

import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import { useState } from 'react';

import { errorMessage } from '@base/api/client';
import { Section } from '@base/components/section';
import { useChangePasswordMutation, useMeQuery, useUpdateMeMutation } from '@base/store/api';
import { setToken } from '@base/api/client';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';

export function ProfilePanel() {
  const dispatch = useAppDispatch();
  const { data: me } = useMeQuery();
  const [updateMe, { isLoading: saving }] = useUpdateMeMutation();
  const [changePassword, { isLoading: changing }] = useChangePasswordMutation();

  const [name, setName] = useState('');
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [error, setError] = useState('');

  const displayName = name || me?.name || '';

  const saveProfile = async () => {
    try {
      await updateMe({ name: displayName }).unwrap();
      dispatch(pushToast('Profil gespeichert.', 'success'));
    } catch (caught) {
      dispatch(pushToast(errorMessage(caught), 'error'));
    }
  };

  const savePassword = async () => {
    setError('');
    try {
      const result = await changePassword({
        current_password: current, new_password: next,
      }).unwrap();
      // The old token is invalidated server side – keep the session alive.
      setToken(result.token);
      setCurrent('');
      setNext('');
      dispatch(pushToast('Passwort geändert.', 'success'));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <Section title="Profil">
      <Stack spacing={2}>
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
          }}
        >
          <TextField
            label="Anzeigename"
            value={displayName}
            onChange={(event) => setName(event.target.value)}
          />
          <TextField label="E-Mail" value={me?.email ?? ''} disabled />
        </Box>
        <Button
          size="small"
          variant="outlined"
          sx={{ alignSelf: 'flex-start' }}
          disabled={saving}
          onClick={saveProfile}
        >
          Profil speichern
        </Button>

        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
          }}
        >
          <TextField
            label="Aktuelles Passwort"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
          <TextField
            label="Neues Passwort"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(event) => setNext(event.target.value)}
          />
        </Box>
        <Button
          size="small"
          variant="outlined"
          sx={{ alignSelf: 'flex-start' }}
          disabled={changing || !current || next.length < 8}
          onClick={savePassword}
        >
          Passwort ändern
        </Button>
      </Stack>
    </Section>
  );
}
