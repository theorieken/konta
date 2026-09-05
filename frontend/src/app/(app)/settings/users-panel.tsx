'use client';

import AddIcon from '@mui/icons-material/Add';
import Alert from '@mui/material/Alert';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import { errorMessage } from '@base/api/client';
import { Section } from '@base/components/section';
import {
  useInviteUserMutation,
  useMeQuery,
  useSendPasswordLinkMutation,
  useUsersQuery,
} from '@base/store/api';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';
import type { User } from '@base/types';

export function UsersPanel() {
  const dispatch = useAppDispatch();
  const { data: me } = useMeQuery();
  const { data: users } = useUsersQuery({ page_size: 200 });
  const [inviteUser, { isLoading: inviting }] = useInviteUserMutation();
  const [sendPasswordLink] = useSendPasswordLinkMutation();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [sendingId, setSendingId] = useState<string | null>(null);

  const invite = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await inviteUser({ name, email }).unwrap();
      dispatch(pushToast('Einladung wurde versendet.', 'success'));
      setName('');
      setEmail('');
      setOpen(false);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  const sendLink = async (user: User) => {
    setSendingId(user.id);
    try {
      await sendPasswordLink(user.id).unwrap();
      dispatch(pushToast(
        user.is_active ? 'Reset-Link wurde versendet.' : 'Einladung wurde erneut versendet.',
        'success',
      ));
    } catch (caught) {
      dispatch(pushToast(errorMessage(caught), 'error'));
    } finally {
      setSendingId(null);
    }
  };

  return (
    <>
      <Section
        title="Benutzer"
        action={me?.is_staff ? (
          <Button size="small" startIcon={<AddIcon />} onClick={() => setOpen(true)}>
            Benutzer
          </Button>
        ) : undefined}
      >
        <Stack divider={<Divider flexItem />}>
          {(users?.results ?? []).map((user) => (
            <Stack
              key={user.id}
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1.5}
              alignItems={{ xs: 'flex-start', sm: 'center' }}
              sx={{ py: 1.25, '&:first-of-type': { pt: 0 }, '&:last-of-type': { pb: 0 } }}
            >
              <Avatar sx={{ width: 32, height: 32, fontSize: '0.75rem', bgcolor: 'primary.main' }}>
                {user.initials}
              </Avatar>
              <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>{user.display_name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {user.email} · {user.is_active ? 'Aktiv' : 'Einladung ausstehend'}
                </Typography>
              </Box>
              {me?.is_staff ? (
                <Button
                  size="small"
                  color="inherit"
                  disabled={sendingId === user.id}
                  onClick={() => void sendLink(user)}
                >
                  {user.is_active ? 'Reset-Link senden' : 'Einladung erneut senden'}
                </Button>
              ) : null}
            </Stack>
          ))}
        </Stack>
      </Section>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="xs">
        <Box component="form" onSubmit={invite}>
          <DialogTitle>Benutzer einladen</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              {error ? <Alert severity="error">{error}</Alert> : null}
              <TextField
                label="Name"
                autoFocus
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
              <TextField
                label="E-Mail"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
              <Typography variant="caption" color="text.secondary">
                Die Person erhält einen einmal verwendbaren Link, um ihr Passwort festzulegen.
              </Typography>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button color="inherit" onClick={() => setOpen(false)}>Abbrechen</Button>
            <Button type="submit" variant="contained" disabled={inviting || !name || !email}>
              Einladen
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </>
  );
}
