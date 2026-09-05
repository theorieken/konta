'use client';

import Box from '@mui/material/Box';
import Typography, { type TypographyProps } from '@mui/material/Typography';

import { formatMoney, toNumber } from '@base/lib/format';
import { amountColor } from '@base/lib/theme';

interface MoneyProps extends Omit<TypographyProps, 'children' | 'color'> {
  value: unknown;
  currency?: string;
  /** Colour income green and expenses red. Off for neutral totals. */
  colored?: boolean;
  signDisplay?: 'auto' | 'always' | 'never';
  compact?: boolean;
}

/** The only component that renders an amount – keeps colour and format consistent. */
export function Money({
  value,
  currency = 'EUR',
  colored = true,
  signDisplay = 'auto',
  compact = false,
  sx,
  ...props
}: MoneyProps) {
  const numeric = toNumber(value);
  return (
    <Typography
      component="span"
      className="tabular"
      color={colored ? amountColor(numeric) : undefined}
      sx={{ fontWeight: 500, whiteSpace: 'nowrap', ...sx }}
      {...props}
    >
      {formatMoney(numeric, currency, { signDisplay, compact })}
    </Typography>
  );
}

/** Big number for KPI tiles. */
export function MoneyLarge({ value, currency = 'EUR', colored = false }: MoneyProps) {
  return (
    <Box>
      <Money
        value={value}
        currency={currency}
        colored={colored}
        variant="h2"
        sx={{ fontWeight: 600, letterSpacing: '-0.02em' }}
      />
    </Box>
  );
}
