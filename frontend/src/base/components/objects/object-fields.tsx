'use client';

import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

import { CategoryInline } from '@base/components/category-chip';
import { Money } from '@base/components/money';
import { ObjectChip } from '@base/components/objects/object-chip';
import type { FieldDef } from '@base/components/objects/fields';
import { formatDate, formatNumber, formatPercent } from '@base/lib/format';
import type { BaseObject, ObjectRef } from '@base/types';

function isEmpty(value: unknown): boolean {
  return value === null || value === undefined || value === '' ||
    (Array.isArray(value) && value.length === 0);
}

function renderValue(field: FieldDef, object: BaseObject): ReactNode {
  if (field.render) return field.render(object as unknown as Record<string, unknown>);

  const value = object[field.name];

  switch (field.kind) {
    case 'money':
      return <Money value={value} colored={false} />;
    case 'number':
      return <span className="tabular">{formatNumber(value, field.step && field.step < 1 ? 2 : 0)}</span>;
    case 'percent':
      return <span className="tabular">{formatPercent(value, 2)}</span>;
    case 'date':
      return formatDate(value as string);
    case 'boolean':
      return value ? 'Ja' : 'Nein';
    case 'keywords':
      return (
        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
          {((value as string[]) || []).map((keyword) => (
            <Chip key={keyword} size="small" variant="outlined" label={keyword} />
          ))}
        </Stack>
      );
    case 'select': {
      const option = field.options?.find((entry) => entry.value === value);
      return option?.label ?? String(value ?? '–');
    }
    case 'reference': {
      const detail = object[`${field.name}_detail`] as ObjectRef | null | undefined;
      if (!detail) return '–';
      if (field.source === 'categories') return <CategoryInline category={detail} />;
      return <ObjectChip reference={detail.object_reference} label={detail.name} />;
    }
    default:
      return isEmpty(value) ? '–' : String(value);
  }
}

interface ObjectFieldsProps {
  object: BaseObject;
  fields: FieldDef[];
}

/** Read-only definition list. Empty optional fields are simply left out. */
export function ObjectFields({ object, fields }: ObjectFieldsProps) {
  const visible = fields.filter(
    (field) => !(field.hideWhenEmpty && isEmpty(object[field.name]) && !field.render),
  );

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
        columnGap: 3,
        rowGap: 2,
      }}
    >
      {visible.map((field) => (
        <Box key={field.name} sx={{ gridColumn: field.wide ? '1 / -1' : 'auto', minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.25 }}>
            {field.label}
          </Typography>
          <Typography component="div" variant="body2" sx={{ wordBreak: 'break-word' }}>
            {renderValue(field, object)}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
