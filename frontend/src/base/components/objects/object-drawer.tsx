'use client';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CloseIcon from '@mui/icons-material/Close';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useEffect, useState } from 'react';

import { ConfirmDialog } from '@base/components/confirm-dialog';
import { Loading } from '@base/components/loading';
import { ObjectDisplay } from '@base/components/objects/object-display';
import { ObjectForm } from '@base/components/objects/object-form';
import { modelFor } from '@base/components/objects/registry';
import { useObjectDrawer } from '@base/hooks/use-object-drawer';
import { useDeleteObjectMutation, useObjectQuery } from '@base/store/api';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';

/**
 * Right side drawer for any object.
 *
 * Name top left, maximise + close top right. Maximising navigates to
 * `/objects/{reference}`, which renders the exact same ObjectDisplay – so the
 * drawer is never a lesser version of the full page.
 */
export function ObjectDrawer() {
  const { reference, isOpen, canGoBack, close, back, maximize } = useObjectDrawer();
  const dispatch = useAppDispatch();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const { data, isLoading, isError } = useObjectQuery(reference as string, { skip: !reference });
  const [deleteObject, { isLoading: deleting }] = useDeleteObjectMutation();

  useEffect(() => setEditing(false), [reference]);

  const entry = modelFor(data?._meta?.db_table);
  const title = data?._meta?.name ?? 'Objekt';

  const remove = async () => {
    if (!reference) return;
    setConfirming(false);
    try {
      await deleteObject(reference).unwrap();
      dispatch(pushToast(`${entry?.label ?? 'Objekt'} gelöscht.`, 'success'));
      close();
    } catch {
      dispatch(pushToast('Löschen nicht möglich.', 'error'));
    }
  };

  return (
    <Drawer
      anchor="right"
      open={isOpen}
      onClose={close}
      slotProps={{
        paper: {
          sx: {
            width: { xs: '100%', sm: 480, md: 560 },
            borderRadius: 0,
            overflowX: 'hidden',
          },
        },
      }}
    >
      {/* Header */}
      <Stack
        direction="row"
        alignItems="center"
        spacing={0.5}
        sx={{ minHeight: 68, px: 2.5, py: 1.25, borderBottom: 1, borderColor: 'divider' }}
      >
        {canGoBack ? (
          <Tooltip title="Zurück">
            <IconButton size="small" onClick={back}><ArrowBackIcon fontSize="small" /></IconButton>
          </Tooltip>
        ) : null}

        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="subtitle1" noWrap sx={{ fontWeight: 600 }}>{title}</Typography>
          {entry ? (
            <Typography variant="caption" color="text.secondary">{entry.label}</Typography>
          ) : null}
        </Box>

        {entry?.editable && data ? (
          <Tooltip title={editing ? 'Bearbeiten beenden' : 'Bearbeiten'}>
            <IconButton size="small" onClick={() => setEditing((value) => !value)}>
              <EditIcon fontSize="small" color={editing ? 'primary' : 'inherit'} />
            </IconButton>
          </Tooltip>
        ) : null}

        {data ? (
          <Tooltip title="Löschen">
            <IconButton size="small" onClick={() => setConfirming(true)} disabled={deleting}>
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ) : null}

        <Tooltip title="Auf ganzer Seite öffnen">
          <IconButton size="small" onClick={maximize} disabled={!reference}>
            <OpenInFullIcon fontSize="small" />
          </IconButton>
        </Tooltip>

        <Tooltip title="Schließen">
          <IconButton size="small" onClick={close}><CloseIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Stack>

      {/* Body */}
      <Box sx={{ px: { xs: 2, sm: 3 }, py: 2.5, overflowY: 'auto', flexGrow: 1 }}>
        {isLoading ? <Loading /> : null}
        {isError ? <Alert severity="error">Objekt konnte nicht geladen werden.</Alert> : null}
        {data && !editing ? <ObjectDisplay object={data} showReference={false} /> : null}
        {data && editing ? (
          <ObjectForm
            object={data}
            onSaved={() => setEditing(false)}
            onCancel={() => setEditing(false)}
          />
        ) : null}
      </Box>

      <ConfirmDialog
        open={confirming}
        title={`${entry?.label ?? 'Objekt'} löschen?`}
        message={`„${title}“ wird in den Papierkorb verschoben.`}
        onConfirm={remove}
        onCancel={() => setConfirming(false)}
      />
    </Drawer>
  );
}
