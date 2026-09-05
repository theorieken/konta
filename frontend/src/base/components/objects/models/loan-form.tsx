'use client';

import { ModelForm } from '@base/components/objects/model-form';
import { INTERVAL_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { startOfMonth } from '@base/lib/format';
import { useCreateLoanMutation, useUpdateLoanMutation } from '@base/store/api';
import type { Loan } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true, wide: true },
  { name: 'principal', label: 'Kreditsumme', kind: 'money', required: true, min: 0 },
  { name: 'instalment', label: 'Rate', kind: 'money', required: true, min: 0 },
  { name: 'interest_rate', label: 'Zinssatz p. a.', kind: 'percent', step: 0.001, min: 0 },
  {
    name: 'remaining_at_start', label: 'Restschuld heute', kind: 'money', min: 0,
    helper: 'Leer = volle Kreditsumme',
  },
  { name: 'interval', label: 'Intervall', kind: 'select', options: INTERVAL_OPTIONS, required: true },
  { name: 'day_of_month', label: 'Fällig am', kind: 'number', min: 1, max: 31 },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories', required: true },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts', required: true },
  { name: 'start_date', label: 'Beginn', kind: 'date', required: true },
  { name: 'end_date', label: 'Letzte Rate', kind: 'date' },
  { name: 'lender', label: 'Kreditgeber', kind: 'text' },
  { name: 'is_active', label: 'Aktiv', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface LoanFormProps {
  object?: Loan | null;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function LoanForm({ object, defaults, onSaved, onCancel }: LoanFormProps) {
  const [create, createState] = useCreateLoanMutation();
  const [update, updateState] = useUpdateLoanMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      defaults={{
        interval: 'monthly',
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
