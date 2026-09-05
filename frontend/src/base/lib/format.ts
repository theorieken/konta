/** Formatting helpers – German locale everywhere. */

const LOCALE = 'de-DE';

export function toNumber(value: unknown): number {
  if (value === null || value === undefined || value === '') return 0;
  const parsed = typeof value === 'number' ? value : Number(String(value).replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatMoney(value: unknown, currency = 'EUR', options?: {
  signDisplay?: 'auto' | 'always' | 'never';
  compact?: boolean;
}): string {
  return new Intl.NumberFormat(LOCALE, {
    style: 'currency',
    currency,
    signDisplay: options?.signDisplay ?? 'auto',
    notation: options?.compact ? 'compact' : 'standard',
    maximumFractionDigits: options?.compact ? 1 : 2,
    minimumFractionDigits: options?.compact ? 0 : 2,
  }).format(toNumber(value));
}

/** Short form for chart axes: 1.234 € -> "1,2k €". */
export function formatMoneyCompact(value: unknown, currency = 'EUR'): string {
  return formatMoney(value, currency, { compact: true });
}

export function formatNumber(value: unknown, digits = 0): string {
  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(toNumber(value));
}

export function formatPercent(value: unknown, digits = 0): string {
  return `${formatNumber(value, digits)} %`;
}

export function formatDate(value?: string | null, style: 'short' | 'long' | 'month' = 'short'): string {
  if (!value) return '–';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '–';
  if (style === 'month') {
    return new Intl.DateTimeFormat(LOCALE, { month: 'long', year: 'numeric' }).format(date);
  }
  if (style === 'long') {
    return new Intl.DateTimeFormat(LOCALE, { dateStyle: 'long' }).format(date);
  }
  return new Intl.DateTimeFormat(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric' })
    .format(date);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '–';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '–';
  return new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

/** "vor 3 Tagen" – used where an exact timestamp would be noise. */
export function formatRelative(value?: string | null): string {
  if (!value) return '–';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '–';
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });
  const steps: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000], ['month', 2592000], ['week', 604800],
    ['day', 86400], ['hour', 3600], ['minute', 60],
  ];
  for (const [unit, size] of steps) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(seconds, 'second');
}

const MONTH_SHORT = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
  'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];

/** "2028-07" -> "Jul 28" – the same labels the dashboard chart uses. */
export function formatMonthKey(value?: string | null): string {
  if (!value) return '–';
  const [year, month] = value.split('-');
  const index = Number(month) - 1;
  if (!year || Number.isNaN(index) || index < 0 || index > 11) return value;
  return `${MONTH_SHORT[index]} ${year.slice(2)}`;
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${formatNumber(bytes / 1024 ** index, index === 0 ? 0 : 1)} ${units[index]}`;
}

/** ISO date (yyyy-mm-dd) for <input type="date"> and API queries. */
export function isoDate(date: Date): string {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

export function today(): string {
  return isoDate(new Date());
}

export function startOfMonth(date = new Date()): string {
  return isoDate(new Date(date.getFullYear(), date.getMonth(), 1));
}

export function addMonths(iso: string, months: number): string {
  const date = new Date(iso);
  return isoDate(new Date(date.getFullYear(), date.getMonth() + months, date.getDate()));
}

export function endOfMonth(iso: string): string {
  const date = new Date(iso);
  return isoDate(new Date(date.getFullYear(), date.getMonth() + 1, 0));
}

export function truncate(value: string, length = 60): string {
  if (!value) return '';
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}
