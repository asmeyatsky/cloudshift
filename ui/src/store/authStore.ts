/**
 * Auth state: token (JWT for password mode), auth_mode and deployment_mode from server.
 * Used by api.ts to send Bearer token and by Layout to show login when required.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

const AUTH_STORAGE = "cloudshift-auth";

interface AuthState {
  token: string | null;
  authMode: string | null;
  deploymentMode: string | null;
  /** Set true when token is cleared due to 401 (show "Session expired" on login page). */
  sessionExpired: boolean;
  setToken: (token: string | null) => void;
  setMode: (authMode: string | null, deploymentMode: string | null) => void;
  setSessionExpired: (v: boolean) => void;
  logout: () => void;
  needsLogin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      authMode: null,
      deploymentMode: null,
      sessionExpired: false,
      setToken: (token) => set({ token }),
      setMode: (authMode, deploymentMode) => set({ authMode, deploymentMode }),
      setSessionExpired: (sessionExpired) => set({ sessionExpired }),
      logout: () => set({ token: null, sessionExpired: false }),
      needsLogin: () => {
        const { authMode, token } = get();
        return authMode === "password" && !token;
      },
    }),
    { name: AUTH_STORAGE, partialize: (s) => ({ token: s.token }) }
  )
);
