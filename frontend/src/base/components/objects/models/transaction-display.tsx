'use client';

import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import LinkIcon from '@mui/icons-material/Link';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { CategoryInline } from '@base/components/category-chip';
import { Money } from '@base/components/money';
import { ObjectChip } from '@base/components/objects/object-chip';
import { ObjectFields } from '@base/components/objects/object-fields';
import { STATE_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { formatDate, formatPercent } from '@base/lib/format';
import type { Transaction } from '@base/types';

export const transactionFields: FieldDef[] = [
  { name: 'booking_date', label: 'Datum', kind: 'date', required: true },
  {
    name: 'amount', label: 'Betrag', kind: 'money', required: true,
    render: (object) => <Money value={object.amount} variant="body1" />,
  },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories', required: true },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts', required: true },
  { name: 'state', label: 'Status', kind: 'select', options: STATE_OPTIONS, required: true },
  { name: 'counterparty', label: 'Gegenseite', kind: 'text', hideWhenEmpty: true },
  { name: 'purpose', label: 'Verwendungszweck', kind: 'textarea', wide: true, hideWhenEmpty: true },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

const SOURCE_LABEL: Record<string, string> = {
  manual: 'Manuell erfasst',
  import: 'Aus CSV importiert',
  generated: 'Aus dem Plan erzeugt',
};

export function TransactionDisplay({ object }: { object: Transaction }) {
  const origin = object.origin_reference;

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Chip
          size="small"
          label={object.state === 'planned' ? 'Geplant' : 'Gebucht'}
          variant={object.state === 'planned' ? 'outlined' : 'filled'}
        />
        {object.needs_review ? (
          <Chip size="small" color="warning" label="Prüfen" variant="outlined" />
        ) : null}
        {object.classified_by_ai ? (
          <Chip
            size="small"
            variant="outlined"
            icon={<AutoAwesomeIcon />}
            label={
              object.classification_confidence
                ? `KI · ${formatPercent(object.classification_confidence * 100)}`
                : 'KI'
            }
          />
        ) : null}
        {object.is_matched ? (
          <Chip size="small" variant="outlined" icon={<LinkIcon />} label="Abgeglichen" />
        ) : null}
        {object.is_internal_transfer ? (
          <Chip size="small" variant="outlined" icon={<SwapHorizIcon />} label="Umbuchung" />
        ) : null}
      </Stack>

      <Stack spacing={0.5}>
        <Money value={object.amount} variant="h1" />
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Typography variant="body2" color="text.secondary">
            {formatDate(object.booking_date)}
          </Typography>
          <CategoryInline category={object.category_detail} />
        </Stack>
      </Stack>

      <ObjectFields object={object} fields={transactionFields.filter(
        (field) => !['amount', 'booking_date', 'category'].includes(field.name),
      )} />

      {(origin || object.classification_note) && (
        <Stack spacing={1}>
          {origin ? (
            <Typography variant="body2" color="text.secondary">
              Erzeugt aus <ObjectChip reference={origin} label="Quelle öffnen" />
            </Typography>
          ) : null}
          {object.classification_note ? (
            <Typography variant="caption" color="text.secondary">
              Zuordnung: {object.classification_note} · {SOURCE_LABEL[object.source] ?? object.source}
            </Typography>
          ) : (
            <Typography variant="caption" color="text.secondary">
              {SOURCE_LABEL[object.source] ?? object.source}
            </Typography>
          )}
        </Stack>
      )}
      {object.transfer_pair ? (
        <Typography variant="body2" color="text.secondary">
          Gegenbuchung:{' '}
          <ObjectChip
            reference={`finance_transaction-${object.transfer_pair}`}
            label="Transaktion öffnen"
          />
        </Typography>
      ) : null}
    </Stack>
  );
}
