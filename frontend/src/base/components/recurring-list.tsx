'use client';

import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { CategoryInline } from '@base/components/category-chip';
import { EmptyState } from '@base/components/empty-state';
import { ListSkeleton } from '@base/components/loading';
import { Money } from '@base/components/money';
import { useObjectDrawer } from '@base/hooks/use-object-drawer';
import { formatDate } from '@base/lib/format';
import type { Contract, Job, Loan } from '@base/types';

const INTERVAL_LABEL: Record<string, string> = {
  weekly: 'wöchentlich',
  biweekly: '2-wöchentlich',
  monthly: 'monatlich',
  quarterly: 'quartalsweise',
  semiannual: 'halbjährlich',
  yearly: 'jährlich',
  once: 'einmalig',
};

type Recurring = Contract | Loan | Job;

interface RecurringListProps {
  rows: Recurring[];
  loading?: boolean;
  emptyTitle: string;
  emptyHint?: string;
  /** Which amount to show – differs per model. */
  amountOf: (row: Recurring) => string;
  amountHint?: string;
}

/** Compact list for contracts, loans and incomes – one row per source. */
export function RecurringList({
  rows, loading = false, emptyTitle, emptyHint, amountOf, amountHint,
}: RecurringListProps) {
  const { open } = useObjectDrawer();

  if (loading) return <ListSkeleton rows={4} />;
  if (rows.length === 0) return <EmptyState title={emptyTitle} hint={emptyHint} />;

  return (
    <Stack divider={<Box sx={{ borderBottom: 1, borderColor: 'divider' }} />}>
      {rows.map((row) => (
        <Stack
          key={row.id}
          direction="row"
          alignItems="center"
          spacing={2}
          onClick={() => open(row._meta.object_reference)}
          sx={{ py: 1.25, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' }, px: 1, mx: -1 }}
        >
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Stack direction="row" spacing={0.75} alignItems="center" sx={{ minWidth: 0 }}>
              <Typography variant="body2" noWrap>{row.name}</Typography>
              {!row.is_active ? (
                <Chip size="small" variant="outlined" label="Pausiert" />
              ) : null}
            </Stack>
            <Typography variant="caption" color="text.secondary" noWrap>
              {INTERVAL_LABEL[row.interval] ?? row.interval}
              {row.next_due_date ? ` · nächste ${formatDate(row.next_due_date)}` : ''}
            </Typography>
          </Box>

          <Box sx={{ width: 170, display: { xs: 'none', sm: 'block' } }}>
            <CategoryInline category={row.category_detail} />
          </Box>

          <Stack alignItems="flex-end" sx={{ minWidth: 110 }}>
            <Money value={amountOf(row)} />
            {amountHint ? (
              <Typography variant="caption" color="text.disabled">{amountHint}</Typography>
            ) : null}
          </Stack>
        </Stack>
      ))}
    </Stack>
  );
}
