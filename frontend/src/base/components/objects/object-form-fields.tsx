'use client';

import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import FormControlLabel from '@mui/material/FormControlLabel';
import InputAdornment from '@mui/material/InputAdornment';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import { useMemo } from 'react';

import { CategoryIcon } from '@base/lib/icons';
import type { FieldDef, OptionSource, SelectOption } from '@base/components/objects/fields';
import {
  useAccountsQuery,
  useCategoriesQuery,
  useContractsQuery,
  useJobsQuery,
  useLoansQuery,
} from '@base/store/api';

/** Loads the option lists that reference fields need. */
function useOptionSources(sources: OptionSource[]) {
  const needs = (source: OptionSource) => !sources.includes(source);

  const accounts = useAccountsQuery({ page_size: 200 }, { skip: needs('accounts') });
  const categories = useCategoriesQuery({ page_size: 300 }, { skip: needs('categories') });
  const contracts = useContractsQuery({ page_size: 200 }, { skip: needs('contracts') });
  const loans = useLoansQuery({ page_size: 200 }, { skip: needs('loans') });
  const jobs = useJobsQuery({ page_size: 200 }, { skip: needs('jobs') });

  return useMemo(() => {
    const map: Record<OptionSource, Record<string, unknown>[]> = {
      accounts: accounts.data?.results ?? [],
      categories: categories.data?.results ?? [],
      contracts: contracts.data?.results ?? [],
      loans: loans.data?.results ?? [],
      jobs: jobs.data?.results ?? [],
    };
    return map;
  }, [accounts.data, categories.data, contracts.data, loans.data, jobs.data]);
}

interface ObjectFormFieldsProps {
  fields: FieldDef[];
  draft: Record<string, unknown>;
  errors: Record<string, string>;
  onChange: (name: string, value: unknown) => void;
}

export function ObjectFormFields({ fields, draft, errors, onChange }: ObjectFormFieldsProps) {
  const sources = useMemo(
    () => Array.from(new Set(fields.map((field) => field.source).filter(Boolean))) as OptionSource[],
    [fields],
  );
  const loaded = useOptionSources(sources);

  const optionsFor = (field: FieldDef): SelectOption[] => {
    if (field.options) return field.options;
    if (!field.source) return [];
    const rows = loaded[field.source] || [];
    return rows
      .filter((row) => (field.filter ? field.filter(row) : true))
      .map((row) => ({
        value: String(row.id),
        label: String(row.name ?? ''),
        color: (row.color as string) || undefined,
        icon: (row.icon as string) || undefined,
      }));
  };

  const visible = fields.filter(
    (field) => !field.readOnly && field.kind !== 'custom' &&
      (!field.visible || field.visible(draft)),
  );

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
        columnGap: 1.75,
        rowGap: 2,
      }}
    >
      {visible.map((field) => {
        const value = draft[field.name];
        const error = errors[field.name];
        const gridColumn = field.wide ? '1 / -1' : 'auto';

        if (field.kind === 'boolean') {
          return (
            <Box key={field.name} sx={{ gridColumn, alignSelf: 'center' }}>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={Boolean(value)}
                    onChange={(event) => onChange(field.name, event.target.checked)}
                  />
                }
                label={field.label}
              />
            </Box>
          );
        }

        if (field.kind === 'select' || field.kind === 'reference') {
          const options = optionsFor(field);
          return (
            <Box key={field.name} sx={{ gridColumn }}>
              <TextField
                select
                label={field.label}
                required={field.required}
                value={value ?? ''}
                error={Boolean(error)}
                helperText={error || field.helper}
                onChange={(event) => onChange(field.name, event.target.value)}
              >
                {!field.required && <MenuItem value=""><em>–</em></MenuItem>}
                {options.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      {option.icon ? (
                        <CategoryIcon
                          name={option.icon}
                          sx={{ fontSize: 18, color: 'text.primary' }}
                        />
                      ) : null}
                      <span>{option.label}</span>
                    </Stack>
                  </MenuItem>
                ))}
              </TextField>
            </Box>
          );
        }

        if (field.kind === 'keywords') {
          const list = (value as string[]) || [];
          return (
            <Box key={field.name} sx={{ gridColumn: '1 / -1' }}>
              <TextField
                label={field.label}
                value={list.join(', ')}
                helperText={error || field.helper || 'Mit Komma trennen'}
                error={Boolean(error)}
                onChange={(event) =>
                  onChange(
                    field.name,
                    event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                  )
                }
              />
              {list.length > 0 && (
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                  {list.slice(0, 12).map((keyword) => (
                    <Chip key={keyword} size="small" variant="outlined" label={keyword} />
                  ))}
                </Stack>
              )}
            </Box>
          );
        }

        const isMoney = field.kind === 'money';
        const isNumeric = isMoney || field.kind === 'number' || field.kind === 'percent';

        return (
          <Box key={field.name} sx={{ gridColumn: field.kind === 'textarea' ? '1 / -1' : gridColumn }}>
            <TextField
              label={field.label}
              required={field.required}
              placeholder={field.placeholder}
              type={field.kind === 'date' ? 'date' : isNumeric ? 'number' : 'text'}
              multiline={field.kind === 'textarea'}
              minRows={field.kind === 'textarea' ? 3 : undefined}
              value={value ?? ''}
              error={Boolean(error)}
              helperText={error || field.helper}
              slotProps={{
                inputLabel: field.kind === 'date' ? { shrink: true } : undefined,
                htmlInput: isNumeric
                  ? { min: field.min, max: field.max, step: field.step ?? (isMoney ? 0.01 : 1) }
                  : undefined,
                input: isMoney
                  ? { endAdornment: <InputAdornment position="end">€</InputAdornment> }
                  : field.kind === 'percent'
                    ? { endAdornment: <InputAdornment position="end">%</InputAdornment> }
                    : undefined,
              }}
              onChange={(event) => onChange(field.name, event.target.value)}
            />
          </Box>
        );
      })}
    </Box>
  );
}
