import { useCallback } from "react";
import { scanApi } from "../services/api";
import { useProjectStore, useOperationStore, useManifestStore } from "../store";
import type { ManifestEntry, EntryStatus } from "../types";

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
      const res = await scanApi.start(
        activeProject.path,
        activeProject.sourceProvider,
        activeProject.targetProvider,
        activeProject.id,
      );
      
      if (!res.success) {
        throw new Error(res.error ?? "Scan failed to start");
      }

      return new Promise<void>((resolve, reject) => {
        const pollMs = 2000;
        const maxAttempts = 300; // 10 min cap
        let attempts = 0;
        const check = async () => {
          try {
            if (useOperationStore.getState().pipelineAborted) {
              setRunning(false);
              reject(new Error("Cancelled"));
              return;
            }
            attempts += 1;
            const statusRes = await scanApi.status(res.data.job_id);
            if (statusRes.success) {
              const data = statusRes.data as { error?: string; files?: { path?: string; services_detected?: string[]; confidence?: number }[]; source_provider?: string; target_provider?: string };
              if (data.error) {
                throw new Error(data.error);
              }
              setScanResult(statusRes.data);
              const entries: ManifestEntry[] = (data.files || []).map((f, idx) => ({
                  id: `e-${idx}`,
                  filePath: f.path ?? "",
                  resourceType: (f.services_detected || []).join(", ") || "Unknown",
                  sourceProvider: (data.source_provider ?? "aws") as "aws" | "azure" | "gcp",
                  targetProvider: (data.target_provider ?? "gcp") as "aws" | "azure" | "gcp",
                  status: "scanned" as EntryStatus,
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
              if (attempts >= maxAttempts) throw new Error("Scan is taking longer than expected (10 min). Try Cancel and check server.");
              if (statusRes.error?.toLowerCase().includes("not found") || statusRes.error?.toLowerCase().includes("in progress")) {
                setTimeout(check, pollMs);
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
