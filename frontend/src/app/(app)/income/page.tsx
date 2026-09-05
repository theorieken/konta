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
  useJobsQuery,
  useTransactionSummaryQuery,
  useTransactionsQuery,
} from '@base/store/api';
import { useAppSelector } from '@base/store/hooks';
import type { Job } from '@base/types';

const TABS = [
  { key: 'jobs', label: 'Einkommen', table: 'finance_job' },
  { key: 'transactions', label: 'Einzelne Einnahmen', table: 'finance_transaction' },
] as const;

export default function IncomePage() {
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
    direction: 'income',
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

  // Not skipped by tab: the KPI tiles above need it on both tabs.
  const jobs = useJobsQuery({ page_size: 200, ordering: 'name' });
  const transactions = useTransactionsQuery(query, { skip: tab !== 1 });
  const summary = useTransactionSummaryQuery(query);

  const active = TABS[tab];
  const monthlyNet = (jobs.data?.results ?? []).reduce(
    (total, job) => (job.is_active ? total + Number(job.net_amount || 0) : total),
    0,
  );

  return (
    <Stack spacing={2.5}>
      <PageHeader
        title="Einnahmen"
        subtitle="Regelmäßige Einkommen und einzelne Zahlungseingänge."
        actions={
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setCreating(active.table)}
          >
            {tab === 0 ? 'Einkommen' : 'Einnahme'}
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
        <StatTile label="Einnahmen im Zeitraum" value={summary.data?.income ?? 0} />
        <StatTile label="Netto ⌀" value={monthlyNet} hint="aus Einkommen, pro Monat" />
        <StatTile label="Aktive Einkommen">
          <Typography variant="h2" className="tabular" sx={{ fontWeight: 600 }}>
            {(jobs.data?.results ?? []).filter((job) => job.is_active).length}
          </Typography>
        </StatTile>
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
          <RecurringList
            rows={jobs.data?.results ?? []}
            loading={jobs.isLoading}
            emptyTitle="Noch kein Einkommen erfasst"
            emptyHint="Gehalt, Rente, Honorar – daraus entstehen die geplanten Eingänge."
            amountOf={(row) => (row as Job).net_amount}
            amountHint="netto"
          />
        )}

        {tab === 1 && (
          <>
            <FilterBar value={filters} onChange={setFilters} categoryKind="income" />
            <TransactionTable
              rows={transactions.data?.results ?? []}
              loading={transactions.isLoading}
              emptyTitle="Keine Einnahmen im Zeitraum"
              emptyHint="Einmalige Eingänge wie Bonus, Erstattung oder Geschenk landen hier."
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
      </Section>

      {creating ? (
        <CreateDialog
          open
          dbTable={creating}
          defaults={creating === 'finance_transaction' ? { direction: 'income' } : undefined}
          onClose={() => setCreating(null)}
        />
      ) : null}
    </Stack>
  );
}
