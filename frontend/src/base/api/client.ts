/**
 * Low level API access.
 *
 * Authentication is token based: the token lives in localStorage and is sent
 * as `Authorization: Token <key>` on every request (and as `?token=` on the
 * WebSocket, which cannot carry headers).
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || '/ws';
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Finanzplanung';

const TOKEN_KEY = 'finplan.token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode – the session simply does not survive a reload */
  }
}

export function authHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Token ${token}` } : {};
}

/** Absolute WebSocket URL including the auth token. */
export function websocketUrl(path = '/events/'): string {
  if (typeof window === 'undefined') return '';
  const base = WS_URL.startsWith('http') || WS_URL.startsWith('ws')
    ? WS_URL
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${WS_URL}`;
  const token = getToken();
  const url = `${base.replace(/\/$/, '')}${path}`;
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** Send as multipart instead of JSON (file uploads). */
  formData?: FormData;
}

export class ApiRequestError extends Error {
  status: number;
  errors: Record<string, string[] | string>;

  constructor(message: string, status: number, errors: Record<string, string[] | string> = {}) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.errors = errors;
  }
}

function readableErrorValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(readableErrorValue).filter(Boolean).join(' ');
  if (value && typeof value === 'object') {
    return Object.values(value).map(readableErrorValue).filter(Boolean).join(' ');
  }
  return value == null ? '' : String(value);
}

/** Plain fetch wrapper for the few places that do not use RTK Query. */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, formData, headers, ...rest } = options;
  const init: RequestInit = {
    ...rest,
    headers: {
      ...(formData ? {} : { 'Content-Type': 'application/json' }),
      ...authHeader(),
      ...(headers as Record<string, string>),
    },
  };
  if (formData) init.body = formData;
  else if (body !== undefined) init.body = JSON.stringify(body);

  const response = await fetch(`${API_URL}${path}`, init);
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new ApiRequestError(
      payload?.detail || 'Die Anfrage ist fehlgeschlagen.',
      response.status,
      payload?.errors || {},
    );
  }
  return payload as T;
}

/** Authenticated file download that keeps the server-provided filename. */
export async function apiDownload(path: string): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, { headers: authHeader() });
  if (!response.ok) {
    let message = 'Der Download ist fehlgeschlagen.';
    try {
      message = (await response.json()).detail || message;
    } catch {
      /* keep the generic message */
    }
    throw new ApiRequestError(message, response.status);
  }
  const disposition = response.headers.get('content-disposition') || '';
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plain = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  const filename = encoded ? decodeURIComponent(encoded) : plain || 'haushalt.fin';
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Turns any API error into one readable German sentence. */
export function errorMessage(error: unknown): string {
  if (!error) return '';
  if (error instanceof ApiRequestError) {
    const fields = Object.entries(error.errors)
      .map(([field, value]) => `${field}: ${readableErrorValue(value)}`)
      .join(' · ');
    return fields ? `${error.message} (${fields})` : error.message;
  }
  const anyError = error as { data?: { detail?: string; errors?: Record<string, unknown> }; error?: string };
  if (anyError?.data?.detail) {
    const fields = Object.entries(anyError.data.errors || {})
      .map(([field, value]) => `${field}: ${readableErrorValue(value)}`)
      .join(' · ');
    return fields ? `${anyError.data.detail} (${fields})` : anyError.data.detail;
  }
  if (anyError?.error) return anyError.error;
  if (error instanceof Error) return error.message;
  return 'Unbekannter Fehler.';
}

/** Field level errors for form components. */
export function fieldErrors(error: unknown): Record<string, string> {
  const source =
    error instanceof ApiRequestError
      ? error.errors
      : ((error as { data?: { errors?: Record<string, string[] | string> } })?.data?.errors ?? {});
  return Object.fromEntries(
    Object.entries(source || {}).map(([field, value]) => [
      field,
      Array.isArray(value) ? value.join(' ') : String(value),
    ]),
  );
}
