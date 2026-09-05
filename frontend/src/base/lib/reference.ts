/**
 * Object references: `{db_table}-{uuid}`.
 *
 * Table names contain underscores and UUIDs contain dashes, so we anchor on
 * the fixed 36 character UUID at the end – exactly like `base/registry.py`
 * does on the backend.
 */

const UUID_LENGTH = 36;

export interface ParsedReference {
  dbTable: string;
  uuid: string;
}

export function parseReference(reference: string): ParsedReference | null {
  const value = (reference || '').trim();
  if (value.length < UUID_LENGTH + 2) return null;
  if (value[value.length - UUID_LENGTH - 1] !== '-') return null;
  const uuid = value.slice(-UUID_LENGTH);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(uuid)) return null;
  return { dbTable: value.slice(0, -(UUID_LENGTH + 1)), uuid };
}

export function buildReference(dbTable: string, uuid: string): string {
  return `${dbTable}-${uuid}`;
}

export function referenceTable(reference: string): string {
  return parseReference(reference)?.dbTable ?? '';
}

export function objectPath(reference: string): string {
  return `/objects/${reference}`;
}
