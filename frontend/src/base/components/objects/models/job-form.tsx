'use client';

import { ModelForm } from '@base/components/objects/model-form';
import { INTERVAL_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { startOfMonth } from '@base/lib/format';
import { useCreateJobMutation, useUpdateJobMutation } from '@base/store/api';
import type { Job } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true, wide: true },
  { name: 'net_amount', label: 'Netto', kind: 'money', required: true, min: 0 },
  { name: 'gross_amount', label: 'Brutto', kind: 'money', min: 0 },
  { name: 'employer', label: 'Arbeitgeber', kind: 'text' },
  { name: 'tax_class', label: 'Steuerklasse', kind: 'text', placeholder: 'I, VI …' },
  {
    name: 'part_time_factor', label: 'Teilzeitquote', kind: 'number',
    step: 0.05, min: 0, max: 1, helper: '1 = Vollzeit',
  },
  { name: 'interval', label: 'Intervall', kind: 'select', options: INTERVAL_OPTIONS, required: true },
  { name: 'day_of_month', label: 'Zahltag', kind: 'number', min: 1, max: 31 },
  { name: 'category', label: 'Kategorie', kind: 'reference', source: 'categories', required: true },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts', required: true },
  { name: 'start_date', label: 'Beginn', kind: 'date', required: true },
  { name: 'end_date', label: 'Ende', kind: 'date', helper: 'Leer = unbefristet' },
  { name: 'is_active', label: 'Aktiv', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface JobFormProps {
  object?: Job | null;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function JobForm({ object, defaults, onSaved, onCancel }: JobFormProps) {
  const [create, createState] = useCreateJobMutation();
  const [update, updateState] = useUpdateJobMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      defaults={{
        interval: 'monthly',
        day_of_month: 28,
        part_time_factor: 1,
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
