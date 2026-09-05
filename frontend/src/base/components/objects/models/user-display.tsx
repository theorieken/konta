'use client';

import Avatar from '@mui/material/Avatar';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectFields } from '@base/components/objects/object-fields';
import type { FieldDef } from '@base/components/objects/fields';
import { formatRelative } from '@base/lib/format';
import type { User } from '@base/types';

export const userFields: FieldDef[] = [
  { name: 'email', label: 'E-Mail', kind: 'text' },
  { name: 'first_name', label: 'Vorname', kind: 'text', hideWhenEmpty: true },
  { name: 'last_name', label: 'Nachname', kind: 'text', hideWhenEmpty: true },
  {
    name: 'last_login', label: 'Zuletzt angemeldet', kind: 'text',
    render: (object) => formatRelative(object.last_login as string),
  },
  { name: 'is_active', label: 'Aktiv', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function UserDisplay({ object }: { object: User }) {
  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={2} alignItems="center">
        <Avatar sx={{ width: 48, height: 48, bgcolor: object.color || 'primary.main' }}>
          {object.initials}
        </Avatar>
        <Stack>
          <Typography variant="h2">{object.display_name}</Typography>
          <Typography variant="body2" color="text.secondary">{object.email}</Typography>
        </Stack>
        {object.is_staff ? (
          <Chip size="small" variant="outlined" label="Admin" sx={{ ml: 'auto' }} />
        ) : null}
      </Stack>

      <ObjectFields object={object} fields={userFields} />
    </Stack>
  );
}
