'use client';

import Link from '@mui/material/Link';

import { useObjectDrawer } from '@base/hooks/use-object-drawer';

interface ObjectChipProps {
  reference?: string | null;
  label?: string;
}

/** A reference the user can click to open the object drawer. */
export function ObjectChip({ reference, label }: ObjectChipProps) {
  const { open } = useObjectDrawer();
  if (!reference) return <>–</>;
  return (
    <Link
      component="button"
      type="button"
      underline="hover"
      color="inherit"
      onClick={(event) => {
        event.stopPropagation();
        open(reference);
      }}
      sx={{ font: 'inherit', textAlign: 'left', cursor: 'pointer' }}
    >
      {label || reference}
    </Link>
  );
}
