'use client';

import MenuIcon from '@mui/icons-material/Menu';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import { useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';

import { useLiveEvents } from '@base/hooks/use-live-events';
import { SIDEBAR_WIDTH, Sidebar } from '@base/components/sidebar';
import { ObjectDrawer } from '@base/components/objects/object-drawer';
import { Toaster } from '@base/components/toaster';
import { useAuthStatusQuery, useLogoutMutation } from '@base/store/api';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';
import { setNeedsOnboarding, setUser, signedOut } from '@base/store/authSlice';
import { toggleSidebar } from '@base/store/uiSlice';

/**
 * Sidebar left, content right – the whole app lives in here.
 *
 * It also owns the two global concerns: the auth guard (redirect to
 * /onboarding or /login) and the live WebSocket.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const theme = useTheme();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'));

  const ready = useAppSelector((state) => state.auth.ready);
  const token = useAppSelector((state) => state.auth.token);
  const sidebarOpen = useAppSelector((state) => state.ui.sidebarOpen);

  const { data: status, error: statusError, isLoading } = useAuthStatusQuery(
    undefined,
    { skip: !ready },
  );
  const [logout] = useLogoutMutation();
  const statusUnauthorized = Boolean(
    statusError && 'status' in statusError && statusError.status === 401,
  );

  useLiveEvents(Boolean(token && status?.authenticated), status?.current_household ?? undefined);

  useEffect(() => {
    if (statusUnauthorized) {
      router.replace('/login');
      return;
    }
    if (!status) return;
    dispatch(setNeedsOnboarding(status.needs_onboarding));
    if (status.needs_onboarding) router.replace('/onboarding');
    else if (!token || !status.authenticated) router.replace('/login');
    else dispatch(setUser(status.user));
  }, [dispatch, router, status, statusUnauthorized, token]);

  const handleLogout = async () => {
    await logout().unwrap().catch(() => undefined);
    dispatch(signedOut());
    router.replace('/login');
  };

  if (!ready || isLoading || !status?.authenticated) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '100dvh' }}>
        <Typography variant="body2" color="text.secondary">Einen Moment …</Typography>
      </Box>
    );
  }

  const sidebar = (
    <Sidebar
      householdName={status.household_name || 'Haushalt'}
      householdId={status.current_household}
      onLogout={handleLogout}
    />
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100dvh', bgcolor: 'background.default' }}>
      {isDesktop ? (
        <Box
          component="nav"
          sx={{
            width: SIDEBAR_WIDTH,
            flexShrink: 0,
            borderRight: 1,
            borderColor: 'divider',
            position: 'sticky',
            top: 0,
            height: '100dvh',
            // Without this the flex container stretches the nav to the full
            // page height and `position: sticky` has nothing left to do.
            alignSelf: 'flex-start',
          }}
        >
          {sidebar}
        </Box>
      ) : (
        <Drawer
          open={sidebarOpen}
          onClose={() => dispatch(toggleSidebar(false))}
          slotProps={{ paper: { sx: { width: SIDEBAR_WIDTH } } }}
        >
          {sidebar}
        </Drawer>
      )}

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0 }}>
        {!isDesktop && (
          <AppBar
            position="sticky"
            color="inherit"
            elevation={0}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Toolbar variant="dense">
              <IconButton edge="start" onClick={() => dispatch(toggleSidebar(true))}>
                <MenuIcon />
              </IconButton>
              <Typography variant="subtitle2" sx={{ ml: 1 }}>
                {status.household_name || 'Haushalt'}
              </Typography>
            </Toolbar>
          </AppBar>
        )}
        <Box
          sx={{
            px: { xs: 2, md: 3.5 },
            py: { xs: 2.5, md: 3.25 },
            maxWidth: 1440,
            mx: 'auto',
          }}
        >
          {children}
        </Box>
      </Box>

      <ObjectDrawer />
      <Toaster />
    </Box>
  );
}
