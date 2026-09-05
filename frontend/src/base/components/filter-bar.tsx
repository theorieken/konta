'use client';

import SearchIcon from '@mui/icons-material/Search';
import InputAdornment from '@mui/material/InputAdornment';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';

import { useAccountsQuery, useCategoriesQuery } from '@base/store/api';

export interface TransactionFilters {
  search: string;
  category: string;
  account: string;
  state: string;
}

interface FilterBarProps {
  value: TransactionFilters;
  onChange: (next: TransactionFilters) => void;
  /** Restrict the category dropdown to income or expense categories. */
  categoryKind?: 'income' | 'expense';
}

/** Search + the three filters that actually get used. Nothing else. */
export function FilterBar({ value, onChange, categoryKind }: FilterBarProps) {
  const { data: categories } = useCategoriesQuery({ page_size: 300 });
  const { data: accounts } = useAccountsQuery({ page_size: 200 });

  const set = (patch: Partial<TransactionFilters>) => onChange({ ...value, ...patch });

  const categoryOptions = (categories?.results ?? []).filter(
    (category) => !categoryKind || category.kind === categoryKind || category.kind === 'both',
  );

  return (
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mb: 1.75 }}>
      <TextField
        placeholder="Suchen"
        value={value.search}
        onChange={(event) => set({ search: event.target.value })}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          },
        }}
      />
      <TextField
        select label="Kategorie" value={value.category} sx={{ minWidth: 180 }}
        onChange={(event) => set({ category: event.target.value })}
      >
        <MenuItem value="">Alle</MenuItem>
        {categoryOptions.map((category) => (
          <MenuItem key={category.id} value={category.id}>{category.name}</MenuItem>
        ))}
      </TextField>
      <TextField
        select label="Konto" value={value.account} sx={{ minWidth: 170 }}
        onChange={(event) => set({ account: event.target.value })}
      >
        <MenuItem value="">Alle</MenuItem>
        {(accounts?.results ?? []).map((account) => (
          <MenuItem key={account.id} value={account.id}>{account.name}</MenuItem>
        ))}
      </TextField>
      <TextField
        select label="Status" value={value.state} sx={{ minWidth: 150 }}
        onChange={(event) => set({ state: event.target.value })}
      >
        <MenuItem value="">Alle</MenuItem>
        <MenuItem value="planned">Geplant</MenuItem>
        <MenuItem value="reality">Gebucht</MenuItem>
      </TextField>
    </Stack>
  );
}
