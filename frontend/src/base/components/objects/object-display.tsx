'use client';

import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { TagEditor } from '@base/components/tag-editor';
import { modelFor } from '@base/components/objects/registry';
import { formatDateTime } from '@base/lib/format';
import type { BaseObject } from '@base/types';

interface ObjectDisplayProps {
  object: BaseObject;
  /** Hide tags and the audit footer – used inside compact contexts. */
  compact?: boolean;
  /** Object references are useful on full pages, but too technical for drawers. */
  showReference?: boolean;
}

/**
 * Renders any object.
 *
 * Looks up the model specific `*-display` component; unknown models fall back
 * to a raw key/value list so nothing is ever unreachable.
 */
export function ObjectDisplay({
  object, compact = false, showReference = true,
}: ObjectDisplayProps) {
  const meta = object._meta;
  const entry = modelFor(meta?.db_table);
  const Display = entry?.Display;

  return (
    <Stack spacing={3}>
      {Display ? <Display object={object} /> : <FallbackDisplay object={object} />}

      {!compact && (
        <>
          <Divider />
          <Stack spacing={1.5}>
            <TagEditor reference={meta.object_reference} tags={meta.tags} />
            <Typography variant="caption" color="text.secondary">
              Angelegt {formatDateTime(meta.created_at)}
              {meta.created_by ? ` von ${meta.created_by.name}` : ''}
              {meta.updated_at && meta.updated_at !== meta.created_at
                ? ` · zuletzt geändert ${formatDateTime(meta.updated_at)}`
                : ''}
            </Typography>
            {showReference ? (
              <Typography
                variant="caption"
                color="text.disabled"
                sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}
              >
                {meta.object_reference}
              </Typography>
            ) : null}
          </Stack>
        </>
      )}
    </Stack>
  );
}

/** Last resort renderer for a model without its own display component. */
function FallbackDisplay({ object }: { object: BaseObject }) {
  const hidden = new Set(['_meta', 'id', 'created_by']);
  const entries = Object.entries(object).filter(
    ([key, value]) =>
      !hidden.has(key) && value !== null && value !== '' && typeof value !== 'object',
  );

  return (
    <Stack spacing={2}>
      <Typography variant="h2">{object._meta.name}</Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
          columnGap: 3,
          rowGap: 2,
        }}
      >
        {entries.map(([key, value]) => (
          <Box key={key}>
            <Typography variant="caption" color="text.secondary" display="block">
              {key}
            </Typography>
            <Typography variant="body2">{String(value)}</Typography>
          </Box>
        ))}
      </Box>
    </Stack>
  );
}
