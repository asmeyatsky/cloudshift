import { useCallback } from "react";
import { applyApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";
import { SEED_DIFFS, SEED_DIFFS_AZURE } from "../seed";
import type { ApplyResult, FileDiff } from "../types";

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

/** Exported for unit tests. */
export function buildFileDiffsFromApplyResult(data: Record<string, unknown>): FileDiff[] {
  const details = data.modified_file_details as Array<{ path: string; original_content: string; modified_content: string }> | undefined;
  if (!Array.isArray(details) || details.length === 0) return [];
  return details.map((f) => {
    const orig = f.original_content ?? "";
    const mod = f.modified_content ?? "";
    const origLines = orig.split("\n").length;
    const modLines = mod.split("\n").length;
    return {
      filePath: f.path,
      original: orig,
      modified: mod,
      hunks: [],
      stats: { additions: Math.max(0, modLines - origLines), deletions: Math.max(0, origLines - modLines) },
    };
  });
}

export function useApply() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const planResult = useOperationStore((s) => s.planResult);
  const running = useOperationStore((s) => s.running);
  const progress = useOperationStore((s) => s.progress);
  const applyResult = useOperationStore((s) => s.applyResult);
  const setApplyResult = useOperationStore((s) => s.setApplyResult);
  const setDiffs = useOperationStore((s) => s.setDiffs);
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
      const maxAttempts = 600; // 20 min cap
      let attempts = 0;
      return new Promise<void>((resolve, reject) => {
        const poll = async () => {
          if (useOperationStore.getState().pipelineAborted) {
            setRunning(false);
            reject(new Error("Cancelled"));
            return;
          }
          attempts += 1;
          const statusRes = await applyApi.status(jobId);
          if (statusRes.success && statusRes.data) {
            const data = statusRes.data as unknown as Record<string, unknown>;
            setApplyResult(mapApplyResponse(data));
            let fileDiffs = buildFileDiffsFromApplyResult(data);
            if (fileDiffs.length === 0) {
              const currentProject = useProjectStore.getState().activeProject;
              if (currentProject?.id === "demo-azure") fileDiffs = SEED_DIFFS_AZURE;
              else if (currentProject?.id === "demo-aws") fileDiffs = SEED_DIFFS;
            }
            if (fileDiffs.length > 0) setDiffs(fileDiffs);
            setRunning(false);
            resolve();
            return;
          }
          const errMsg = !statusRes.success ? statusRes.error : undefined;
          if (attempts >= maxAttempts) {
            setError("Apply is taking longer than expected (20 min). Try Cancel and check server.");
            setRunning(false);
            reject(new Error("Apply timed out (20 min)"));
            return;
          }
          if (errMsg?.toLowerCase().includes("not found")) {
            setError("Apply result no longer available (session may have expired). Run Apply again.");
            setRunning(false);
            reject(new Error("Apply result not found (404)"));
            return;
          }
          if (errMsg?.toLowerCase().includes("in progress")) {
            setTimeout(poll, pollMs);
            return;
          }
          setError(errMsg ?? "Apply failed");
          setRunning(false);
          reject(new Error(errMsg ?? "Apply failed"));
        };
        poll();
      });
    });
  }, [activeProject, planResult, running, setRunning, setError, setApplyResult, setDiffs]);

  return { startApply, running, applyResult, progress };
}
