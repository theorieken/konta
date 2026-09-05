'use client';

import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

interface SectionProps {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  dense?: boolean;
}

/** Outlined card with an optional quiet heading. The app's only container. */
export function Section({ title, action, children, dense = false }: SectionProps) {
  return (
    <Card>
      <CardContent sx={{ p: dense ? 1.5 : 2.25, '&:last-child': { pb: dense ? 1.5 : 2.25 } }}>
        {(title || action) && (
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: title ? 1.75 : 0 }}
          >
            {title ? <Typography variant="h3">{title}</Typography> : <span />}
            {action}
          </Stack>
        )}
        {children}
      </CardContent>
    </Card>
  );
}
