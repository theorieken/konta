'use client';

import { ModelForm } from '@base/components/objects/model-form';
import { CATEGORY_KIND_OPTIONS, type FieldDef } from '@base/components/objects/fields';
import { ICON_NAMES } from '@base/lib/icons';
import { useCreateCategoryMutation, useUpdateCategoryMutation } from '@base/store/api';
import type { Category } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true },
  { name: 'kind', label: 'Art', kind: 'select', options: CATEGORY_KIND_OPTIONS, required: true },
  {
    name: 'icon', label: 'Icon', kind: 'select',
    options: ICON_NAMES.map((name) => ({ value: name, label: name, icon: name })),
  },
  { name: 'color', label: 'Farbe', kind: 'text', placeholder: '#5e35b1' },
  { name: 'monthly_budget', label: 'Monatsbudget', kind: 'money', min: 0 },
  { name: 'parent', label: 'Oberkategorie', kind: 'reference', source: 'categories' },
  {
    name: 'keywords', label: 'Stichwörter', kind: 'keywords', wide: true,
    helper: 'Helfen der KI und dem Fallback beim Zuordnen importierter Umsätze.',
  },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface CategoryFormProps {
  object?: Category | null;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function CategoryForm({ object, defaults, onSaved, onCancel }: CategoryFormProps) {
  const [create, createState] = useCreateCategoryMutation();
  const [update, updateState] = useUpdateCategoryMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      defaults={{ kind: 'expense', icon: 'more_horiz', color: '#9e9e9e', ...defaults }}
      saving={createState.isLoading || updateState.isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) =>
        object ? update({ id: object.id, ...payload }).unwrap() : create(payload).unwrap()
      }
    />
  );
}
