'use client';

import { createTheme, type ThemeOptions } from '@mui/material/styles';

/**
 * A deliberately quiet theme.
 *
 * The rules the whole UI follows: one accent colour, generous whitespace,
 * hairline dividers instead of shadows, and numbers in tabular figures so
 * columns line up. Green means money in, red means money out – nothing else
 * in the app is allowed to use those two colours.
 */

export const INCOME_COLOR = '#2e7d32';
export const EXPENSE_COLOR = '#c62828';
export const PLANNED_COLOR = '#74819a';

const shared: ThemeOptions = {
  shape: { borderRadius: 8 },
  typography: {
    fontFamily:
      '"Inter", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontSize: '1.65rem', fontWeight: 650, lineHeight: 1.2, letterSpacing: '-0.025em' },
    h2: { fontSize: '1.25rem', fontWeight: 650, lineHeight: 1.25, letterSpacing: '-0.015em' },
    h3: { fontSize: '1rem', fontWeight: 650 },
    h4: { fontSize: '1rem', fontWeight: 600 },
    subtitle2: { fontSize: '0.8rem', fontWeight: 500 },
    body2: { fontSize: '0.875rem' },
    caption: { fontSize: '0.75rem' },
    button: { textTransform: 'none', fontWeight: 500 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        // Amounts, dates and IDs must align vertically in every table.
        '.tabular': { fontVariantNumeric: 'tabular-nums' },
        '::-webkit-scrollbar': { width: 8, height: 8 },
        '::-webkit-scrollbar-thumb': { borderRadius: 8, background: 'rgba(128,128,128,.24)' },
        '::-webkit-scrollbar-track': { background: 'transparent' },
      },
    },
    MuiPaper: { defaultProps: { elevation: 0 }, styleOverrides: { root: { backgroundImage: 'none' } } },
    MuiCard: {
      defaultProps: { elevation: 0, variant: 'outlined' },
      styleOverrides: { root: { borderRadius: 10 } },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          minHeight: 36,
          borderRadius: 7,
          paddingInline: 12,
          letterSpacing: '-0.005em',
        },
        contained: { boxShadow: 'none' },
        startIcon: { marginRight: 6 },
      },
    },
    MuiIconButton: {
      styleOverrides: { root: { borderRadius: 7 } },
    },
    MuiTextField: {
      defaultProps: {
        size: 'small',
        fullWidth: true,
        slotProps: { inputLabel: { shrink: true } },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          minHeight: 40,
          borderRadius: 7,
          backgroundColor: theme.palette.mode === 'light'
            ? 'rgba(255,255,255,.72)'
            : 'rgba(255,255,255,.025)',
          '& .MuiOutlinedInput-notchedOutline': { borderColor: theme.palette.divider },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.text.secondary,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderWidth: 1 },
          '&.Mui-error .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.text.primary,
          },
        }),
        input: {
          boxSizing: 'content-box',
          padding: '8.5px 14px',
        },
        multiline: { minHeight: 0, paddingBlock: 8.5 },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { fontSize: '0.875rem' },
        shrink: ({ theme }) => ({
          paddingInline: 3,
          marginLeft: -3,
          backgroundColor: theme.palette.background.paper,
        }),
      },
    },
    MuiFormHelperText: {
      styleOverrides: { root: { marginTop: 5, marginInline: 0, lineHeight: 1.35 } },
    },
    MuiSelect: { defaultProps: { size: 'small' } },
    MuiChip: { styleOverrides: { root: { borderRadius: 6, fontWeight: 500, height: 28 } } },
    MuiTooltip: { defaultProps: { arrow: true, enterDelay: 400 } },
    MuiTableCell: {
      styleOverrides: {
        root: { paddingBlock: 10 },
        head: { fontWeight: 600, fontSize: '0.75rem', letterSpacing: '0.03em',
                textTransform: 'uppercase', opacity: 0.7 },
      },
    },
    MuiListItemIcon: { styleOverrides: { root: { minWidth: 36 } } },
    MuiDialog: { styleOverrides: { paper: { borderRadius: 12 } } },
    MuiAlert: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          border: '1px solid',
          borderColor: theme.palette.divider,
          '& .MuiAlert-icon': { color: 'inherit', opacity: 0.65 },
        }),
        standardInfo: { color: 'inherit', backgroundColor: 'transparent' },
        standardWarning: { color: 'inherit', backgroundColor: 'transparent' },
        standardError: { color: 'inherit', backgroundColor: 'transparent' },
        standardSuccess: { color: 'inherit', backgroundColor: 'transparent' },
      },
    },
    MuiTabs: { styleOverrides: { indicator: { height: 2 } } },
    MuiTab: {
      styleOverrides: {
        root: { minHeight: 38, paddingInline: 12, textTransform: 'none', fontWeight: 500 },
      },
    },
  },
};

export const lightTheme = createTheme({
  ...shared,
  palette: {
    mode: 'light',
    primary: { main: '#37445f' },
    secondary: { main: '#37445f' },
    success: { main: INCOME_COLOR },
    error: { main: EXPENSE_COLOR },
    background: { default: '#f6f7f8', paper: '#ffffff' },
    divider: 'rgba(20,27,40,0.10)',
    text: { primary: '#20242c', secondary: '#667080' },
  },
});

export const darkTheme = createTheme({
  ...shared,
  palette: {
    mode: 'dark',
    primary: { main: '#aab8d4' },
    secondary: { main: '#aab8d4' },
    success: { main: '#66bb6a' },
    error: { main: '#ef5350' },
    background: { default: '#111318', paper: '#181b20' },
    divider: 'rgba(255,255,255,0.10)',
    text: { primary: '#e7e9ee', secondary: '#9aa3b2' },
  },
});

/** Colour for a signed amount – the single source of truth for money colours. */
export function amountColor(value: number): 'success.main' | 'error.main' | 'text.primary' {
  if (value > 0) return 'success.main';
  if (value < 0) return 'error.main';
  return 'text.primary';
}
