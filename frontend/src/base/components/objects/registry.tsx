'use client';

import type { ComponentType } from 'react';

import { AccountDisplay } from '@base/components/objects/models/account-display';
import { AccountForm } from '@base/components/objects/models/account-form';
import { CategoryDisplay } from '@base/components/objects/models/category-display';
import { CategoryForm } from '@base/components/objects/models/category-form';
import { ContractDisplay } from '@base/components/objects/models/contract-display';
import { ContractForm } from '@base/components/objects/models/contract-form';
import { FileDisplay } from '@base/components/objects/models/file-display';
import { FileForm } from '@base/components/objects/models/file-form';
import { JobDisplay } from '@base/components/objects/models/job-display';
import { JobForm } from '@base/components/objects/models/job-form';
import { HouseholdDisplay } from '@base/components/objects/models/household-display';
import { HouseholdForm } from '@base/components/objects/models/household-form';
import { LoanDisplay } from '@base/components/objects/models/loan-display';
import { LoanForm } from '@base/components/objects/models/loan-form';
import { SettingDisplay } from '@base/components/objects/models/setting-display';
import { SettingForm } from '@base/components/objects/models/setting-form';
import { TagDisplay } from '@base/components/objects/models/tag-display';
import { TagForm } from '@base/components/objects/models/tag-form';
import { TransactionDisplay } from '@base/components/objects/models/transaction-display';
import { TransactionForm } from '@base/components/objects/models/transaction-form';
import { UserDisplay } from '@base/components/objects/models/user-display';
import { UserForm } from '@base/components/objects/models/user-form';

/* eslint-disable @typescript-eslint/no-explicit-any */
export interface ModelEntry {
  label: string;
  plural: string;
  Display: ComponentType<{ object: any }>;
  Form: ComponentType<{
    object?: any;
    defaults?: Record<string, unknown>;
    onSaved?: () => void;
    onCancel?: () => void;
  }>;
  /** REST collection – used by the delete action in the drawer. */
  endpoint: string;
  editable: boolean;
}

/**
 * db_table -> components.
 *
 * This is the frontend twin of `base/registry.py`: anything listed here can be
 * opened in the drawer, rendered on /objects/[reference] and edited in place.
 */
export const MODEL_REGISTRY: Record<string, ModelEntry> = {
  base_household: {
    label: 'Haushalt', plural: 'Haushalte',
    Display: HouseholdDisplay, Form: HouseholdForm,
    endpoint: '/households/', editable: true,
  },
  finance_transaction: {
    label: 'Transaktion', plural: 'Transaktionen',
    Display: TransactionDisplay, Form: TransactionForm,
    endpoint: '/transactions/', editable: true,
  },
  finance_contract: {
    label: 'Vertrag', plural: 'Verträge',
    Display: ContractDisplay, Form: ContractForm,
    endpoint: '/contracts/', editable: true,
  },
  finance_loan: {
    label: 'Kredit', plural: 'Kredite',
    Display: LoanDisplay, Form: LoanForm,
    endpoint: '/loans/', editable: true,
  },
  finance_job: {
    label: 'Einkommen', plural: 'Einkommen',
    Display: JobDisplay, Form: JobForm,
    endpoint: '/jobs/', editable: true,
  },
  finance_account: {
    label: 'Konto', plural: 'Konten',
    Display: AccountDisplay, Form: AccountForm,
    endpoint: '/accounts/', editable: true,
  },
  finance_category: {
    label: 'Kategorie', plural: 'Kategorien',
    Display: CategoryDisplay, Form: CategoryForm,
    endpoint: '/categories/', editable: true,
  },
  users_user: {
    label: 'Benutzer', plural: 'Benutzer',
    Display: UserDisplay, Form: UserForm,
    endpoint: '/users/', editable: true,
  },
  base_file: {
    label: 'Datei', plural: 'Dateien',
    Display: FileDisplay, Form: FileForm,
    endpoint: '/files/', editable: true,
  },
  base_tag: {
    label: 'Tag', plural: 'Tags',
    Display: TagDisplay, Form: TagForm,
    endpoint: '/tags/', editable: true,
  },
  base_setting: {
    label: 'Einstellung', plural: 'Einstellungen',
    Display: SettingDisplay, Form: SettingForm,
    endpoint: '/settings/', editable: true,
  },
};

export function modelFor(dbTable?: string | null): ModelEntry | undefined {
  return dbTable ? MODEL_REGISTRY[dbTable] : undefined;
}
