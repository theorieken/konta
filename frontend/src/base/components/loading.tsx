'use client';

import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';

export function Loading({ height = 200 }: { height?: number }) {
  return (
    <Box sx={{ display: 'grid', placeItems: 'center', minHeight: height }}>
      <CircularProgress size={22} thickness={5} />
    </Box>
  );
}

export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Stack spacing={1}>
      {Array.from({ length: rows }).map((_item, index) => (
        <Skeleton key={index} variant="rounded" height={44} />
      ))}
    </Stack>
  );
}
