'use client';

import AddIcon from '@mui/icons-material/Add';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useState } from 'react';

import { CreateDialog } from '@base/components/create-dialog';
import { Money } from '@base/components/money';
import { Section } from '@base/components/section';
import { useObjectDrawer } from '@base/hooks/use-object-drawer';
import { CategoryIcon } from '@base/lib/icons';
import { useAccountsQuery, useCategoriesQuery } from '@base/store/api';

/** Konten und Kategorien – Stammdaten, die selten angefasst werden. */
export function MasterDataPanel() {
  const { open } = useObjectDrawer();
  const [creating, setCreating] = useState<string | null>(null);

  const { data: accounts } = useAccountsQuery({ page_size: 200, ordering: 'name' });
  const { data: categories } = useCategoriesQuery({ page_size: 300, ordering: 'name' });

  return (
    <>
      <Section
        title="Konten"
        action={
          <Button size="small" startIcon={<AddIcon />} onClick={() => setCreating('finance_account')}>
            Konto
          </Button>
        }
      >
        <Stack divider={<Box sx={{ borderBottom: 1, borderColor: 'divider' }} />}>
          {(accounts?.results ?? []).map((account) => (
            <Stack
              key={account.id}
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              spacing={2}
              onClick={() => open(account._meta.object_reference)}
              sx={{ py: 1.25, px: 1, mx: -1, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2" noWrap>{account.name}</Typography>
                  {!account.is_active ? (
                    <Chip size="small" variant="outlined" label="Inaktiv" />
                  ) : null}
                </Stack>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {[account.holder, account.bank_name].filter(Boolean).join(' · ') || '—'}
                </Typography>
              </Box>
              <Money value={account.balance_today} currency={account.currency} />
            </Stack>
          ))}
        </Stack>
      </Section>

      <Section
        title="Kategorien"
        action={
          <Button size="small" startIcon={<AddIcon />} onClick={() => setCreating('finance_category')}>
            Kategorie
          </Button>
        }
      >
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {(categories?.results ?? []).map((category) => (
            <Chip
              key={category.id}
              variant="outlined"
              onClick={() => open(category._meta.object_reference)}
              icon={
                <CategoryIcon
                  name={category.icon}
                  sx={{ color: 'text.primary !important' }}
                />
              }
              label={
                <Stack direction="row" spacing={0.75} alignItems="baseline">
                  <span>{category.name}</span>
                  <Typography variant="caption" color="text.disabled">
                    {category.transaction_count ?? 0}
                  </Typography>
                </Stack>
              }
            />
          ))}
        </Stack>
      </Section>

      {creating ? (
        <CreateDialog open dbTable={creating} onClose={() => setCreating(null)} />
      ) : null}
    </>
  );
}
