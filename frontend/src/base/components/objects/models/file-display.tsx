'use client';

import DownloadIcon from '@mui/icons-material/Download';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectFields } from '@base/components/objects/object-fields';
import type { FieldDef } from '@base/components/objects/fields';
import { formatBytes, formatDateTime } from '@base/lib/format';
import type { FileObject } from '@base/types';

const STATUS: Record<string, { label: string; color: 'default' | 'info' | 'success' | 'error' }> = {
  pending: { label: 'Wartet', color: 'default' },
  processing: { label: 'Läuft', color: 'info' },
  ready: { label: 'Bereit', color: 'info' },
  completed: { label: 'Fertig', color: 'default' },
  failed: { label: 'Fehler', color: 'default' },
};

export const fileFields: FieldDef[] = [
  { name: 'original_name', label: 'Dateiname', kind: 'text' },
  { name: 'size', label: 'Größe', kind: 'number', render: (o) => formatBytes(Number(o.size)) },
  { name: 'account_name', label: 'Konto', kind: 'text', hideWhenEmpty: true },
  { name: 'content_type', label: 'Typ', kind: 'text', hideWhenEmpty: true },
  {
    name: 'processed_at', label: 'Verarbeitet', kind: 'text',
    render: (o) => formatDateTime(o.processed_at as string),
  },
  { name: 'notes', label: 'Notiz', kind: 'textarea', wide: true, hideWhenEmpty: true },
];

export function FileDisplay({ object }: { object: FileObject }) {
  const status = STATUS[object.status] ?? STATUS.pending;
  const stats = object.stats as Record<string, number | string | undefined>;

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip size="small" color={status.color} label={status.label} />
        <Typography variant="body2" color="text.secondary">{object.original_name}</Typography>
      </Stack>

      {object.status === 'processing' ? <LinearProgress /> : null}

      {object.error_message ? <Alert severity="error">{object.error_message}</Alert> : null}

      {['transaction_import', 'backup_import'].includes(object.purpose) && Object.keys(stats || {}).length > 0 ? (
        <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap>
          {[
            ['Importiert', stats.imported],
            ['Duplikate', stats.duplicates],
            ['Kategorisiert', stats.classified],
            ['Abgeglichen', stats.matched],
            ['Übersprungen', stats.rows_skipped],
          ]
            .filter(([, value]) => value !== undefined)
            .map(([label, value]) => (
              <Stack key={String(label)}>
                <Typography variant="h3" className="tabular">{String(value)}</Typography>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </Stack>
            ))}
        </Stack>
      ) : null}

      <ObjectFields object={object} fields={fileFields} />

      {object.download_url ? (
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          href={object.download_url}
          target="_blank"
          rel="noopener"
          sx={{ alignSelf: 'flex-start' }}
        >
          Herunterladen
        </Button>
      ) : null}
    </Stack>
  );
}
