'use client';

import { ModelForm } from '@base/components/objects/model-form';
import type { FieldDef } from '@base/components/objects/fields';
import { useUpdateObjectMutation } from '@base/store/api';
import type { Household } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Name', kind: 'text', required: true, wide: true },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface HouseholdFormProps {
  object?: Household | null;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function HouseholdForm({ object, onSaved, onCancel }: HouseholdFormProps) {
  const [updateObject, { isLoading }] = useUpdateObjectMutation();
  return (
    <ModelForm
      fields={fields}
      object={object}
      saving={isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) => {
        if (!object) throw new Error('Haushalte werden in der Seitenleiste angelegt.');
        return updateObject({ reference: object._meta.object_reference, body: payload }).unwrap();
      }}
    />
  );
}
