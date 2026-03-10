import { useState } from "react";
import { Zap } from "lucide-react";
import { authApi } from "../services/api";
import { useAuthStore } from "../store/authStore";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);
  const setSessionExpired = useAuthStore((s) => s.setSessionExpired);
  const sessionExpired = useAuthStore((s) => s.sessionExpired);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = await authApi.login(username, password);
    setLoading(false);
    if (res.success) {
      setToken(res.data.token);
      setSessionExpired(false);
      setUsername("");
      setPassword("");
    } else {
      setError(res.error ?? "Login failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-0">
      <div className="w-full max-w-sm rounded-2xl border border-white/[0.08] bg-surface-50 p-8 shadow-2xl">
        <div className="mb-8 flex items-center justify-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-accent-purple">
            <Zap className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">CloudShift</h1>
            <p className="text-xs text-gray-500">Sign in (client mode)</p>
          </div>
        </div>
        {sessionExpired && (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            Your session expired. Please sign in again.
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              autoComplete="current-password"
              required
            />
          </div>
          {error && (
            <p className="rounded-lg border border-red-500/20 bg-red-500/[0.06] px-3 py-2 text-xs text-red-400">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gradient-to-r from-primary-600 to-accent-purple py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary-500/20 hover:brightness-110 disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
