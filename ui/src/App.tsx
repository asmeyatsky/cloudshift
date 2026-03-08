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
  useManifestStore,
  useOperationStore,
  useValidationStore,
  usePatternsStore,
} from "./store";
import {
  SEED_PROJECT,
  SEED_ENTRIES,
  SEED_SCAN_RESULT,
  SEED_PLAN_RESULT,
  SEED_APPLY_RESULT,
  SEED_DIFFS,
  SEED_VALIDATION,
  SEED_PATTERNS,
} from "./seed";

function useSeedData() {
  const setProjects = useProjectStore((s) => s.setProjects);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const setEntries = useManifestStore((s) => s.setEntries);
  const setScanResult = useOperationStore((s) => s.setScanResult);
  const setPlanResult = useOperationStore((s) => s.setPlanResult);
  const setApplyResult = useOperationStore((s) => s.setApplyResult);
  const setDiffs = useOperationStore((s) => s.setDiffs);
  const setValidationResult = useValidationStore((s) => s.setResult);
  const setPatterns = usePatternsStore((s) => s.setPatterns);

  useEffect(() => {
    setProjects([SEED_PROJECT]);
    setActiveProject(SEED_PROJECT);
    setEntries(SEED_ENTRIES);
    setScanResult(SEED_SCAN_RESULT);
    setPlanResult(SEED_PLAN_RESULT);
    setApplyResult(SEED_APPLY_RESULT);
    setDiffs(SEED_DIFFS);
    setValidationResult(SEED_VALIDATION);
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
