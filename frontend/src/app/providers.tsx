'use client';

import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useEffect, useMemo, type ReactNode } from 'react';
import { Provider, useDispatch } from 'react-redux';

import { darkTheme, lightTheme } from '@base/lib/theme';
import { store } from '@base/store';
import { hydrate } from '@base/store/authSlice';
import { useAppSelector } from '@base/store/hooks';
import { setThemeMode } from '@base/store/uiSlice';

const THEME_KEY = 'finplan.theme';

function ThemedApp({ children }: { children: ReactNode }) {
  const dispatch = useDispatch();
  const mode = useAppSelector((state) => state.ui.themeMode);
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)', { noSsr: true });

  // The token only exists in the browser, so hydration happens here.
  useEffect(() => {
    dispatch(hydrate());
    try {
      const stored = window.localStorage.getItem(THEME_KEY);
      if (stored === 'light' || stored === 'dark') dispatch(setThemeMode(stored));
    } catch {
      /* ignore */
    }
  }, [dispatch]);

  useEffect(() => {
    try {
      if (mode === 'system') window.localStorage.removeItem(THEME_KEY);
      else window.localStorage.setItem(THEME_KEY, mode);
    } catch {
      /* ignore */
    }
  }, [mode]);

  const theme = useMemo(() => {
    const dark = mode === 'dark' || (mode === 'system' && prefersDark);
    return dark ? darkTheme : lightTheme;
  }, [mode, prefersDark]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <Provider store={store}>
      <ThemedApp>{children}</ThemedApp>
    </Provider>
  );
}
