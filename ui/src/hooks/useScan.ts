import { useCallback } from "react";
import { scanApi } from "../services/api";
import { useProjectStore, useOperationStore, useManifestStore } from "../store";

export function useScan() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const { running, scanResult, progress, error } = useOperationStore();
  const setScanResult = useOperationStore((s) => s.setScanResult);
  const setRunning = useOperationStore((s) => s.setRunning);
  const setError = useOperationStore((s) => s.setError);
  const setEntries = useManifestStore((s) => s.setEntries);

  const startScan = useCallback(async () => {
    if (!activeProject || running) return;

    setRunning(true);
    setError(null);
    setScanResult(null);

    const res = await scanApi.start(activeProject.id);
    if (res.success) {
      setScanResult(res.data);
      setEntries(res.data.entries);
    } else {
      setError(res.error ?? "Scan failed");
    }
    setRunning(false);
  }, [activeProject, running, setRunning, setError, setScanResult, setEntries]);

  return { startScan, running, scanResult, progress, error };
}
