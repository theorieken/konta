'use client';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import { useRouter } from 'next/navigation';
import { use, useState } from 'react';

import { ConfirmDialog } from '@base/components/confirm-dialog';
import { Loading } from '@base/components/loading';
import { ObjectDisplay } from '@base/components/objects/object-display';
import { ObjectForm } from '@base/components/objects/object-form';
import { modelFor } from '@base/components/objects/registry';
import { PageHeader } from '@base/components/page-header';
import { Section } from '@base/components/section';
import { useDeleteObjectMutation, useObjectQuery } from '@base/store/api';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';

/**
 * `/objects/{db_table}-{uuid}` – the full page version of the object drawer.
 * Same components, more room; this is where "maximise" lands.
 */
export default function ObjectPage({ params }: { params: Promise<{ reference: string }> }) {
  const { reference } = use(params);
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const { data, isLoading, isError } = useObjectQuery(reference);
  const [deleteObject, { isLoading: deleting }] = useDeleteObjectMutation();

  const entry = modelFor(data?._meta?.db_table);

  const remove = async () => {
    setConfirming(false);
    try {
      await deleteObject(reference).unwrap();
      dispatch(pushToast(`${entry?.label ?? 'Objekt'} gelöscht.`, 'success'));
      router.back();
    } catch {
      dispatch(pushToast('Löschen nicht möglich.', 'error'));
    }
  };

  if (isLoading) return <Loading height={320} />;
  if (isError || !data) {
    return (
      <Stack spacing={2}>
        <Alert severity="error">Dieses Objekt gibt es nicht (mehr).</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => router.push('/dashboard')}>
          Zum Dashboard
        </Button>
      </Stack>
    );
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 860 }}>
      <PageHeader
        title={data._meta.name}
        subtitle={entry?.label ?? data._meta.verbose_name}
        actions={
          <>
            <Button size="small" color="inherit" startIcon={<ArrowBackIcon />} onClick={() => router.back()}>
              Zurück
            </Button>
            {entry?.editable ? (
              <Button
                size="small"
                variant={editing ? 'contained' : 'outlined'}
                startIcon={<EditIcon />}
                onClick={() => setEditing((value) => !value)}
              >
                Bearbeiten
              </Button>
            ) : null}
            <Button
              size="small"
              color="inherit"
              startIcon={<DeleteOutlineIcon />}
              disabled={deleting}
              onClick={() => setConfirming(true)}
            >
              Löschen
            </Button>
          </>
        }
      />

      <Section>
        {editing ? (
          <ObjectForm
            object={data}
            onSaved={() => setEditing(false)}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <ObjectDisplay object={data} />
        )}
      </Section>

      <ConfirmDialog
        open={confirming}
        title={`${entry?.label ?? 'Objekt'} löschen?`}
        message={`„${data._meta.name}“ wird in den Papierkorb verschoben.`}
        onConfirm={remove}
        onCancel={() => setConfirming(false)}
      />
    </Stack>
  );
}
