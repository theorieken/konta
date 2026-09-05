'use client';

import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Snackbar from '@mui/material/Snackbar';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { useAppDispatch, useAppSelector } from '@base/store/hooks';
import { dismissToast, type Toast } from '@base/store/uiSlice';

const ICONS: Record<Toast['severity'], typeof InfoOutlinedIcon> = {
  success: CheckCircleOutlineRoundedIcon,
  info: InfoOutlinedIcon,
  warning: WarningAmberRoundedIcon,
  error: ErrorOutlineRoundedIcon,
};

/** Compact, auto-dismissing notifications. Messages are shown one at a time. */
export function Toaster() {
  const toast = useAppSelector((state) => state.ui.toasts[0]);
  const dispatch = useAppDispatch();

  if (!toast) return null;

  const Icon = ICONS[toast.severity];
  const dismiss = () => dispatch(dismissToast(toast.id));

  return (
    <Snackbar
      key={toast.id}
      open
      autoHideDuration={toast.severity === 'error' ? 5500 : 3800}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      onClose={(_event, reason) => {
        if (reason !== 'clickaway') dismiss();
      }}
      sx={{ m: { xs: 0.5, sm: 1 }, maxWidth: { xs: 'calc(100vw - 24px)', sm: 420 } }}
    >
      <Paper
        role="status"
        variant="outlined"
        sx={{
          width: '100%',
          px: 1.5,
          py: 1,
          borderRadius: 2,
          boxShadow: '0 10px 32px rgba(12,18,28,.14)',
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <Icon sx={{ fontSize: 19, color: 'primary.main', flexShrink: 0 }} />
          <Typography variant="body2" sx={{ flexGrow: 1, lineHeight: 1.4 }}>
            {toast.message}
          </Typography>
          <IconButton size="small" aria-label="Meldung schließen" onClick={dismiss}>
            <CloseRoundedIcon sx={{ fontSize: 17 }} />
          </IconButton>
        </Stack>
      </Paper>
    </Snackbar>
  );
}
