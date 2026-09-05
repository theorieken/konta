'use client';

import Chip from '@mui/material/Chip';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { CategoryInline } from '@base/components/category-chip';
import { Money } from '@base/components/money';
import { ObjectFields } from '@base/components/objects/object-fields';
import { INTERVAL_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { formatDate, toNumber } from '@base/lib/format';
import type { Loan } from '@base/types';

export const loanFields: FieldDef[] = [
  { name: 'lender', label: 'Kreditgeber', kind: 'text', hideWhenEmpty: true },
  { name: 'principal', label: 'Kreditsumme', kind: 'money' },
  { name: 'instalment', label: 'Rate', kind: 'money' },
  { name: 'interest_rate', label: 'Zinssatz', kind: 'percent' },
  { name: 'interval', label: 'Intervall', kind: 'select', options: INTERVAL_OPTIONS },
  { name: 'day_of_month', label: 'Fällig am', kind: 'number' },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories' },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts' },
  { name: 'start_date', label: 'Beginn', kind: 'date' },
  { name: 'end_date', label: 'Ende', kind: 'date', hideWhenEmpty: true },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function LoanDisplay({ object }: { object: Loan }) {
  const principal = toNumber(object.remaining_at_start ?? object.principal);
  const paid = toNumber(object.paid_so_far);
  const progress = principal > 0 ? Math.min((paid / principal) * 100, 100) : 0;

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip
          size="small"
          label={object.is_active ? 'Läuft' : 'Beendet'}
          color={object.is_active ? 'success' : 'default'}
          variant={object.is_active ? 'filled' : 'outlined'}
        />
        <CategoryInline category={object.category_detail} />
      </Stack>

      <Stack spacing={0.5}>
        <Money value={`-${object.outstanding}`} variant="h1" />
        <Typography variant="body2" color="text.secondary">
          Restschuld · nächste Rate {formatDate(object.next_due_date)}
        </Typography>
      </Stack>

      <Stack spacing={0.75}>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{ height: 6, borderRadius: 3 }}
        />
        <Stack direction="row" justifyContent="space-between">
          <Typography variant="caption" color="text.secondary">
            Getilgt <Money value={paid} colored={false} variant="caption" />
          </Typography>
          <Typography variant="caption" color="text.secondary">
            von <Money value={principal} colored={false} variant="caption" />
          </Typography>
        </Stack>
      </Stack>

      <ObjectFields object={object} fields={loanFields} />
    </Stack>
  );
}
