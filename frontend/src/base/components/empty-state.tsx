'use client';

import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, hint, action }: EmptyStateProps) {
  return (
    <Stack alignItems="center" spacing={1} sx={{ py: 3.5, textAlign: 'center' }}>
      {icon ? <Box sx={{ color: 'text.disabled', display: 'flex' }}>{icon}</Box> : null}
      <Typography variant="body2" color="text.secondary">{title}</Typography>
      {hint ? (
        <Typography variant="body2" color="text.disabled" sx={{ maxWidth: 380 }}>
          {hint}
        </Typography>
      ) : null}
      {action}
    </Stack>
  );
}
