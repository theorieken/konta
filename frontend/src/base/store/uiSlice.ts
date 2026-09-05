import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { addMonths, endOfMonth, startOfMonth } from '@base/lib/format';

export interface Toast {
  id: number;
  message: string;
  severity: 'success' | 'info' | 'warning' | 'error';
}

interface UiState {
  /** Object reference currently shown in the right hand drawer. */
  drawerReference: string | null;
  /** Stack of previously opened references so "back" works inside the drawer. */
  drawerHistory: string[];
  sidebarOpen: boolean;
  themeMode: 'light' | 'dark' | 'system';
  dateFrom: string;
  dateUntil: string;
  toasts: Toast[];
  liveConnected: boolean;
}

const initialState: UiState = {
  drawerReference: null,
  drawerHistory: [],
  sidebarOpen: false,
  themeMode: 'system',
  dateFrom: startOfMonth(),
  dateUntil: endOfMonth(addMonths(startOfMonth(), 23)),
  toasts: [],
  liveConnected: false,
};

let toastId = 0;

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    openObject(state, action: PayloadAction<string>) {
      if (state.drawerReference && state.drawerReference !== action.payload) {
        state.drawerHistory.push(state.drawerReference);
      }
      state.drawerReference = action.payload;
    },
    closeObject(state) {
      state.drawerReference = null;
      state.drawerHistory = [];
    },
    drawerBack(state) {
      state.drawerReference = state.drawerHistory.pop() ?? null;
    },
    toggleSidebar(state, action: PayloadAction<boolean | undefined>) {
      state.sidebarOpen = action.payload ?? !state.sidebarOpen;
    },
    setThemeMode(state, action: PayloadAction<'light' | 'dark' | 'system'>) {
      state.themeMode = action.payload;
    },
    setRange(state, action: PayloadAction<{ from?: string; until?: string }>) {
      if (action.payload.from) state.dateFrom = action.payload.from;
      if (action.payload.until) state.dateUntil = action.payload.until;
    },
    pushToast: {
      reducer(state, action: PayloadAction<Toast>) {
        const duplicate = state.toasts.some(
          (toast) => toast.message === action.payload.message &&
            toast.severity === action.payload.severity,
        );
        if (duplicate) return;
        state.toasts.push(action.payload);
        if (state.toasts.length > 3) state.toasts.shift();
      },
      prepare(message: string, severity: Toast['severity'] = 'info') {
        toastId += 1;
        return { payload: { id: toastId, message, severity } };
      },
    },
    dismissToast(state, action: PayloadAction<number>) {
      state.toasts = state.toasts.filter((toast) => toast.id !== action.payload);
    },
    setLiveConnected(state, action: PayloadAction<boolean>) {
      state.liveConnected = action.payload;
    },
  },
});

export const {
  openObject, closeObject, drawerBack, toggleSidebar, setThemeMode,
  setRange, pushToast, dismissToast, setLiveConnected,
} = uiSlice.actions;
export default uiSlice.reducer;
