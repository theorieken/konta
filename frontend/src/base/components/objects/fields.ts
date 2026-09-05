/**
 * Declarative field descriptions.
 *
 * Each model contributes a short list of `FieldDef`s; `ObjectFields` renders
 * them read-only and `ObjectFormFields` renders them as inputs. That keeps the
 * per-model display/form components small enough to read at a glance while
 * still letting any of them drop down to a custom renderer.
 */

import type { ReactNode } from 'react';

export type FieldKind =
  | 'text'
  | 'textarea'
  | 'number'
  | 'money'
  | 'percent'
  | 'date'
  | 'boolean'
  | 'select'
  | 'reference'
  | 'keywords'
  | 'custom';

/** Select options that have to be fetched from the API. */
export type OptionSource = 'accounts' | 'categories' | 'contracts' | 'loans' | 'jobs';

export interface SelectOption {
  value: string;
  label: string;
  color?: string;
  icon?: string;
}

export interface FieldDef {
  name: string;
  label: string;
  kind: FieldKind;
  /** Static options for `kind: 'select'`. */
  options?: SelectOption[];
  /** Dynamic options loaded from the API. */
  source?: OptionSource;
  /** Filter the loaded options, e.g. income categories only. */
  filter?: (option: Record<string, unknown>) => boolean;
  required?: boolean;
  readOnly?: boolean;
  helper?: string;
  placeholder?: string;
  /** Hide the row entirely when the value is empty (display only). */
  hideWhenEmpty?: boolean;
  /** Full width instead of half. */
  wide?: boolean;
  min?: number;
  max?: number;
  step?: number;
  /** Custom read-only renderer. */
  render?: (object: Record<string, unknown>) => ReactNode;
  /** Only show this field in the form when the predicate holds. */
  visible?: (draft: Record<string, unknown>) => boolean;
}

export const INTERVAL_OPTIONS: SelectOption[] = [
  { value: 'monthly', label: 'monatlich' },
  { value: 'quarterly', label: 'vierteljährlich' },
  { value: 'semiannual', label: 'halbjährlich' },
  { value: 'yearly', label: 'jährlich' },
  { value: 'weekly', label: 'wöchentlich' },
  { value: 'biweekly', label: 'zweiwöchentlich' },
  { value: 'once', label: 'einmalig' },
];

export const DIRECTION_OPTIONS: SelectOption[] = [
  { value: 'expense', label: 'Ausgabe' },
  { value: 'income', label: 'Einnahme' },
];

export const STATE_OPTIONS: SelectOption[] = [
  { value: 'planned', label: 'Geplant' },
  { value: 'reality', label: 'Gebucht' },
];

export const ACCOUNT_KIND_OPTIONS: SelectOption[] = [
  { value: 'checking', label: 'Girokonto' },
  { value: 'savings', label: 'Sparkonto' },
  { value: 'credit', label: 'Kreditkarte' },
  { value: 'cash', label: 'Bargeld' },
  { value: 'investment', label: 'Depot' },
];

export const CATEGORY_KIND_OPTIONS: SelectOption[] = [
  { value: 'expense', label: 'Ausgabe' },
  { value: 'income', label: 'Einnahme' },
  { value: 'both', label: 'Beides' },
];

/** Build the payload a form sends: only fields the user can actually change. */
export function collectValues(
  fields: FieldDef[],
  draft: Record<string, unknown>,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  fields.forEach((field) => {
    if (field.readOnly || field.kind === 'custom') return;
    if (field.visible && !field.visible(draft)) return;
    const value = draft[field.name];
    if (value === undefined) return;
    if (field.kind === 'number' || field.kind === 'money' || field.kind === 'percent') {
      payload[field.name] = value === '' || value === null ? null : value;
      return;
    }
    if (field.kind === 'reference' || field.kind === 'select') {
      payload[field.name] = value === '' ? null : value;
      return;
    }
    if (field.kind === 'date') {
      payload[field.name] = value === '' ? null : value;
      return;
    }
    payload[field.name] = value;
  });
  return payload;
}
