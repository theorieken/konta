'use client';

import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import DownloadOutlinedIcon from '@mui/icons-material/DownloadOutlined';
import ReplayIcon from '@mui/icons-material/Replay';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import LinearProgress from '@mui/material/LinearProgress';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useEffect, useRef, useState } from 'react';

import { apiDownload, apiFetch, errorMessage } from '@base/api/client';
import { ConfirmDialog } from '@base/components/confirm-dialog';
import { EmptyState } from '@base/components/empty-state';
import { Money } from '@base/components/money';
import { PageHeader } from '@base/components/page-header';
import { Section } from '@base/components/section';
import { formatDate, formatDateTime, formatNumber } from '@base/lib/format';
import {
  api,
  useAccountsQuery,
  useCommitImportMutation,
  useDeleteFileMutation,
  useImportHistoryQuery,
  useImportPreviewQuery,
  useReprocessFileMutation,
} from '@base/store/api';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';
import type { FileObject } from '@base/types';

const STATUS: Record<string, { label: string; color: 'default' | 'info' | 'success' | 'error' }> = {
  pending: { label: 'Wartet', color: 'default' },
  processing: { label: 'Wird geprüft', color: 'info' },
  ready: { label: 'Bereit', color: 'info' },
  completed: { label: 'Importiert', color: 'default' },
  failed: { label: 'Fehler', color: 'error' },
};

function ImportResult({ file }: { file: FileObject }) {
  const dispatch = useAppDispatch();
  const isBackup = file.purpose === 'backup_import';
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [commit, { isLoading }] = useCommitImportMutation();
  const { data: preview } = useImportPreviewQuery(
    { id: file.id },
    { skip: file.status !== 'ready' || isBackup },
  );
  const stats = file.stats as Record<string, unknown>;
  const counts = (stats.counts ?? {}) as Record<string, number>;

  const startCommit = async (restore = false) => {
    try {
      await commit({ id: file.id, confirm_restore: restore }).unwrap();
      dispatch(pushToast(
        restore ? 'Wiederherstellung gestartet.' : 'Import gestartet.',
        'info',
      ));
    } catch (caught) {
      dispatch(pushToast(errorMessage(caught), 'error'));
    }
  };

  if (file.status === 'processing' || file.status === 'pending') {
    return <LinearProgress sx={{ mt: 1.5 }} />;
  }
  if (file.status === 'failed') {
    return <Alert severity="error" sx={{ mt: 1.5 }}>{file.error_message}</Alert>;
  }
  if (file.status !== 'ready') return null;

  if (isBackup) {
    return (
      <Stack spacing={1.5} sx={{ mt: 1.5 }}>
        <Alert severity="warning">
          Diese Sicherung ersetzt alle Daten im aktiven Haushalt. Benutzerkonten bleiben erhalten.
        </Alert>
        <Typography variant="body2">
          Sicherung von <strong>{String(stats.household_name ?? 'Haushalt')}</strong>
          {stats.exported_at ? ` · ${formatDateTime(String(stats.exported_at))}` : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {formatNumber(counts.transactions ?? 0)} Transaktionen ·{' '}
          {formatNumber(counts.accounts ?? 0)} Konten ·{' '}
          {formatNumber(counts.files ?? 0)} Dateien
        </Typography>
        <Box>
          <Button
            variant="contained"
            color="error"
            disabled={isLoading}
            onClick={() => setConfirmRestore(true)}
          >
            Haushalt vollständig wiederherstellen
          </Button>
        </Box>
        <ConfirmDialog
          open={confirmRestore}
          title="Haushalt vollständig wiederherstellen?"
          message="Alle Konten, Transaktionen, Planungen, Einstellungen und Dateien des aktiven Haushalts werden durch diese Sicherung ersetzt."
          confirmLabel="Vollständig wiederherstellen"
          onCancel={() => setConfirmRestore(false)}
          onConfirm={() => {
            setConfirmRestore(false);
            void startCommit(true);
          }}
        />
      </Stack>
    );
  }

  return (
    <Stack spacing={1.5} sx={{ mt: 1.5 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`${String(stats.new ?? 0)} neu`} size="small" />
        <Chip label={`${String(stats.duplicates ?? 0)} bereits vorhanden`} size="small" />
        <Chip label={`${String(stats.internal_transfers ?? 0)} Umbuchungen`} size="small" />
        {Number(stats.needs_review ?? 0) > 0 ? (
          <Chip label={`${String(stats.needs_review)} unsicher`} size="small" />
        ) : null}
      </Stack>

      {(preview?.results.length ?? 0) > 0 ? (
        <Box sx={{ overflowX: 'auto', borderTop: 1, borderBottom: 1, borderColor: 'divider' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Datum</TableCell>
                <TableCell>Gegenseite</TableCell>
                <TableCell>Kategorie</TableCell>
                <TableCell align="right">Betrag</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {preview?.results.slice(0, 8).map((row) => (
                <TableRow key={`${row.index}-${row.booking_date}`}>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatDate(row.booking_date)}</TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 360 }}>
                      {row.counterparty || row.name}
                    </Typography>
                    {row.is_internal_transfer ? (
                      <Typography variant="caption" color="text.secondary">
                        Gegenbuchung: {row.transfer_pair_name}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>{row.category_name}</TableCell>
                  <TableCell align="right"><Money value={row.amount} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : (
        <Alert severity="success">Alle Buchungen aus dieser Datei sind bereits vorhanden.</Alert>
      )}

      <Box>
        <Button variant="contained" disabled={isLoading} onClick={() => void startCommit()}>
          Transaktionen importieren
        </Button>
      </Box>
    </Stack>
  );
}

export default function ImportPage() {
  const dispatch = useAppDispatch();
  const input = useRef<HTMLInputElement>(null);
  const [account, setAccount] = useState('');
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState('');
  const { data: accounts } = useAccountsQuery({ page_size: 200, is_active: true });
  const { data: history, isLoading } = useImportHistoryQuery();
  const [reprocess] = useReprocessFileMutation();
  const [deleteFile] = useDeleteFileMutation();

  useEffect(() => {
    if (!account && accounts?.results.length) setAccount(accounts.results[0].id);
  }, [account, accounts]);

  const upload = async (file: globalThis.File) => {
    const backup = file.name.toLowerCase().endsWith('.fin');
    if (!backup && !account) {
      setError('Bitte zuerst ein Konto wählen.');
      return;
    }
    setError('');
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      if (!backup) body.append('account', account);
      const result = await apiFetch<{ file: FileObject }>('/imports/transactions/', {
        method: 'POST', formData: body,
      });
      setExpanded(result.file.id);
      dispatch(api.util.invalidateTags(['File'] as never));
      dispatch(pushToast('Datei wird geprüft.', 'info'));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setUploading(false);
      if (input.current) input.current.value = '';
    }
  };

  return (
    <Stack spacing={2.5}>
      <PageHeader
        title="Import"
        subtitle="Bankdateien prüfen, übernehmen und vollständige Sicherungen verwalten."
        actions={(
          <Button
            startIcon={<DownloadOutlinedIcon />}
            onClick={async () => {
              try {
                await apiDownload('/imports/export/');
              } catch (caught) {
                dispatch(pushToast(errorMessage(caught), 'error'));
              }
            }}
          >
            .fin exportieren
          </Button>
        )}
      />

      <Box
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files?.[0];
          if (file) void upload(file);
        }}
        onClick={() => input.current?.click()}
        sx={{
          minHeight: 230,
          border: 1,
          borderStyle: 'dashed',
          borderColor: dragging ? 'primary.main' : 'divider',
          borderRadius: 2,
          bgcolor: dragging ? 'action.hover' : 'transparent',
          display: 'grid',
          placeItems: 'center',
          cursor: 'pointer',
          transition: 'background-color .15s, border-color .15s',
        }}
      >
        <Stack spacing={1.5} alignItems="center" sx={{ px: 3, textAlign: 'center' }}>
          <CloudUploadOutlinedIcon sx={{ fontSize: 38, color: 'text.secondary' }} />
          <Box>
            <Typography variant="h6">Datei hier ablegen</Typography>
            <Typography variant="body2" color="text.secondary">
              CSV, TSV oder .fin · die Prüfung startet sofort
            </Typography>
          </Box>
          <TextField
            select
            size="small"
            label="Konto für Bankdateien"
            value={account}
            onClick={(event) => event.stopPropagation()}
            onChange={(event) => setAccount(event.target.value)}
            sx={{ minWidth: 240 }}
          >
            {(accounts?.results ?? []).map((entry) => (
              <MenuItem key={entry.id} value={entry.id}>{entry.name}</MenuItem>
            ))}
          </TextField>
          <input
            ref={input}
            hidden
            type="file"
            accept=".csv,.tsv,.txt,.fin,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
        </Stack>
      </Box>
      {uploading ? <LinearProgress /> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Section title="Bisherige Importe">
        {!isLoading && !(history?.results.length) ? (
          <EmptyState title="Noch nichts importiert" />
        ) : (
          <Stack divider={<Box sx={{ borderBottom: 1, borderColor: 'divider' }} />}>
            {(history?.results ?? []).map((file) => {
              const meta = STATUS[file.status] ?? STATUS.pending;
              const open = expanded === file.id || file.status === 'ready';
              return (
                <Box key={file.id} sx={{ py: 1.5 }}>
                  <Stack direction="row" alignItems="center" spacing={1.5}>
                    <Box
                      sx={{ flexGrow: 1, minWidth: 0, cursor: 'pointer' }}
                      onClick={() => setExpanded(open && expanded === file.id ? null : file.id)}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" noWrap sx={{ fontWeight: 550 }}>
                          {file.original_name || file.name}
                        </Typography>
                        <Chip size="small" color={meta.color} label={meta.label} />
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        {formatDateTime(file.created_at)}
                        {file.account_name ? ` · ${file.account_name}` : ' · vollständige Sicherung'}
                      </Typography>
                    </Box>
                    <Tooltip title="Erneut prüfen">
                      <IconButton size="small" onClick={() => void reprocess(file.id)}>
                        <ReplayIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {!file.stats?.imported && file.status !== 'completed' ? (
                      <Tooltip title="Datei entfernen">
                        <IconButton size="small" onClick={() => void deleteFile(file.id)}>
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    ) : null}
                  </Stack>
                  {open ? <ImportResult file={file} /> : null}
                </Box>
              );
            })}
          </Stack>
        )}
      </Section>
    </Stack>
  );
}
