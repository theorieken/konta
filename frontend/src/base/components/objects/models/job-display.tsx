'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { CategoryInline } from '@base/components/category-chip';
import { Money } from '@base/components/money';
import { ObjectFields } from '@base/components/objects/object-fields';
import { INTERVAL_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { formatDate, formatNumber, toNumber } from '@base/lib/format';
import type { Job } from '@base/types';

export const jobFields: FieldDef[] = [
  { name: 'employer', label: 'Arbeitgeber', kind: 'text', hideWhenEmpty: true },
  { name: 'gross_amount', label: 'Brutto', kind: 'money', hideWhenEmpty: true },
  { name: 'net_amount', label: 'Netto', kind: 'money' },
  { name: 'tax_class', label: 'Steuerklasse', kind: 'text', hideWhenEmpty: true },
  {
    name: 'part_time_factor', label: 'Teilzeitquote', kind: 'number', hideWhenEmpty: true,
    render: (object) => `${formatNumber(toNumber(object.part_time_factor) * 100, 0)} %`,
  },
  { name: 'interval', label: 'Intervall', kind: 'select', options: INTERVAL_OPTIONS },
  { name: 'day_of_month', label: 'Zahltag', kind: 'number' },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories' },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts' },
  { name: 'start_date', label: 'Beginn', kind: 'date' },
  { name: 'end_date', label: 'Ende', kind: 'date', hideWhenEmpty: true },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function JobDisplay({ object }: { object: Job }) {
  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip
          size="small"
          label={object.is_active ? 'Aktiv' : 'Beendet'}
          color={object.is_active ? 'success' : 'default'}
          variant={object.is_active ? 'filled' : 'outlined'}
        />
        <CategoryInline category={object.category_detail} />
      </Stack>

      <Stack spacing={0.5}>
        <Money value={object.net_amount} variant="h1" />
        <Typography variant="body2" color="text.secondary">
          netto · nächste Zahlung {formatDate(object.next_due_date)}
        </Typography>
      </Stack>

      <ObjectFields object={object} fields={jobFields} />
    </Stack>
  );
}
