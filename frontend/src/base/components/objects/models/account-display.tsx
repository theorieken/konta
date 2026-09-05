'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { Money } from '@base/components/money';
import { ObjectFields } from '@base/components/objects/object-fields';
import { ACCOUNT_KIND_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import type { Account } from '@base/types';

export const accountFields: FieldDef[] = [
  { name: 'holder', label: 'Inhaber', kind: 'text', hideWhenEmpty: true },
  { name: 'kind', label: 'Art', kind: 'select', options: ACCOUNT_KIND_OPTIONS },
  { name: 'bank_name', label: 'Bank', kind: 'text', hideWhenEmpty: true },
  { name: 'iban', label: 'IBAN', kind: 'text', hideWhenEmpty: true },
  { name: 'opening_balance', label: 'Startsaldo', kind: 'money' },
  { name: 'opening_balance_date', label: 'Startsaldo am', kind: 'date', hideWhenEmpty: true },
  { name: 'currency', label: 'Währung', kind: 'text' },
  { name: 'include_in_net_worth', label: 'Im Gesamtvermögen', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function AccountDisplay({ object }: { object: Account }) {
  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip
          size="small"
          label={object.is_active ? 'Aktiv' : 'Inaktiv'}
          color={object.is_active ? 'success' : 'default'}
          variant={object.is_active ? 'filled' : 'outlined'}
        />
        {object.holder ? (
          <Typography variant="body2" color="text.secondary">{object.holder}</Typography>
        ) : null}
      </Stack>

      <Stack spacing={0.5}>
        <Money value={object.balance_today} currency={object.currency} variant="h1" />
        <Typography variant="body2" color="text.secondary">
          Saldo heute · {object.transaction_count} Transaktionen
        </Typography>
      </Stack>

      <ObjectFields object={object} fields={accountFields} />
    </Stack>
  );
}
