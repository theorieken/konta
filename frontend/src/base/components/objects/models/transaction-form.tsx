'use client';

import { ModelForm } from '@base/components/objects/model-form';
import { DIRECTION_OPTIONS, STATE_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { today } from '@base/lib/format';
import {
  useCreateTransactionMutation,
  useUpdateTransactionMutation,
} from '@base/store/api';
import type { Transaction } from '@base/types';

/**
 * The form works with a positive amount plus a direction; the API turns that
 * into the signed amount the database stores.
 */
const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true, wide: true },
  { name: 'direction', label: 'Art', kind: 'select', options: DIRECTION_OPTIONS, required: true },
  { name: 'amount', label: 'Betrag', kind: 'money', required: true, min: 0 },
  { name: 'booking_date', label: 'Datum', kind: 'date', required: true },
  { name: 'state', label: 'Status', kind: 'select', options: STATE_OPTIONS, required: true },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories', required: true },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts', required: true },
  { name: 'counterparty', label: 'Gegenseite', kind: 'text' },
  { name: 'purpose', label: 'Verwendungszweck', kind: 'textarea', wide: true },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface TransactionFormProps {
  object?: Transaction | null;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function TransactionForm({ object, defaults, onSaved, onCancel }: TransactionFormProps) {
  const [create, createState] = useCreateTransactionMutation();
  const [update, updateState] = useUpdateTransactionMutation();

  const seed = { booking_date: today(), state: 'planned', direction: 'expense', ...defaults };

  // The stored amount is signed – split it into direction + magnitude so the
  // form never asks the user to type a minus sign.
  const editing = object
    ? {
        ...object,
        direction: Number(object.amount) >= 0 ? 'income' : 'expense',
        amount: Math.abs(Number(object.amount)).toFixed(2),
      }
    : null;

  return (
    <ModelForm
      fields={fields}
      object={editing}
      defaults={seed}
      saving={createState.isLoading || updateState.isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) => {
        if (object) return update({ id: object.id, ...payload }).unwrap();
        return create(payload).unwrap();
      }}
    />
  );
}
