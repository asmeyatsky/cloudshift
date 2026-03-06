import { Routes, Route } from "react-router";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import ManifestPage from "./pages/ManifestPage";
import DiffPage from "./pages/DiffPage";
import ValidationPage from "./pages/ValidationPage";
import PatternsPage from "./pages/PatternsPage";
import SettingsPage from "./pages/SettingsPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
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
