import { create } from "zustand";

import { authApi } from "../api/auth";
import { tokenStorage } from "../lib/tokenStorage";
import type {
  TokenWithRefresh,
  UserLoginRequest,
  UserMe,
  UserRegisterRequest,
} from "../types/api";

interface AuthState {
  user: UserMe | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setAuthenticatedSession: (
    tokens: TokenWithRefresh,
    user: UserMe,
  ) => void;

  login: (payload: UserLoginRequest) => Promise<void>;
  register: (payload: UserRegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,

  setAuthenticatedSession: (tokens, user) => {
    tokenStorage.setTokens(
      tokens.access_token,
      tokens.refresh_token,
    );

    set({
      user,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  login: async (payload) => {
    set({ isLoading: true });

    try {
      const tokens = await authApi.login(payload);

      

      tokenStorage.setTokens(
        tokens.access_token,
        tokens.refresh_token,
      );

      

      const user = await authApi.me();

      
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      
      tokenStorage.clear();

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      throw error;
    }
  },

  register: async (payload) => {
    set({ isLoading: true });

    try {
      const tokens = await authApi.register(payload);

      // Store the access token BEFORE calling /auth/me.
      tokenStorage.setTokens(
        tokens.access_token,
        tokens.refresh_token,
      );

      const user = await authApi.me();

      set({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      tokenStorage.clear();

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      throw error;
    }
  },

  logout: async () => {
    const refreshToken = tokenStorage.getRefreshToken();

    try {
      if (refreshToken) {
        await authApi.logout({
          refresh_token: refreshToken,
        });
      }
    } finally {
      tokenStorage.clear();

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  restoreSession: async () => {
    const accessToken = tokenStorage.getAccessToken();
    const refreshToken = tokenStorage.getRefreshToken();

    if (!accessToken && !refreshToken) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      return;
    }

    set({ isLoading: true });

    try {
      const user = await authApi.me();

      set({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      if (!refreshToken) {
        tokenStorage.clear();

        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });

        return;
      }

      try {
        const tokens = await authApi.refresh({
          refresh_token: refreshToken,
        });

        tokenStorage.setTokens(tokens.access_token);

        const user = await authApi.me();

        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch {
        tokenStorage.clear();

        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    }
  },

  clearSession: () => {
    tokenStorage.clear();

    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },
}));
