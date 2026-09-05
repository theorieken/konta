'use client';

import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ScheduleIcon from '@mui/icons-material/Schedule';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import { CategoryInline } from '@base/components/category-chip';
import { EmptyState } from '@base/components/empty-state';
import { ListSkeleton } from '@base/components/loading';
import { Money } from '@base/components/money';
import { useObjectDrawer } from '@base/hooks/use-object-drawer';
import { formatDate, truncate } from '@base/lib/format';
import type { Transaction } from '@base/types';

interface TransactionTableProps {
  rows: Transaction[];
  loading?: boolean;
  emptyTitle?: string;
  emptyHint?: string;
  showAccount?: boolean;
}

/** The one table used for transactions everywhere. Clicking a row opens the drawer. */
export function TransactionTable({
  rows,
  loading = false,
  emptyTitle = 'Keine Transaktionen',
  emptyHint,
  showAccount = true,
}: TransactionTableProps) {
  const { open } = useObjectDrawer();

  if (loading) return <ListSkeleton rows={6} />;
  if (rows.length === 0) return <EmptyState title={emptyTitle} hint={emptyHint} />;

  return (
    <Box sx={{ overflowX: 'auto' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell width={110}>Datum</TableCell>
            <TableCell>Bezeichnung</TableCell>
            <TableCell width={200}>Kategorie</TableCell>
            {showAccount ? <TableCell width={160}>Konto</TableCell> : null}
            <TableCell width={140} align="right">Betrag</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow
              key={row.id}
              hover
              onClick={() => open(row._meta.object_reference)}
              sx={{
                cursor: 'pointer',
                opacity: row.state === 'planned' ? 0.82 : 1,
                '& td': { borderColor: 'divider' },
              }}
            >
              <TableCell className="tabular">
                <Stack direction="row" spacing={0.5} alignItems="center">
                  {row.state === 'planned' ? (
                    <Tooltip title="Geplant">
                      <ScheduleIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                    </Tooltip>
                  ) : null}
                  <span>{formatDate(row.booking_date)}</span>
                </Stack>
              </TableCell>

              <TableCell sx={{ maxWidth: 320 }}>
                <Stack direction="row" spacing={0.75} alignItems="center" sx={{ minWidth: 0 }}>
                  <Typography variant="body2" noWrap>{row.name}</Typography>
                  {row.needs_review ? (
                    <Chip size="small" color="warning" variant="outlined" label="Prüfen" />
                  ) : null}
                  {row.classified_by_ai ? (
                    <Tooltip title={row.classification_note || 'Von der KI zugeordnet'}>
                      <AutoAwesomeIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                    </Tooltip>
                  ) : null}
                  {row.is_internal_transfer ? (
                    <Tooltip title="Interne Umbuchung">
                      <SwapHorizIcon sx={{ fontSize: 15, color: 'text.disabled' }} />
                    </Tooltip>
                  ) : null}
                </Stack>
                {row.counterparty ? (
                  <Typography variant="caption" color="text.secondary" noWrap display="block">
                    {truncate(row.counterparty, 48)}
                  </Typography>
                ) : null}
              </TableCell>

              <TableCell><CategoryInline category={row.category_detail} /></TableCell>

              {showAccount ? (
                <TableCell>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {row.account_detail?.name ?? '–'}
                  </Typography>
                </TableCell>
              ) : null}

              <TableCell align="right"><Money value={row.amount} /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
