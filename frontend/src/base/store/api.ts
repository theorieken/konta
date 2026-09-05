/**
 * RTK Query API – the single place where endpoints are declared.
 *
 * Tag based cache invalidation keeps the UI in sync: mutating a transaction
 * refreshes the transaction lists *and* the dashboard, so a number can never
 * be stale on one screen and fresh on another.
 */

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

import { API_URL, getToken } from '@base/api/client';
import { signedOut } from '@base/store/authSlice';
import type {
  Account,
  AuthStatus,
  BaseObject,
  Category,
  Contract,
  Dashboard,
  FileObject,
  Household,
  ImportPreview,
  Job,
  Loan,
  Paginated,
  SettingDefinition,
  Tag,
  Transaction,
  TransactionSummary,
  User,
} from '@base/types';

export type ListQuery = Record<string, string | number | boolean | undefined | null>;

function toQueryString(params: ListQuery = {}): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

const TAG_TYPES = [
  'Account', 'Category', 'Transaction', 'Contract', 'Loan', 'Job',
  'File', 'Setting', 'Tag', 'User', 'Household', 'Dashboard', 'Object',
] as const;

export type ApiTag = (typeof TAG_TYPES)[number];

/** Invalidate everything – used by login, onboarding and the generic object API. */
const ALL_TAGS: ApiTag[] = [...TAG_TYPES];

/** Requests that must also work when localStorage still contains a stale token. */
const PUBLIC_ENDPOINTS = new Set([
  'login',
  'onboarding',
  'requestPasswordReset',
  'confirmPasswordReset',
]);

const rawBaseQuery = fetchBaseQuery({
  baseUrl: API_URL,
  prepareHeaders: (headers, { endpoint }) => {
    const token = getToken();
    if (token && !PUBLIC_ENDPOINTS.has(endpoint)) {
      headers.set('Authorization', `Token ${token}`);
    }
    return headers;
  },
});

/** A rejected token must immediately become a signed-out client session. */
const baseQuery: typeof rawBaseQuery = async (args, queryApi, extraOptions) => {
  const result = await rawBaseQuery(args, queryApi, extraOptions);
  if (result.error?.status === 401) queryApi.dispatch(signedOut());
  return result;
};

export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: TAG_TYPES,
  // Money changes while you look at it – refetch when the tab regains focus.
  refetchOnFocus: true,
  refetchOnReconnect: true,
  endpoints: (builder) => ({
    /* ---------------------------------------------------------------- auth */
    authStatus: builder.query<AuthStatus, void>({
      query: () => '/auth/status/',
      providesTags: ['User'],
    }),
    login: builder.mutation<{ token: string; user: User }, { email: string; password: string }>({
      query: (body) => ({ url: '/auth/login/', method: 'POST', body }),
      invalidatesTags: ALL_TAGS,
    }),
    logout: builder.mutation<void, void>({
      query: () => ({ url: '/auth/logout/', method: 'POST' }),
    }),
    onboarding: builder.mutation<{ token: string; user: User }, Record<string, unknown>>({
      query: (body) => ({ url: '/auth/onboarding/', method: 'POST', body }),
      invalidatesTags: ALL_TAGS,
    }),
    me: builder.query<User, void>({ query: () => '/auth/me/', providesTags: ['User'] }),
    updateMe: builder.mutation<User, Partial<User>>({
      query: (body) => ({ url: '/auth/me/', method: 'PATCH', body }),
      invalidatesTags: ['User'],
    }),
    changePassword: builder.mutation<{ token: string },
      { current_password: string; new_password: string }>({
      query: (body) => ({ url: '/auth/password/', method: 'POST', body }),
    }),
    requestPasswordReset: builder.mutation<{ detail: string }, { email: string }>({
      query: (body) => ({ url: '/auth/password/reset/request/', method: 'POST', body }),
    }),
    confirmPasswordReset: builder.mutation<{ token: string; user: User },
      { token: string; new_password: string }>({
      query: (body) => ({ url: '/auth/password/reset/confirm/', method: 'POST', body }),
      invalidatesTags: ALL_TAGS,
    }),
    users: builder.query<Paginated<User>, ListQuery | void>({
      query: (params) => `/users/${toQueryString(params || {})}`,
      providesTags: ['User'],
    }),
    inviteUser: builder.mutation<User, { name: string; email: string }>({
      query: (body) => ({ url: '/users/invite/', method: 'POST', body }),
      invalidatesTags: ['User'],
    }),
    sendPasswordLink: builder.mutation<{ detail: string }, string>({
      query: (id) => ({ url: `/users/${id}/password-link/`, method: 'POST' }),
      invalidatesTags: ['User'],
    }),

    /* ----------------------------------------------------------- households */
    households: builder.query<Paginated<Household>, void>({
      query: () => '/households/?page_size=100',
      providesTags: ['Household'],
    }),
    createHousehold: builder.mutation<Household, { name: string }>({
      query: (body) => ({ url: '/households/', method: 'POST', body }),
      invalidatesTags: ['Household', 'User'],
    }),
    activateHousehold: builder.mutation<Household, string>({
      query: (id) => ({ url: `/households/${id}/activate/`, method: 'POST' }),
      invalidatesTags: ALL_TAGS,
    }),

    /* ------------------------------------------------------------ accounts */
    accounts: builder.query<Paginated<Account>, ListQuery | void>({
      query: (params) => `/accounts/${toQueryString(params || {})}`,
      providesTags: ['Account'],
    }),
    createAccount: builder.mutation<Account, Partial<Account>>({
      query: (body) => ({ url: '/accounts/', method: 'POST', body }),
      invalidatesTags: ['Account', 'Dashboard'],
    }),
    updateAccount: builder.mutation<Account, { id: string } & Partial<Account>>({
      query: ({ id, ...body }) => ({ url: `/accounts/${id}/`, method: 'PATCH', body }),
      invalidatesTags: ['Account', 'Dashboard', 'Object'],
    }),
    deleteAccount: builder.mutation<void, string>({
      query: (id) => ({ url: `/accounts/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Account', 'Dashboard'],
    }),

    /* ---------------------------------------------------------- categories */
    categories: builder.query<Paginated<Category>, ListQuery | void>({
      query: (params) => `/categories/${toQueryString({ page_size: 200, ...(params || {}) })}`,
      providesTags: ['Category'],
    }),
    createCategory: builder.mutation<Category, Partial<Category>>({
      query: (body) => ({ url: '/categories/', method: 'POST', body }),
      invalidatesTags: ['Category', 'Dashboard'],
    }),
    updateCategory: builder.mutation<Category, { id: string } & Partial<Category>>({
      query: ({ id, ...body }) => ({ url: `/categories/${id}/`, method: 'PATCH', body }),
      invalidatesTags: ['Category', 'Dashboard', 'Object'],
    }),
    deleteCategory: builder.mutation<void, string>({
      query: (id) => ({ url: `/categories/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Category'],
    }),

    /* -------------------------------------------------------- transactions */
    transactions: builder.query<Paginated<Transaction>, ListQuery | void>({
      query: (params) => `/transactions/${toQueryString(params || {})}`,
      providesTags: ['Transaction'],
    }),
    transactionSummary: builder.query<TransactionSummary, ListQuery | void>({
      query: (params) => `/transactions/summary/${toQueryString(params || {})}`,
      providesTags: ['Transaction'],
    }),
    createTransaction: builder.mutation<Transaction, Partial<Transaction> & { direction?: string }>({
      query: (body) => ({ url: '/transactions/', method: 'POST', body }),
      invalidatesTags: ['Transaction', 'Dashboard', 'Account'],
    }),
    updateTransaction: builder.mutation<Transaction,
      { id: string } & Partial<Transaction> & { direction?: string }>({
      query: ({ id, ...body }) => ({ url: `/transactions/${id}/`, method: 'PATCH', body }),
      invalidatesTags: ['Transaction', 'Dashboard', 'Account', 'Object'],
    }),
    deleteTransaction: builder.mutation<void, string>({
      query: (id) => ({ url: `/transactions/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Transaction', 'Dashboard', 'Account'],
    }),
    bulkCategory: builder.mutation<{ updated: number },
      { transactions: string[]; category: string }>({
      query: (body) => ({ url: '/transactions/bulk-category/', method: 'POST', body }),
      invalidatesTags: ['Transaction', 'Dashboard'],
    }),

    /* ------------------------------------------------ contracts/loans/jobs */
    contracts: builder.query<Paginated<Contract>, ListQuery | void>({
      query: (params) => `/contracts/${toQueryString(params || {})}`,
      providesTags: ['Contract'],
    }),
    createContract: builder.mutation<Contract, Partial<Contract>>({
      query: (body) => ({ url: '/contracts/', method: 'POST', body }),
      invalidatesTags: ['Contract', 'Transaction', 'Dashboard'],
    }),
    updateContract: builder.mutation<Contract, { id: string } & Partial<Contract>>({
      query: ({ id, ...body }) => ({ url: `/contracts/${id}/`, method: 'PATCH', body }),
      invalidatesTags: ['Contract', 'Transaction', 'Dashboard', 'Object'],
    }),
    deleteContract: builder.mutation<void, string>({
      query: (id) => ({ url: `/contracts/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Contract', 'Transaction', 'Dashboard'],
    }),

    loans: builder.query<Paginated<Loan>, ListQuery | void>({
      query: (params) => `/loans/${toQueryString(params || {})}`,
      providesTags: ['Loan'],
    }),
    createLoan: builder.mutation<Loan, Partial<Loan>>({
      query: (body) => ({ url: '/loans/', method: 'POST', body }),
      invalidatesTags: ['Loan', 'Transaction', 'Dashboard'],
    }),
    updateLoan: builder.mutation<Loan, { id: string } & Partial<Loan>>({
      query: ({ id, ...body }) => ({ url: `/loans/${id}/`, method: 'PATCH', body }),
      invalidatesTags: ['Loan', 'Transaction', 'Dashboard', 'Object'],
    }),
    deleteLoan: builder.mutation<void, string>({
      query: (id) => ({ url: `/loans/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Loan', 'Transaction', 'Dashboard'],
    }),

    jobs: builder.query<Paginated<Job>, ListQuery | void>({
      query: (params) => `/jobs/${toQueryString(params || {})}`,
      providesTags: ['Job'],
    }),
    createJob: builder.mutation<Job, Partial<Job>>({
      query: (body) => ({ url: '/jobs/', method: 'POST', body }),
      invalidatesTags: ['Job', 'Transaction', 'Dashboard'],
    }),
    updateJob: builder.mutation<Job, { id: string } & Partial<Job>>({
      query: ({ id, ...body }) => ({ url: `/jobs/${id}/`, method: 'PATCH', body }),
      invalidatesTags: ['Job', 'Transaction', 'Dashboard', 'Object'],
    }),
    deleteJob: builder.mutation<void, string>({
      query: (id) => ({ url: `/jobs/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Job', 'Transaction', 'Dashboard'],
    }),

    /* ----------------------------------------------------------- dashboard */
    dashboard: builder.query<Dashboard,
      { date_from?: string; date_until?: string; accounts?: string } | void>({
      query: (params) => `/dashboard/${toQueryString(params || {})}`,
      providesTags: ['Dashboard'],
    }),
    regeneratePlan: builder.mutation<Record<string, unknown>, { months?: number } | void>({
      query: (body) => ({ url: '/plan/regenerate/', method: 'POST', body: body || {} }),
      invalidatesTags: ['Transaction', 'Dashboard'],
    }),

    /* ------------------------------------------------------------ settings */
    settingDefinitions: builder.query<{ results: SettingDefinition[] }, void>({
      query: () => '/settings/definitions/',
      providesTags: ['Setting'],
    }),
    saveSettings: builder.mutation<{ updated: string[] }, Record<string, unknown>>({
      query: (body) => ({ url: '/settings/bulk/', method: 'PUT', body }),
      invalidatesTags: ['Setting', 'Dashboard', 'Transaction'],
    }),

    /* --------------------------------------------------------------- files */
    files: builder.query<Paginated<FileObject>, ListQuery | void>({
      query: (params) => `/files/${toQueryString(params || {})}`,
      providesTags: ['File'],
    }),
    deleteFile: builder.mutation<void, string>({
      query: (id) => ({ url: `/files/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['File'],
    }),
    reprocessFile: builder.mutation<FileObject, string>({
      query: (id) => ({ url: `/files/${id}/reprocess/`, method: 'POST' }),
      invalidatesTags: ['File', 'Transaction', 'Dashboard'],
    }),
    importStatus: builder.query<{
      files: Record<string, number>;
      needs_review: number;
      ai_configured: boolean;
      model: string;
    }, void>({
      query: () => '/imports/status/',
      providesTags: ['File', 'Transaction'],
    }),
    importHistory: builder.query<{ results: FileObject[] }, void>({
      query: () => '/imports/transactions/',
      providesTags: ['File'],
    }),
    importPreview: builder.query<ImportPreview, { id: string; page?: number }>({
      query: ({ id, page = 1 }) => `/imports/${id}/preview/?page=${page}&page_size=20`,
      providesTags: ['File'],
    }),
    commitImport: builder.mutation<
      { queued: boolean; file: FileObject },
      { id: string; confirm_restore?: boolean }
    >({
      query: ({ id, ...body }) => ({ url: `/imports/${id}/commit/`, method: 'POST', body }),
      invalidatesTags: ['File'],
    }),
    reclassify: builder.mutation<{ queued: boolean },
      { transactions?: string[]; only_review?: boolean }>({
      query: (body) => ({ url: '/imports/reclassify/', method: 'POST', body }),
      invalidatesTags: ['Transaction', 'Dashboard'],
    }),

    /* ---------------------------------------------------------------- tags */
    tags: builder.query<Paginated<Tag>, ListQuery | void>({
      query: (params) => `/tags/${toQueryString(params || {})}`,
      providesTags: ['Tag'],
    }),
    tagNames: builder.query<{ results: string[] }, void>({
      query: () => '/tags/names/',
      providesTags: ['Tag'],
    }),
    createTag: builder.mutation<Tag, { name: string; color?: string; target_reference: string }>({
      query: (body) => ({ url: '/tags/', method: 'POST', body }),
      invalidatesTags: ['Tag', 'Object'],
    }),
    deleteTag: builder.mutation<void, string>({
      query: (id) => ({ url: `/tags/${id}/`, method: 'DELETE' }),
      invalidatesTags: ['Tag', 'Object'],
    }),

    /* ------------------------------------------------- generic object API */
    object: builder.query<BaseObject, string>({
      query: (reference) => `/objects/${reference}/`,
      providesTags: (_result, _error, reference) => [{ type: 'Object' as const, id: reference }],
    }),
    updateObject: builder.mutation<BaseObject, { reference: string; body: Record<string, unknown> }>({
      query: ({ reference, body }) => ({ url: `/objects/${reference}/`, method: 'PATCH', body }),
      invalidatesTags: ALL_TAGS,
    }),
    deleteObject: builder.mutation<void, string>({
      query: (reference) => ({ url: `/objects/${reference}/`, method: 'DELETE' }),
      invalidatesTags: ALL_TAGS,
    }),
  }),
});

export const {
  useAuthStatusQuery,
  useLoginMutation,
  useLogoutMutation,
  useOnboardingMutation,
  useMeQuery,
  useUpdateMeMutation,
  useChangePasswordMutation,
  useRequestPasswordResetMutation,
  useConfirmPasswordResetMutation,
  useUsersQuery,
  useInviteUserMutation,
  useSendPasswordLinkMutation,
  useHouseholdsQuery,
  useCreateHouseholdMutation,
  useActivateHouseholdMutation,
  useAccountsQuery,
  useCreateAccountMutation,
  useUpdateAccountMutation,
  useDeleteAccountMutation,
  useCategoriesQuery,
  useCreateCategoryMutation,
  useUpdateCategoryMutation,
  useDeleteCategoryMutation,
  useTransactionsQuery,
  useTransactionSummaryQuery,
  useCreateTransactionMutation,
  useUpdateTransactionMutation,
  useDeleteTransactionMutation,
  useBulkCategoryMutation,
  useContractsQuery,
  useCreateContractMutation,
  useUpdateContractMutation,
  useDeleteContractMutation,
  useLoansQuery,
  useCreateLoanMutation,
  useUpdateLoanMutation,
  useDeleteLoanMutation,
  useJobsQuery,
  useCreateJobMutation,
  useUpdateJobMutation,
  useDeleteJobMutation,
  useDashboardQuery,
  useRegeneratePlanMutation,
  useSettingDefinitionsQuery,
  useSaveSettingsMutation,
  useFilesQuery,
  useDeleteFileMutation,
  useReprocessFileMutation,
  useImportStatusQuery,
  useImportHistoryQuery,
  useImportPreviewQuery,
  useCommitImportMutation,
  useReclassifyMutation,
  useTagsQuery,
  useTagNamesQuery,
  useCreateTagMutation,
  useDeleteTagMutation,
  useObjectQuery,
  useUpdateObjectMutation,
  useDeleteObjectMutation,
} = api;
