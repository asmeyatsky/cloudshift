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
    if (!activeProject || running) return Promise.reject("Already running or no project");

    setRunning(true);
    setError(null);
    setScanResult(null);

    try {
      const res = await scanApi.start(activeProject.path, activeProject.sourceProvider, activeProject.targetProvider);
      
      if (!res.success) {
        throw new Error(res.error ?? "Scan failed to start");
      }

      return new Promise<void>((resolve, reject) => {
        const check = async () => {
          try {
            const statusRes = await scanApi.status(res.data.job_id);
            if (statusRes.success) {
              setScanResult(statusRes.data);
              // Map backend files to ManifestEntry[]
              const entries = (statusRes.data.files || []).map((f: any, idx: number) => ({
                  id: `e-${idx}`,
                  filePath: f.path,
                  resourceType: (f.services_detected || []).join(", ") || "Unknown",
                  sourceProvider: statusRes.data.source_provider,
                  targetProvider: statusRes.data.target_provider,
                  status: "scanned",
                  transformations: [],
                  issues: [],
                  metadata: { services: f.services_detected, confidence: f.confidence },
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
              }));
              setEntries(entries);
              setRunning(false);
              resolve();
            } else {
              if (statusRes.error && statusRes.error.includes("progress")) {
                setTimeout(check, 1000);
              } else {
                throw new Error(statusRes.error ?? "Scan failed");
              }
            }
          } catch (err: any) {
            setError(err.message);
            setRunning(false);
            reject(err);
          }
        };
        check();
      });
    } catch (err: any) {
      setError(err.message);
      setRunning(false);
      return Promise.reject(err);
    }
  }, [activeProject, running, setRunning, setError, setScanResult, setEntries]);

  return { startScan, running, scanResult, progress, error };
}
