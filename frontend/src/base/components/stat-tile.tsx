'use client';

import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

import { Money } from '@base/components/money';

interface StatTileProps {
  label: string;
  value?: unknown;
  /** Render something other than an amount. */
  children?: ReactNode;
  hint?: string;
  currency?: string;
  colored?: boolean;
  icon?: ReactNode;
}

/** One KPI. Label small and quiet, number large – nothing else. */
export function StatTile({
  label, value, children, hint, currency = 'EUR', colored = false, icon,
}: StatTileProps) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
        <Stack spacing={0.5}>
          <Stack direction="row" spacing={0.75} alignItems="center">
            {icon ? (
              <Stack sx={{ color: 'text.disabled', display: 'flex' }}>{icon}</Stack>
            ) : null}
            <Typography variant="caption" color="text.secondary" noWrap>{label}</Typography>
          </Stack>
          {children ?? (
            <Money
              value={value}
              currency={currency}
              colored={colored}
              variant="h2"
              sx={{ fontWeight: 600 }}
            />
          )}
          {hint ? (
            <Typography variant="caption" color="text.disabled" noWrap>{hint}</Typography>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}
