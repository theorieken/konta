'use client';

import AddIcon from '@mui/icons-material/Add';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Pagination from '@mui/material/Pagination';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import { CreateDialog } from '@base/components/create-dialog';
import { FilterBar, type TransactionFilters } from '@base/components/filter-bar';
import { PageHeader } from '@base/components/page-header';
import { RecurringList } from '@base/components/recurring-list';
import { Section } from '@base/components/section';
import { StatTile } from '@base/components/stat-tile';
import { TransactionTable } from '@base/components/transaction-table';
import { useDebounced } from '@base/hooks/use-debounced';
import {
  useContractsQuery,
  useLoansQuery,
  useTransactionSummaryQuery,
  useTransactionsQuery,
} from '@base/store/api';
import { useAppSelector } from '@base/store/hooks';
import type { Contract, Loan } from '@base/types';

const TABS = [
  { key: 'transactions', label: 'Transaktionen', table: 'finance_transaction' },
  { key: 'contracts', label: 'Verträge', table: 'finance_contract' },
  { key: 'loans', label: 'Kredite', table: 'finance_loan' },
] as const;

export default function ExpensesPage() {
  const dateFrom = useAppSelector((state) => state.ui.dateFrom);
  const dateUntil = useAppSelector((state) => state.ui.dateUntil);

  const [tab, setTab] = useState(0);
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState<string | null>(null);
  const [filters, setFilters] = useState<TransactionFilters>({
    search: '', category: '', account: '', state: '',
  });
  const search = useDebounced(filters.search);

  const query = {
    direction: 'expense',
    date_from: dateFrom,
    date_until: dateUntil,
    search: search || undefined,
    category: filters.category || undefined,
    account: filters.account || undefined,
    state: filters.state || undefined,
    page,
    page_size: 50,
    ordering: 'booking_date',
  };

  const transactions = useTransactionsQuery(query, { skip: tab !== 0 });
  const summary = useTransactionSummaryQuery(query, { skip: tab !== 0 });
  // Not skipped by tab: the KPI tiles above show these totals on every tab.
  const contracts = useContractsQuery({ page_size: 200, ordering: 'name' });
  const loans = useLoansQuery({ page_size: 200, ordering: 'name' });

  const active = TABS[tab];

  const monthlyContracts = (contracts.data?.results ?? []).reduce(
    (total, contract) => total + Math.abs(Number(contract.monthly_equivalent || 0)),
    0,
  );
  const monthlyLoans = (loans.data?.results ?? []).reduce(
    (total, loan) => (loan.is_active ? total + Math.abs(Number(loan.instalment || 0)) : total),
    0,
  );

  return (
    <Stack spacing={2.5}>
      <PageHeader
        title="Ausgaben"
        subtitle="Geplante und gebuchte Ausgaben, Verträge und Kredite."
        actions={
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setCreating(active.table)}
          >
            {active.label.replace(/en$/, '')}
          </Button>
        }
      />

      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
        }}
      >
        <StatTile label="Ausgaben im Zeitraum" value={summary.data?.expense ?? 0} />
        <StatTile label="Verträge ⌀" value={monthlyContracts} hint="pro Monat" />
        <StatTile label="Kreditraten ⌀" value={monthlyLoans} hint="pro Monat" />
        <StatTile label="Buchungen">
          <Typography variant="h2" className="tabular" sx={{ fontWeight: 600 }}>
            {summary.data?.count ?? 0}
          </Typography>
        </StatTile>
      </Box>

      <Section dense>
        <Tabs
          value={tab}
          onChange={(_event, next) => { setTab(next); setPage(1); }}
          sx={{ mb: 2, minHeight: 40 }}
        >
          {TABS.map((entry) => (
            <Tab key={entry.key} label={entry.label} sx={{ minHeight: 40 }} />
          ))}
        </Tabs>

        {tab === 0 && (
          <>
            <FilterBar value={filters} onChange={setFilters} categoryKind="expense" />
            <TransactionTable
              rows={transactions.data?.results ?? []}
              loading={transactions.isLoading}
              emptyTitle="Keine Ausgaben im Zeitraum"
              emptyHint="Lege eine Transaktion an oder importiere Kontoumsätze in den Einstellungen."
            />
            {(transactions.data?.pages ?? 1) > 1 && (
              <Stack alignItems="center" sx={{ mt: 2 }}>
                <Pagination
                  size="small"
                  count={transactions.data?.pages ?? 1}
                  page={page}
                  onChange={(_event, next) => setPage(next)}
                />
              </Stack>
            )}
          </>
        )}

        {tab === 1 && (
          <RecurringList
            rows={contracts.data?.results ?? []}
            loading={contracts.isLoading}
            emptyTitle="Noch keine Verträge"
            emptyHint="Miete, Versicherungen, Abos – alles, was regelmäßig abgebucht wird."
            amountOf={(row) => (row as Contract).monthly_equivalent}
            amountHint="pro Monat"
          />
        )}

        {tab === 2 && (
          <RecurringList
            rows={loans.data?.results ?? []}
            loading={loans.isLoading}
            emptyTitle="Keine Kredite"
            emptyHint="Erfasse geliehenes Geld, damit die Raten in der Prognose auftauchen."
            amountOf={(row) => `-${(row as Loan).instalment}`}
            amountHint="pro Rate"
          />
        )}
      </Section>

      {creating ? (
        <CreateDialog
          open
          dbTable={creating}
          defaults={creating === 'finance_transaction' ? { direction: 'expense' } : undefined}
          onClose={() => setCreating(null)}
        />
      ) : null}
    </Stack>
  );
}
