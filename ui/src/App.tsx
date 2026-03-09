import { useEffect } from "react";
import { Routes, Route } from "react-router";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import ManifestPage from "./pages/ManifestPage";
import DiffPage from "./pages/DiffPage";
import ValidationPage from "./pages/ValidationPage";
import PatternsPage from "./pages/PatternsPage";
import SettingsPage from "./pages/SettingsPage";
import ReportPage from "./pages/ReportPage";
import {
  useProjectStore,
  usePatternsStore,
} from "./store";
import {
  SEED_PROJECT,
  SEED_PATTERNS,
} from "./seed";

function useSeedData() {
  const setProjects = useProjectStore((s) => s.setProjects);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const setPatterns = usePatternsStore((s) => s.setPatterns);

  useEffect(() => {
    // Only seed the project and patterns catalogue.
    // Pipeline data (scan/plan/apply/validate) is populated
    // by clicking "Run Pipeline" on the Dashboard.
    setProjects([SEED_PROJECT]);
    setActiveProject(SEED_PROJECT);
    setPatterns(SEED_PATTERNS);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}

export default function App() {
  useSeedData();

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
