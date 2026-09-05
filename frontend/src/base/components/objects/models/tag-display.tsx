'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectChip } from '@base/components/objects/object-chip';
import { ObjectFields } from '@base/components/objects/object-fields';
import type { FieldDef } from '@base/components/objects/fields';
import type { BaseObject } from '@base/types';

export const tagFields: FieldDef[] = [
  { name: 'db_table', label: 'Tabelle', kind: 'text' },
  { name: 'color', label: 'Farbe', kind: 'text', hideWhenEmpty: true },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

interface TagObject extends BaseObject {
  color: string;
  db_table: string;
  object_uuid: string;
  target_reference?: string;
}

export function TagDisplay({ object }: { object: TagObject }) {
  const target = object.target_reference || `${object.db_table}-${object.object_uuid}`;
  return (
    <Stack spacing={3}>
      <Chip
        label={object.name}
        sx={{
          alignSelf: 'flex-start',
          bgcolor: object.color || 'action.hover',
          color: object.color ? '#fff' : 'text.primary',
        }}
      />
      <Typography variant="body2" color="text.secondary">
        Vergeben an <ObjectChip reference={target} label={target} />
      </Typography>
      <ObjectFields object={object} fields={tagFields} />
    </Stack>
  );
}
