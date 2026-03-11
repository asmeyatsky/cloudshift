import { useCallback } from "react";
import { applyApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";
import type { ApplyResult } from "../types";

function mapApplyResponse(data: Record<string, unknown>): ApplyResult {
  return {
    id: (data.plan_id as string) ?? "",
    planId: (data.plan_id as string) ?? "",
    filesModified: (data.files_modified as number) ?? 0,
    transformationsApplied: Array.isArray(data.applied_steps) ? data.applied_steps.length : 0,
    errors: Array.isArray(data.errors) ? (data.errors as string[]) : [],
    duration: 0,
    timestamp: new Date().toISOString(),
  };
}

export function useApply() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const planResult = useOperationStore((s) => s.planResult);
  const running = useOperationStore((s) => s.running);
  const progress = useOperationStore((s) => s.progress);
  const applyResult = useOperationStore((s) => s.applyResult);
  const setApplyResult = useOperationStore((s) => s.setApplyResult);
  const setRunning = useOperationStore((s) => s.setRunning);
  const setError = useOperationStore((s) => s.setError);

  const startApply = useCallback((): Promise<void> => {
    if (!activeProject || !planResult || running) return Promise.reject(new Error("No project, plan, or already running"));

    setRunning(true);
    setError(null);
    setApplyResult(null);

    return applyApi.start(planResult.id).then((res) => {
      if (!res.success || !res.data) {
        setError(res.error ?? "Apply failed to start");
        setRunning(false);
        return Promise.reject(new Error(res.error ?? "Apply failed to start"));
      }
      const jobId = "job_id" in res.data ? res.data.job_id : "";
      const pollMs = 1500;
      const maxAttempts = 120;
      let attempts = 0;
      return new Promise<void>((resolve, reject) => {
        const poll = async () => {
          attempts += 1;
          const statusRes = await applyApi.status(jobId);
          if (statusRes.success && statusRes.data) {
            setApplyResult(mapApplyResponse(statusRes.data as Record<string, unknown>));
            setRunning(false);
            resolve();
            return;
          }
          if (attempts >= maxAttempts) {
            setError(statusRes.error ?? "Apply timed out");
            setRunning(false);
            reject(new Error(statusRes.error ?? "Apply timed out"));
            return;
          }
          if (statusRes.error?.toLowerCase().includes("not found") || statusRes.error?.toLowerCase().includes("in progress")) {
            setTimeout(poll, pollMs);
          } else {
            setError(statusRes.error ?? "Apply failed");
            setRunning(false);
            reject(new Error(statusRes.error ?? "Apply failed"));
          }
        };
        poll();
      });
    });
  }, [activeProject, planResult, running, setRunning, setError, setApplyResult]);

  return { startApply, running, applyResult, progress };
}
