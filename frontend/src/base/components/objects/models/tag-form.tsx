'use client';

import { ModelForm } from '@base/components/objects/model-form';
import type { FieldDef } from '@base/components/objects/fields';
import { useUpdateObjectMutation } from '@base/store/api';
import type { BaseObject } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Name', kind: 'text', required: true },
  { name: 'color', label: 'Farbe', kind: 'text', placeholder: '#8ab' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface TagFormProps {
  object?: BaseObject | null;
  onSaved?: () => void;
  onCancel?: () => void;
}

/** Tags are created inline on the object they belong to – see TagEditor. */
export function TagForm({ object, onSaved, onCancel }: TagFormProps) {
  const [updateObject, { isLoading }] = useUpdateObjectMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      saving={isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) => {
        if (!object) throw new Error('Tags werden direkt am Objekt vergeben.');
        return updateObject({ reference: object._meta.object_reference, body: payload }).unwrap();
      }}
    />
  );
}
