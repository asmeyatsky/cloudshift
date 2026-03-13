/**
 * Auth state: token (JWT for password mode), apiKey (for searce_id when /api is behind non-IAP backend), auth_mode and deployment_mode from server.
 * Used by api.ts to send Bearer token or X-API-Key and by Layout to show login when required.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

const AUTH_STORAGE = "cloudshift-auth";

interface AuthState {
  token: string | null;
  /** API key for searce_id mode when UI calls /api without IAP (user can set in sidebar). */
  apiKey: string | null;
  authMode: string | null;
  deploymentMode: string | null;
  /** Set true when token is cleared due to 401 (show "Session expired" on login page). */
  sessionExpired: boolean;
  setToken: (token: string | null) => void;
  setApiKey: (apiKey: string | null) => void;
  setMode: (authMode: string | null, deploymentMode: string | null) => void;
  setSessionExpired: (v: boolean) => void;
  logout: () => void;
  needsLogin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      apiKey: null,
      authMode: null,
      deploymentMode: null,
      sessionExpired: false,
      setToken: (token) => set({ token }),
      setApiKey: (apiKey) => set({ apiKey }),
      setMode: (authMode, deploymentMode) => set({ authMode, deploymentMode }),
      setSessionExpired: (sessionExpired) => set({ sessionExpired }),
      logout: () => set({ token: null, sessionExpired: false }),
      needsLogin: () => {
        const { authMode, token } = get();
        return authMode === "password" && !token;
      },
    }),
    { name: AUTH_STORAGE, partialize: (s) => ({ token: s.token, apiKey: s.apiKey }) }
  )
);
