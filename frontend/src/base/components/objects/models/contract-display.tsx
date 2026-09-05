'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { CategoryInline } from '@base/components/category-chip';
import { Money } from '@base/components/money';
import { ObjectFields } from '@base/components/objects/object-fields';
import { INTERVAL_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { formatDate } from '@base/lib/format';
import type { Contract } from '@base/types';

export const contractFields: FieldDef[] = [
  { name: 'provider', label: 'Anbieter', kind: 'text', hideWhenEmpty: true },
  { name: 'amount', label: 'Betrag', kind: 'money' },
  { name: 'interval', label: 'Intervall', kind: 'select', options: INTERVAL_OPTIONS },
  { name: 'day_of_month', label: 'Fällig am', kind: 'number', min: 1, max: 31 },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories' },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts' },
  { name: 'start_date', label: 'Beginn', kind: 'date' },
  { name: 'end_date', label: 'Ende', kind: 'date', hideWhenEmpty: true },
  { name: 'contract_number', label: 'Vertragsnummer', kind: 'text', hideWhenEmpty: true },
  {
    name: 'cancellation_period_days', label: 'Kündigungsfrist', kind: 'number',
    hideWhenEmpty: true,
    render: (object) => `${object.cancellation_period_days} Tage`,
  },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function ContractDisplay({ object }: { object: Contract }) {
  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip
          size="small"
          label={object.is_active ? 'Aktiv' : 'Pausiert'}
          color={object.is_active ? 'success' : 'default'}
          variant={object.is_active ? 'filled' : 'outlined'}
        />
        <CategoryInline category={object.category_detail} />
      </Stack>

      <Stack spacing={0.5}>
        <Money value={object.monthly_equivalent} variant="h1" />
        <Typography variant="body2" color="text.secondary">
          pro Monat · nächste Fälligkeit {formatDate(object.next_due_date)}
        </Typography>
      </Stack>

      <ObjectFields object={object} fields={contractFields} />

      <Typography variant="caption" color="text.secondary">
        {object.planned_count} geplante Transaktionen im Prognosezeitraum
      </Typography>
    </Stack>
  );
}
