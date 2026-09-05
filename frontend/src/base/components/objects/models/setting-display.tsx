'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectFields } from '@base/components/objects/object-fields';
import type { FieldDef } from '@base/components/objects/fields';
import type { SettingObject } from '@base/types';

export const settingFields: FieldDef[] = [
  { name: 'key', label: 'Schlüssel', kind: 'text' },
  { name: 'value_type', label: 'Typ', kind: 'text' },
  { name: 'description', label: 'Beschreibung', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function SettingDisplay({ object }: { object: SettingObject }) {
  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h2">{object.name || object.key}</Typography>
          {object.is_secret ? <Chip size="small" variant="outlined" label="Geheim" /> : null}
        </Stack>
        <Typography variant="body2" color="text.secondary" className="tabular">
          {object.is_secret
            ? object.is_set ? '•••••••• (gesetzt)' : 'nicht gesetzt'
            : String(object.value ?? '–')}
        </Typography>
      </Stack>

      <ObjectFields object={object} fields={settingFields} />
    </Stack>
  );
}
