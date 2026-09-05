'use client';

import { ModelForm } from '@base/components/objects/model-form';
import type { FieldDef } from '@base/components/objects/fields';
import { useSaveSettingsMutation } from '@base/store/api';
import type { SettingObject } from '@base/types';

interface SettingFormProps {
  object?: SettingObject | null;
  onSaved?: () => void;
  onCancel?: () => void;
}

/**
 * Single setting editor. The settings page uses the grouped bulk editor
 * instead – this form exists so the object drawer can edit any setting too.
 */
export function SettingForm({ object, onSaved, onCancel }: SettingFormProps) {
  const [saveSettings, { isLoading }] = useSaveSettingsMutation();

  const fields: FieldDef[] = [
    {
      name: 'value',
      label: object?.name || object?.key || 'Wert',
      kind: object?.value_type === 'number'
        ? 'number'
        : object?.value_type === 'boolean'
          ? 'boolean'
          : object?.value_type === 'date'
            ? 'date'
            : 'text',
      wide: true,
      helper: object?.description,
    },
  ];

  return (
    <ModelForm
      fields={fields}
      object={object}
      saving={isLoading}
      onSaved={onSaved}
      onCancel={onCancel}
      save={async (payload) => {
        if (!object) throw new Error('Unbekannte Einstellung.');
        return saveSettings({ [object.key]: payload.value }).unwrap();
      }}
    />
  );
}
