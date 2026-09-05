'use client';

import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { ObjectFormFields } from '@base/components/objects/object-form-fields';
import { collectValues, type FieldDef } from '@base/components/objects/fields';
import { errorMessage, fieldErrors } from '@base/api/client';
import type { BaseObject } from '@base/types';

export interface ModelFormProps {
  fields: FieldDef[];
  /** Existing object – omit to create a new one. */
  object?: BaseObject | null;
  /** Prefilled values for a new object. */
  defaults?: Record<string, unknown>;
  save: (payload: Record<string, unknown>) => Promise<unknown>;
  saving?: boolean;
  onSaved?: () => void;
  onCancel?: () => void;
  submitLabel?: string;
  /** Extra content rendered above the buttons. */
  children?: ReactNode;
}

function initialDraft(
  fields: FieldDef[],
  object?: BaseObject | null,
  defaults?: Record<string, unknown>,
): Record<string, unknown> {
  const draft: Record<string, unknown> = {};
  fields.forEach((field) => {
    const fromObject = object ? object[field.name] : undefined;
    const fromDefaults = defaults?.[field.name];
    const value = fromObject ?? fromDefaults;
    if (field.kind === 'boolean') draft[field.name] = Boolean(value ?? false);
    else if (field.kind === 'keywords') draft[field.name] = (value as string[]) ?? [];
    else draft[field.name] = value ?? '';
  });
  return draft;
}

/**
 * The shell every `*-form` component uses: state, validation errors from the
 * API and the save/cancel buttons. Models only declare their fields.
 */
export function ModelForm({
  fields,
  object,
  defaults,
  save,
  saving = false,
  onSaved,
  onCancel,
  submitLabel,
  children,
}: ModelFormProps) {
  const [draft, setDraft] = useState(() => initialDraft(fields, object, defaults));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');

  const signature = useMemo(() => object?.id ?? 'new', [object?.id]);
  useEffect(() => {
    setDraft(initialDraft(fields, object, defaults));
    setErrors({});
    setMessage('');
    // Re-seeding on identity change only; `fields`/`defaults` are stable literals.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);

  const change = (name: string, value: unknown) => {
    setDraft((current) => ({ ...current, [name]: value }));
    setErrors((current) => {
      if (!current[name]) return current;
      const next = { ...current };
      delete next[name];
      return next;
    });
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');
    try {
      await save(collectValues(fields, draft));
      onSaved?.();
    } catch (error) {
      setErrors(fieldErrors(error));
      setMessage(errorMessage(error));
    }
  };

  return (
    <Stack component="form" onSubmit={submit} spacing={2}>
      {message ? <Alert severity="error">{message}</Alert> : null}

      <ObjectFormFields fields={fields} draft={draft} errors={errors} onChange={change} />

      {children}

      <Stack direction="row" spacing={1} justifyContent="flex-end">
        {onCancel ? (
          <Button color="inherit" onClick={onCancel} disabled={saving}>
            Abbrechen
          </Button>
        ) : null}
        <Button type="submit" variant="contained" disabled={saving}>
          {submitLabel ?? (object ? 'Speichern' : 'Anlegen')}
        </Button>
      </Stack>
    </Stack>
  );
}
