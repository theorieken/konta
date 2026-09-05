'use client';

import { ModelForm } from '@base/components/objects/model-form';
import type { FieldDef } from '@base/components/objects/fields';
import { useUpdateObjectMutation } from '@base/store/api';
import type { FileObject } from '@base/types';

/** Uploaded files are immutable – only the metadata can be edited. */
const fields: FieldDef[] = [
  { name: 'name', label: 'Bezeichnung', kind: 'text', required: true, wide: true },
  { name: 'account', label: 'Konto', kind: 'reference', source: 'accounts' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface FileFormProps {
  object?: FileObject | null;
  onSaved?: () => void;
  onCancel?: () => void;
}

export function FileForm({ object, onSaved, onCancel }: FileFormProps) {
  const [updateObject, { isLoading }] = useUpdateObjectMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      saving={isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) => {
        if (!object) throw new Error('Dateien werden in den Einstellungen hochgeladen.');
        return updateObject({ reference: object._meta.object_reference, body: payload }).unwrap();
      }}
    />
  );
}
