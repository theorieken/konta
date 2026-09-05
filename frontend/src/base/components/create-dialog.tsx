'use client';

import CloseIcon from '@mui/icons-material/Close';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { ObjectForm } from '@base/components/objects/object-form';
import { modelFor } from '@base/components/objects/registry';
import type { BaseObject } from '@base/types';

interface CreateDialogProps {
  open: boolean;
  dbTable: string;
  object?: BaseObject | null;
  defaults?: Record<string, unknown>;
  onClose: () => void;
}

/** Modal wrapper around a model form – used by every "+" button. */
export function CreateDialog({
  open, dbTable, object, defaults, onClose,
}: CreateDialogProps) {
  const entry = modelFor(dbTable);
  const title = object ? `${entry?.label} bearbeiten` : `Neue${entry?.label === 'Transaktion' ? '' : 'r'} ${entry?.label}`;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ px: 3, pt: 2.5, pb: 1 }}
      >
        <Typography variant="h3">{title}</Typography>
        <IconButton size="small" onClick={onClose}><CloseIcon fontSize="small" /></IconButton>
      </Stack>
      <DialogContent sx={{ pt: 1 }}>
        <ObjectForm
          dbTable={dbTable}
          object={object}
          defaults={defaults}
          onSaved={onClose}
          onCancel={onClose}
        />
      </DialogContent>
    </Dialog>
  );
}
