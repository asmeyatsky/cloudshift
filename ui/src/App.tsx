import { useEffect, useState } from "react";
import { Routes, Route } from "react-router";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";
import ManifestPage from "./pages/ManifestPage";
import DiffPage from "./pages/DiffPage";
import ValidationPage from "./pages/ValidationPage";
import PatternsPage from "./pages/PatternsPage";
import SettingsPage from "./pages/SettingsPage";
import ReportPage from "./pages/ReportPage";
import { useAuthStore } from "./store/authStore";
import { useProjectStore, usePatternsStore } from "./store";
import { authApi } from "./services/api";
import { SEED_PROJECT, SEED_PATTERNS } from "./seed";

function useSeedData() {
  const setProjects = useProjectStore((s) => s.setProjects);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const setPatterns = usePatternsStore((s) => s.setPatterns);

  useEffect(() => {
    setProjects([SEED_PROJECT]);
    setActiveProject(SEED_PROJECT);
    setPatterns(SEED_PATTERNS);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}

function useAuthBootstrap() {
  const setMode = useAuthStore((s) => s.setMode);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    authApi.mode().then((res) => {
      if (res.success) {
        setMode(res.data.auth_mode, res.data.deployment_mode);
      }
      setReady(true);
    });
  }, [setMode]);

  return ready;
}

export default function App() {
  const authReady = useAuthBootstrap();
  const needsLogin = useAuthStore((s) => s.needsLogin);
  useSeedData();

  if (!authReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-0">
        <div className="text-sm text-gray-500">Loading…</div>
      </div>
    );
  }

  if (needsLogin()) {
    return <LoginPage />;
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="manifest" element={<ManifestPage />} />
        <Route path="diff" element={<DiffPage />} />
        <Route path="validation" element={<ValidationPage />} />
        <Route path="patterns" element={<PatternsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="report" element={<ReportPage />} />
      </Route>
    </Routes>
  );
}
