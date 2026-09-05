'use client';

import { ModelForm } from '@base/components/objects/model-form';
import { ACCOUNT_KIND_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { useCreateAccountMutation, useUpdateAccountMutation } from '@base/store/api';
import type { Account } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true },
  { name: 'holder', label: 'Inhaber', kind: 'text' },
  { name: 'kind', label: 'Art', kind: 'select', options: ACCOUNT_KIND_OPTIONS, required: true },
  { name: 'opening_balance', label: 'Startsaldo', kind: 'money' },
  { name: 'opening_balance_date', label: 'Startsaldo am', kind: 'date' },
  { name: 'currency', label: 'Währung', kind: 'text' },
  { name: 'bank_name', label: 'Bank', kind: 'text' },
  { name: 'iban', label: 'IBAN', kind: 'text' },
  { name: 'include_in_net_worth', label: 'Im Gesamtvermögen zählen', kind: 'boolean' },
  { name: 'is_active', label: 'Aktiv', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface AccountFormProps {
  object?: Account | null;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function AccountForm({ object, defaults, onSaved, onCancel }: AccountFormProps) {
  const [create, createState] = useCreateAccountMutation();
  const [update, updateState] = useUpdateAccountMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      defaults={{
        kind: 'checking',
        currency: 'EUR',
        opening_balance: '0.00',
        include_in_net_worth: true,
        is_active: true,
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
