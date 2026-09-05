'use client';

import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { Money } from '@base/components/money';
import { CategoryIcon } from '@base/lib/icons';
import { formatPercent, toNumber } from '@base/lib/format';
import type { CategoryShare } from '@base/types';

interface CategoryBreakdownProps {
  rows: CategoryShare[];
  currency: string;
  limit?: number;
  onSelect?: (categoryId: string) => void;
}

/** Ranked list with a share bar – the top expenses view of the dashboard. */
export function CategoryBreakdown({
  rows, currency, limit = 8, onSelect,
}: CategoryBreakdownProps) {
  const visible = rows.slice(0, limit);
  if (visible.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Für diesen Zeitraum gibt es noch nichts zu zeigen.
      </Typography>
    );
  }

  const max = Math.max(...visible.map((row) => toNumber(row.total)), 1);

  return (
    <Stack spacing={1.75}>
      {visible.map((row) => {
        const total = toNumber(row.total);
        return (
          <Box
            key={row.category.id}
            onClick={onSelect ? () => onSelect(row.category.id) : undefined}
            sx={{
              cursor: onSelect ? 'pointer' : 'default',
              '&:hover .bar': onSelect ? { opacity: 0.85 } : undefined,
            }}
          >
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
              <CategoryIcon
                name={row.category.icon}
                sx={{ fontSize: 18, color: 'text.primary' }}
              />
              <Typography variant="body2" noWrap sx={{ flexGrow: 1, minWidth: 0 }}>
                {row.category.name}
              </Typography>
              <Typography variant="caption" color="text.secondary" className="tabular">
                {formatPercent(row.share, toNumber(row.share) < 10 ? 1 : 0)}
              </Typography>
              <Money value={total} currency={currency} colored={false} variant="body2" />
            </Stack>
            <LinearProgress
              className="bar"
              variant="determinate"
              value={(total / max) * 100}
              sx={{
                height: 4,
                borderRadius: 2,
                bgcolor: 'action.hover',
                '& .MuiLinearProgress-bar': {
                  bgcolor: row.category.color || 'primary.main',
                  borderRadius: 2,
                },
              }}
            />
          </Box>
        );
      })}
    </Stack>
  );
}
