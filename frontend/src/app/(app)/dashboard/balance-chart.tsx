'use client';

import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatMoney, formatMoneyCompact, toNumber } from '@base/lib/format';
import type { MonthPoint } from '@base/types';

interface BalanceChartProps {
  months: MonthPoint[];
  currency: string;
}

interface Point {
  label: string;
  month: string;
  income: number;
  expense: number;
  balance: number;
  isPast: boolean;
}

/**
 * Income and expenses as bars, the projected balance as a line.
 * The dashed marker is today – everything right of it is a projection.
 */
export function BalanceChart({ months, currency }: BalanceChartProps) {
  const theme = useTheme();

  const data: Point[] = months.map((month) => ({
    label: month.label,
    month: month.month,
    income: toNumber(month.income),
    expense: -toNumber(month.expense),
    balance: toNumber(month.balance),
    isPast: month.is_past,
  }));

  const current = months.find((month) => month.is_current)?.label;
  const barSize = months.length > 18 ? 6 : 8;

  return (
    <Box sx={{ width: '100%' }}>
      <Stack
        direction="row"
        justifyContent="flex-end"
        spacing={2}
        sx={{ mb: 0.75, color: 'text.secondary' }}
      >
        <LegendItem label="Einnahmen" color={theme.palette.success.main} />
        <LegendItem label="Ausgaben" color={theme.palette.error.main} />
        <LegendItem label="Saldo" color={theme.palette.primary.main} line />
      </Stack>
      <Box sx={{ height: { xs: 260, md: 290 } }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 6, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="balance-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={theme.palette.primary.main} stopOpacity={0.14} />
              <stop offset="100%" stopColor={theme.palette.primary.main} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={theme.palette.divider} vertical={false} strokeDasharray="2 4" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
            minTickGap={46}
            tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          />
          {/* Monthly flows and the cumulative balance differ by an order of
              magnitude, so they get their own scales – otherwise the bars are
              a flat line next to the balance curve. */}
          <YAxis
            yAxisId="flow"
            tickLine={false}
            axisLine={false}
            width={68}
            tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
            tickFormatter={(value) => formatMoneyCompact(value, currency)}
          />
          <YAxis
            yAxisId="balance"
            orientation="right"
            tickLine={false}
            axisLine={false}
            width={68}
            tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
            tickFormatter={(value) => formatMoneyCompact(value, currency)}
          />
          <Tooltip
            cursor={{ fill: theme.palette.action.hover }}
            content={<ChartTooltip currency={currency} />}
          />

          {current ? (
            <ReferenceLine
              yAxisId="flow"
              x={current}
              stroke={theme.palette.text.secondary}
              strokeDasharray="4 4"
              label={{
                value: 'heute',
                position: 'insideTopLeft',
                fontSize: 11,
                fill: theme.palette.text.secondary,
              }}
            />
          ) : null}
          <ReferenceLine yAxisId="flow" y={0} stroke={theme.palette.divider} />

          {/* Animation is off everywhere: a chart rendered in a background tab
              never finishes its entry animation and would stay blank. */}
          <Bar
            yAxisId="flow" dataKey="income" fill={theme.palette.success.main}
            radius={[2, 2, 0, 0]} barSize={barSize} fillOpacity={0.84}
            isAnimationActive={false}
          />
          <Bar
            yAxisId="flow" dataKey="expense" fill={theme.palette.error.main}
            radius={[0, 0, 2, 2]} barSize={barSize} fillOpacity={0.84}
            isAnimationActive={false}
          />
          <Area
            yAxisId="balance"
            type="monotone"
            dataKey="balance"
            stroke={theme.palette.primary.main}
            strokeWidth={2.25}
            fill="url(#balance-fill)"
            dot={false}
            isAnimationActive={false}
          />
          </ComposedChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
}

function LegendItem({ label, color, line = false }: { label: string; color: string; line?: boolean }) {
  return (
    <Stack direction="row" spacing={0.75} alignItems="center">
      <Box
        sx={{
          width: line ? 14 : 7,
          height: line ? 2 : 7,
          borderRadius: 2,
          bgcolor: color,
        }}
      />
      <Typography variant="caption">{label}</Typography>
    </Stack>
  );
}

interface TooltipProps {
  active?: boolean;
  payload?: { payload: Point }[];
  currency: string;
}

function ChartTooltip({ active, payload, currency }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <Paper
      variant="outlined"
      sx={{ p: 1.25, minWidth: 176, borderRadius: 2, boxShadow: '0 8px 24px rgba(12,18,28,.10)' }}
    >
      <Typography variant="caption" color="text.secondary">{point.label}</Typography>
      <Stack spacing={0.25} sx={{ mt: 0.5 }}>
        <Row label="Einnahmen" value={formatMoney(point.income, currency)} color="success.main" />
        <Row label="Ausgaben" value={formatMoney(point.expense, currency)} color="error.main" />
        <Row label="Saldo" value={formatMoney(point.balance, currency)} />
      </Stack>
    </Paper>
  );
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Stack direction="row" justifyContent="space-between" spacing={2}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="caption" className="tabular" color={color} sx={{ fontWeight: 500 }}>
        {value}
      </Typography>
    </Stack>
  );
}
