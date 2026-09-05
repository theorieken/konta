'use client';

import { ModelForm } from '@base/components/objects/model-form';
import type { FieldDef } from '@base/components/objects/fields';
import { useUpdateObjectMutation } from '@base/store/api';
import type { User } from '@base/types';

const fields: FieldDef[] = [
  { name: 'name', label: 'Anzeigename', kind: 'text', required: true },
  { name: 'email', label: 'E-Mail', kind: 'text', required: true },
  { name: 'first_name', label: 'Vorname', kind: 'text' },
  { name: 'last_name', label: 'Nachname', kind: 'text' },
  { name: 'color', label: 'Farbe', kind: 'text', placeholder: '#3b4a68' },
  { name: 'is_active', label: 'Aktiv', kind: 'boolean' },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true },
];

interface UserFormProps {
  object?: User | null;
  onSaved?: () => void;
  onCancel?: () => void;
}

/** Passwords are changed on the settings page, never in this form. */
export function UserForm({ object, onSaved, onCancel }: UserFormProps) {
  const [updateObject, { isLoading }] = useUpdateObjectMutation();

  return (
    <ModelForm
      fields={fields}
      object={object}
      saving={isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) => {
        if (!object) throw new Error('Benutzer können nur im Onboarding angelegt werden.');
        return updateObject({ reference: object._meta.object_reference, body: payload }).unwrap();
      }}
    />
  );
}
