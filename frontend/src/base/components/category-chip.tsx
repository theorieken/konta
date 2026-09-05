'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { CategoryIcon } from '@base/lib/icons';
import type { ObjectRef } from '@base/types';

interface CategoryChipProps {
  category?: ObjectRef | null;
  size?: 'small' | 'medium';
  onClick?: () => void;
}

/** Category as icon + name, using the same neutral colour as the surrounding text. */
export function CategoryChip({ category, size = 'small', onClick }: CategoryChipProps) {
  if (!category) {
    return <Typography variant="body2" color="text.disabled">–</Typography>;
  }
  return (
    <Chip
      size={size}
      variant="outlined"
      onClick={onClick}
      clickable={Boolean(onClick)}
      icon={<CategoryIcon name={category.icon} sx={{ color: 'text.primary !important' }} />}
      label={category.name}
      sx={{ borderColor: 'divider', maxWidth: 200 }}
    />
  );
}

/** Compact variant for dense tables: a neutral icon plus text. */
export function CategoryInline({ category }: { category?: ObjectRef | null }) {
  if (!category) return <Typography variant="body2" color="text.disabled">–</Typography>;
  return (
    <Stack direction="row" spacing={0.75} alignItems="center" sx={{ minWidth: 0 }}>
      <CategoryIcon name={category.icon} sx={{ fontSize: 18, color: 'text.primary' }} />
      <Typography variant="body2" noWrap>{category.name}</Typography>
    </Stack>
  );
}
