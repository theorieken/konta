'use client';

import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectFields } from '@base/components/objects/object-fields';
import type { FieldDef } from '@base/components/objects/fields';
import type { Household } from '@base/types';

const fields: FieldDef[] = [
  { name: 'member_count', label: 'Mitglieder', kind: 'number' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function HouseholdDisplay({ object }: { object: Household }) {
  return (
    <Stack spacing={3}>
      <Typography variant="h2">{object.name}</Typography>
      <ObjectFields object={object} fields={fields} />
    </Stack>
  );
}
