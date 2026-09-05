'use client';

import { ModelForm } from '@base/components/objects/model-form';
import {
  DIRECTION_OPTIONS,
  INTERVAL_OPTIONS,
  type FieldDef,
} from '@base/components/objects/fields';
import { startOfMonth } from '@base/lib/format';
import { useCreateContractMutation, useUpdateContractMutation } from '@base/store/api';
import type { Contract } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true, wide: true },
  { name: 'amount', label: 'Betrag', kind: 'money', required: true, min: 0 },
  {
    name: 'contract_direction', label: 'Art', kind: 'select',
    options: DIRECTION_OPTIONS, required: true,
  },
  { name: 'interval', label: 'Intervall', kind: 'select', options: INTERVAL_OPTIONS, required: true },
  {
    name: 'day_of_month', label: 'Fällig am', kind: 'number', min: 1, max: 31,
    helper: 'Tag im Monat', visible: (draft) => !['weekly', 'biweekly'].includes(String(draft.interval)),
  },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories', required: true },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts', required: true },
  { name: 'start_date', label: 'Beginn', kind: 'date', required: true },
  { name: 'end_date', label: 'Ende', kind: 'date', helper: 'Leer = unbefristet' },
  { name: 'provider', label: 'Anbieter', kind: 'text' },
  { name: 'contract_number', label: 'Vertragsnummer', kind: 'text' },
  {
    name: 'cancellation_period_days', label: 'Kündigungsfrist (Tage)', kind: 'number', min: 0,
  },
  { name: 'is_active', label: 'Aktiv', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface ContractFormProps {
  object?: Contract | null;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function ContractForm({ object, defaults, onSaved, onCancel }: ContractFormProps) {
  const [create, createState] = useCreateContractMutation();
  const [update, updateState] = useUpdateContractMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      defaults={{
        interval: 'monthly',
        contract_direction: 'expense',
        day_of_month: 1,
        is_active: true,
        start_date: startOfMonth(),
        ...defaults,
      }}
      saving={createState.isLoading || updateState.isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) =>
        object ? update({ id: object.id, ...payload }).unwrap() : create(payload).unwrap()
      }
    />
  );
}
