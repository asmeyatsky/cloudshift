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
    // Read latest from store at call time so pipeline (scan→plan→apply) works without waiting for re-render
    const project = useProjectStore.getState().activeProject ?? activeProject;
    const plan = useOperationStore.getState().planResult ?? planResult;
    const isRunning = useOperationStore.getState().running ?? running;
    if (!project || !plan || isRunning) return Promise.reject(new Error("No project, plan, or already running"));

    setRunning(true);
    setError(null);
    setApplyResult(null);

    return applyApi.start(plan.id).then((res) => {
      if (!res.success) {
        const msg = res.error ?? "Apply failed to start";
        setError(msg);
        setRunning(false);
        return Promise.reject(new Error(msg));
      }
      if (!res.data) {
        setError("Apply failed to start");
        setRunning(false);
        return Promise.reject(new Error("Apply failed to start"));
      }
      const jobId = "job_id" in res.data ? res.data.job_id : "";
      const pollMs = 2000;
      const maxAttempts = 1e6; // No timeout: apply may touch many files
      let attempts = 0;
      return new Promise<void>((resolve, reject) => {
        const poll = async () => {
          attempts += 1;
          const statusRes = await applyApi.status(jobId);
          if (statusRes.success && statusRes.data) {
            setApplyResult(mapApplyResponse(statusRes.data as unknown as Record<string, unknown>));
            setRunning(false);
            resolve();
            return;
          }
          const errMsg = !statusRes.success ? statusRes.error : undefined;
          if (attempts >= maxAttempts) {
            setError(errMsg ?? "Apply timed out");
            setRunning(false);
            reject(new Error(errMsg ?? "Apply timed out"));
            return;
          }
          if (errMsg?.toLowerCase().includes("not found") || errMsg?.toLowerCase().includes("in progress")) {
            setTimeout(poll, pollMs);
          } else {
            setError(errMsg ?? "Apply failed");
            setRunning(false);
            reject(new Error(errMsg ?? "Apply failed"));
          }
        };
        poll();
      });
    });
  }, [activeProject, planResult, running, setRunning, setError, setApplyResult]);

  return { startApply, running, applyResult, progress };
}
