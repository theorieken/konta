/**
 * Shared types – the frontend mirror of the backend serializers.
 *
 * Every object carries a `_meta` block (see backend/base/serializers.py);
 * `objectReference` inside it is how the drawer, the /objects page and tags
 * address anything in the system.
 */

export type DbTable =
  | 'users_user'
  | 'finance_account'
  | 'finance_category'
  | 'finance_transaction'
  | 'finance_contract'
  | 'finance_loan'
  | 'finance_job'
  | 'base_file'
  | 'base_tag'
  | 'base_setting'
  | 'base_household';

export interface UserStub {
  id: string;
  name: string;
  object_reference: string | null;
}

export interface Tag {
  id: string;
  name: string;
  color: string;
  db_table: string;
  object_uuid: string;
  target_reference: string;
}

export interface ObjectMeta {
  id: string;
  object_reference: string;
  db_table: DbTable | string;
  model: string;
  verbose_name: string;
  verbose_name_plural: string;
  name: string;
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
  is_deleted: boolean;
  created_by: UserStub | null;
  tags: Tag[];
  api_url: string;
  frontend_url: string;
}

export interface BaseObject {
  id: string;
  name: string;
  notes: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  _meta: ObjectMeta;
  [key: string]: unknown;
}

export interface ObjectRef {
  id: string;
  name: string;
  object_reference: string;
  color?: string;
  icon?: string;
  slug?: string;
  kind?: string;
}

/* -------------------------------------------------------------------------- */
/* Domain                                                                      */
/* -------------------------------------------------------------------------- */
export type Direction = 'income' | 'expense';
export type TransactionState = 'reality' | 'planned';
export type TransactionSource = 'manual' | 'import' | 'generated';
export type Interval =
  | 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'semiannual' | 'yearly' | 'once';

export interface User extends BaseObject {
  email: string;
  first_name: string;
  last_name: string;
  color: string;
  initials: string;
  display_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_onboarded: boolean;
  last_login: string | null;
  current_household: string | null;
}

export interface Household extends BaseObject {
  member_count: number;
}

export interface Account extends BaseObject {
  holder: string;
  kind: 'checking' | 'savings' | 'credit' | 'cash' | 'investment';
  iban: string;
  bank_name: string;
  currency: string;
  color: string;
  opening_balance: string;
  opening_balance_date: string | null;
  include_in_net_worth: boolean;
  is_active: boolean;
  balance_today: string;
  transaction_count: number;
}

export interface Category extends BaseObject {
  slug: string;
  kind: 'income' | 'expense' | 'both';
  color: string;
  icon: string;
  parent: string | null;
  parent_detail: ObjectRef | null;
  keywords: string[];
  is_system: boolean;
  monthly_budget: string | null;
  transaction_count?: number;
}

export interface Transaction extends BaseObject {
  account: string;
  account_detail: ObjectRef | null;
  category: string;
  category_detail: ObjectRef | null;
  amount: string;
  booking_date: string;
  state: TransactionState;
  source: TransactionSource;
  direction: Direction;
  counterparty: string;
  purpose: string;
  contract: string | null;
  loan: string | null;
  job: string | null;
  origin_reference: string;
  recurrence_key: string;
  import_file: string | null;
  external_id: string;
  matched_transaction: string | null;
  is_matched: boolean;
  is_internal_transfer: boolean;
  transfer_pair: string | null;
  classified_by_ai: boolean;
  classification_confidence: number | null;
  classification_note: string;
  needs_review: boolean;
}

interface RecurringBase extends BaseObject {
  account: string;
  account_detail: ObjectRef | null;
  category: string;
  category_detail: ObjectRef | null;
  interval: Interval;
  interval_count: number;
  day_of_month: number;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  next_due_date: string | null;
  planned_count: number;
}

export interface Contract extends RecurringBase {
  provider: string;
  amount: string;
  contract_direction: Direction;
  contract_number: string;
  cancellation_period_days: number;
  monthly_equivalent: string;
}

export interface Loan extends RecurringBase {
  lender: string;
  principal: string;
  interest_rate: string;
  instalment: string;
  remaining_at_start: string | null;
  outstanding: string;
  paid_so_far: string;
}

export interface Job extends RecurringBase {
  employer: string;
  gross_amount: string;
  net_amount: string;
  tax_class: string;
  part_time_factor: string;
}

export interface FileObject extends BaseObject {
  file: string;
  original_name: string;
  content_type: string;
  size: number;
  purpose: 'transaction_import' | 'backup_import' | 'document' | 'other';
  status: 'pending' | 'processing' | 'ready' | 'completed' | 'failed';
  account: string | null;
  account_name: string;
  stats: Record<string, unknown>;
  error_message: string;
  processed_at: string | null;
  download_url: string;
}

export interface SettingObject extends BaseObject {
  key: string;
  value: unknown;
  value_type: 'string' | 'number' | 'boolean' | 'date' | 'json';
  is_secret: boolean;
  description: string;
  is_set: boolean;
}

export interface SettingDefinition {
  key: string;
  label: string;
  value_type: 'string' | 'number' | 'boolean' | 'date' | 'json';
  default: unknown;
  is_secret: boolean;
  description: string;
  group: string;
  choices: string[];
  value: unknown;
  is_set: boolean;
  object_reference: string | null;
}

/* -------------------------------------------------------------------------- */
/* API envelopes                                                               */
/* -------------------------------------------------------------------------- */
export interface Paginated<T> {
  count: number;
  pages: number;
  page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail: string;
  errors: Record<string, string[] | string>;
}

export interface AuthStatus {
  needs_onboarding: boolean;
  user_count: number;
  authenticated: boolean;
  user: User | null;
  household_name: string;
  current_household: string | null;
  households: Array<{ id: string; name: string }>;
  currency: string;
}

export interface ImportCandidate {
  index: number;
  name: string;
  booking_date: string;
  amount: string;
  counterparty: string;
  purpose: string;
  category: string;
  category_name: string;
  category_slug: string;
  classification_confidence: number;
  classification_note: string;
  needs_review: boolean;
  is_internal_transfer: boolean;
  transfer_pair_name?: string;
}

export interface ImportPreview {
  count: number;
  page: number;
  page_size: number;
  results: ImportCandidate[];
}

export interface MonthPoint {
  month: string;
  label: string;
  date: string;
  income: string;
  expense: string;
  net: string;
  balance: string;
  is_past: boolean;
  is_current: boolean;
}

export interface CategoryShare {
  category: ObjectRef & { slug: string; color: string; icon: string };
  total: string;
  share: string;
}

export interface AccountBalance {
  id: string;
  object_reference: string;
  name: string;
  holder: string;
  kind: string;
  color: string;
  currency: string;
  include_in_net_worth: boolean;
  balance_today: string;
  booked_balance: string;
  balance_end: string;
}

export interface Dashboard {
  range: { from: string; until: string; today: string; months: number };
  currency: string;
  kpis: Record<string, string | null>;
  months: MonthPoint[];
  expenses_by_category: CategoryShare[];
  income_by_category: CategoryShare[];
  accounts: AccountBalance[];
}

export interface TransactionSummary {
  count: number;
  income: string;
  expense: string;
  net: string;
}

/* -------------------------------------------------------------------------- */
/* WebSocket events                                                            */
/* -------------------------------------------------------------------------- */
export type LiveEvent =
  | { type: 'connection.ready'; user: string }
  | { type: 'object.changed'; action: 'created' | 'updated' | 'deleted';
      object_reference: string; db_table: string; name: string; payload: Record<string, unknown> }
  | { type: 'import.progress'; object_reference: string; status: string;
      processed: number; total: number; message: string }
  | { type: 'import.finished'; object_reference: string; imported: number;
      duplicates: number; classified?: number; matched?: number }
  | { type: 'import.analyzed'; object_reference: string; kind: string;
      new?: number; duplicates?: number; internal_transfers?: number }
  | { type: 'household.restored'; counts: Record<string, number> }
  | { type: 'plan.generated'; created: number; removed?: number }
  | { type: 'plan.matched'; checked: number; matched: number }
  | { type: 'toast'; severity: 'info' | 'success' | 'warning' | 'error'; message: string }
  | { type: 'pong' };
