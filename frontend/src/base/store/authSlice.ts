import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { getToken, setToken } from '@base/api/client';
import type { User } from '@base/types';

interface AuthState {
  token: string | null;
  user: User | null;
  /** Null while `/auth/status/` has not answered yet. */
  needsOnboarding: boolean | null;
  ready: boolean;
}

const initialState: AuthState = {
  token: null,
  user: null,
  needsOnboarding: null,
  ready: false,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    /** Reads the token from localStorage once the app runs in the browser. */
    hydrate(state) {
      state.token = getToken();
      state.ready = true;
    },
    signedIn(state, action: PayloadAction<{ token: string; user: User }>) {
      state.token = action.payload.token;
      state.user = action.payload.user;
      state.needsOnboarding = false;
      setToken(action.payload.token);
    },
    signedOut(state) {
      state.token = null;
      state.user = null;
      setToken(null);
    },
    setUser(state, action: PayloadAction<User | null>) {
      state.user = action.payload;
    },
    setNeedsOnboarding(state, action: PayloadAction<boolean>) {
      state.needsOnboarding = action.payload;
    },
  },
});

export const { hydrate, signedIn, signedOut, setUser, setNeedsOnboarding } = authSlice.actions;
export default authSlice.reducer;
