'use client';

import Alert from '@mui/material/Alert';

import { modelFor } from '@base/components/objects/registry';
import type { BaseObject } from '@base/types';

interface ObjectFormProps {
  /** Existing object to edit … */
  object?: BaseObject | null;
  /** … or the table to create a new object in. */
  dbTable?: string;
  defaults?: Record<string, unknown>;
  onSaved?: () => void;
  onCancel?: () => void;
}

/** Renders the `*-form` component that belongs to an object's model. */
export function ObjectForm({ object, dbTable, defaults, onSaved, onCancel }: ObjectFormProps) {
  const table = dbTable ?? object?._meta?.db_table;
  const entry = modelFor(table);

  if (!entry) {
    return <Alert severity="warning">Für „{table}“ gibt es kein Formular.</Alert>;
  }

  const Form = entry.Form;
  return <Form object={object} defaults={defaults} onSaved={onSaved} onCancel={onCancel} />;
}
