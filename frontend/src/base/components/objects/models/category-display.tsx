'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectFields } from '@base/components/objects/object-fields';
import { CATEGORY_KIND_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { CategoryIcon } from '@base/lib/icons';
import type { Category } from '@base/types';

export const categoryFields: FieldDef[] = [
  { name: 'kind', label: 'Art', kind: 'select', options: CATEGORY_KIND_OPTIONS },
  { name: 'slug', label: 'Kürzel', kind: 'text' },
  { name: 'monthly_budget', label: 'Monatsbudget', kind: 'money', hideWhenEmpty: true },
  { name: 'parent', label: 'Oberkategorie', kind: 'reference', source: 'categories', hideWhenEmpty: true },
  {
    name: 'keywords', label: 'Stichwörter für den Import', kind: 'keywords',
    wide: true, hideWhenEmpty: true,
  },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function CategoryDisplay({ object }: { object: Category }) {
  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1.5} alignItems="center">
        <CategoryIcon name={object.icon} sx={{ fontSize: 32, color: 'text.primary' }} />
        <Stack>
          <Typography variant="h2">{object.name}</Typography>
          <Typography variant="caption" color="text.secondary">
            {object.transaction_count ?? 0} Transaktionen
          </Typography>
        </Stack>
        {object.is_system ? (
          <Chip size="small" variant="outlined" label="Standard" sx={{ ml: 'auto' }} />
        ) : null}
      </Stack>

      <ObjectFields object={object} fields={categoryFields} />
    </Stack>
  );
}
