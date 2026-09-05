'use client';

import AutorenewIcon from '@mui/icons-material/Autorenew';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { Loading } from '@base/components/loading';
import { Money } from '@base/components/money';
import { PageHeader } from '@base/components/page-header';
import { Section } from '@base/components/section';
import { StatTile } from '@base/components/stat-tile';
import { formatDate, formatMoney, formatMonthKey, formatPercent, toNumber } from '@base/lib/format';
import { useDashboardQuery, useRegeneratePlanMutation } from '@base/store/api';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';
import { useObjectDrawer } from '@base/hooks/use-object-drawer';

import { BalanceChart } from './balance-chart';
import { CategoryBreakdown } from './category-breakdown';
import { RangePicker } from './range-picker';

export default function DashboardPage() {
  const dispatch = useAppDispatch();
  const { open } = useObjectDrawer();
  const dateFrom = useAppSelector((state) => state.ui.dateFrom);
  const dateUntil = useAppSelector((state) => state.ui.dateUntil);

  const { data, isLoading, isFetching } = useDashboardQuery({
    date_from: dateFrom,
    date_until: dateUntil,
  });
  const [regenerate, { isLoading: regenerating }] = useRegeneratePlanMutation();

  if (isLoading || !data) return <Loading height={400} />;

  const { kpis, currency } = data;
  const goal = toNumber(kpis.savings_goal);
  const goalProgress = Math.min(toNumber(kpis.savings_goal_progress), 100);

  const rebuild = async () => {
    const result = await regenerate().unwrap().catch(() => null);
    dispatch(
      pushToast(
        result
          ? `Plan aktualisiert: ${result.created ?? 0} Transaktionen erzeugt.`
          : 'Plan konnte nicht aktualisiert werden.',
        result ? 'success' : 'error',
      ),
    );
  };

  return (
    <Stack spacing={2.5}>
      <PageHeader
        title="Dashboard"
        subtitle={`${formatDate(data.range.from)} – ${formatDate(data.range.until)} · ${data.range.months} Monate`}
        actions={
          <>
            <RangePicker />
            <Button
              size="small"
              color="inherit"
              startIcon={<AutorenewIcon />}
              disabled={regenerating}
              onClick={rebuild}
            >
              Plan
            </Button>
          </>
        }
      />

      {isFetching ? <LinearProgress sx={{ mb: -2 }} /> : null}

      {/* KPIs */}
      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: {
            xs: 'repeat(2, minmax(0, 1fr))',
            md: 'repeat(4, minmax(0, 1fr))',
          },
        }}
      >
        <StatTile
          label="Saldo heute"
          value={kpis.balance_today}
          colored
          hint={`gebucht ${formatMoney(kpis.booked_balance_today, currency)}`}
        />
        <StatTile
          label="Prognose Ende"
          value={kpis.projected_balance}
          colored
          hint={formatDate(data.range.until)}
        />
        <StatTile
          label="Einnahmen ⌀"
          value={kpis.income_monthly_avg}
          hint="pro Monat"
        />
        <StatTile
          label="Ausgaben ⌀"
          value={kpis.expense_monthly_avg}
          hint="pro Monat"
        />
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: {
            xs: 'repeat(2, minmax(0, 1fr))',
            md: 'repeat(4, minmax(0, 1fr))',
          },
        }}
      >
        <StatTile label="Überschuss ⌀" value={kpis.net_monthly_avg} colored hint="pro Monat" />
        <StatTile label="Sparquote">
          <Typography variant="h2" className="tabular" sx={{ fontWeight: 600 }}>
            {formatPercent(kpis.savings_rate, 1)}
          </Typography>
        </StatTile>
        <StatTile
          label="Tiefster Stand"
          value={kpis.lowest_balance}
          colored
          hint={kpis.lowest_balance_month ? formatMonthKey(kpis.lowest_balance_month) : undefined}
        />
        {goal > 0 ? (
          <StatTile label="Sparziel" hint={
            kpis.savings_goal_reached_month
              ? `erreicht ${formatMonthKey(kpis.savings_goal_reached_month)}`
              : 'im Zeitraum nicht erreicht'
          }>
            <Stack spacing={0.75}>
              <Money value={kpis.savings_goal} colored={false} variant="h2" sx={{ fontWeight: 600 }} />
              <LinearProgress
                variant="determinate"
                value={goalProgress}
                color={kpis.savings_goal_reached_month ? 'success' : 'primary'}
                sx={{ height: 4, borderRadius: 2 }}
              />
            </Stack>
          </StatTile>
        ) : (
          <StatTile label="Einnahmen gesamt" value={kpis.income_total} />
        )}
      </Box>

      {/* Verlauf */}
      <Section title="Verlauf">
        <BalanceChart months={data.months} currency={currency} />
      </Section>

      {/* Kategorien + Konten */}
      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: '1fr', lg: '1.4fr 1fr' },
          alignItems: 'start',
        }}
      >
        <Section title="Größte Ausgaben">
          <CategoryBreakdown rows={data.expenses_by_category} currency={currency} />
        </Section>

        <Stack spacing={2}>
          <Section title="Konten">
            <Stack spacing={1.5}>
              {data.accounts.map((account) => (
                <Stack
                  key={account.id}
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  spacing={2}
                  onClick={() => open(account.object_reference)}
                  sx={{ cursor: 'pointer', '&:hover': { opacity: 0.8 } }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body2" noWrap>{account.name}</Typography>
                    {account.holder ? (
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {account.holder}
                      </Typography>
                    ) : null}
                  </Box>
                  <Stack alignItems="flex-end">
                    <Money value={account.balance_today} currency={account.currency} />
                    <Typography variant="caption" color="text.disabled" className="tabular">
                      Ende {formatMoney(account.balance_end, account.currency)}
                    </Typography>
                  </Stack>
                </Stack>
              ))}
            </Stack>
          </Section>

          <Section title="Einnahmen nach Kategorie">
            <CategoryBreakdown
              rows={data.income_by_category}
              currency={currency}
              limit={5}
            />
          </Section>
        </Stack>
      </Box>
    </Stack>
  );
}
