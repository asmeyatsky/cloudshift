import { useCallback } from "react";
import { planApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";
import type { PlanResult } from "../types";

function mapPlanResponse(data: Record<string, unknown>, jobId?: string): PlanResult {
  const steps = (data.steps as Array<Record<string, unknown>>) ?? [];
  const planId = (data.plan_id as string) ?? "";
  return {
    id: planId,
    jobId,
    manifestId: (data.project_id as string) ?? "",
    transformations: steps.map((s, i) => ({
      id: (s.step_id as string) ?? `step-${i}`,
      patternId: (s.pattern_id as string) ?? "",
      patternName: (s.description as string) ?? "",
      filePath: (s.file_path as string) ?? "",
      lineStart: 0,
      lineEnd: 0,
      before: "",
      after: "",
      confidence: (s.confidence as number) ?? 0,
      status: "pending" as const,
    })),
    diffs: [],
    estimatedChanges: (data.estimated_files_changed as number) ?? 0,
    riskLevel: ((data.estimated_confidence as number) ?? 0.5) >= 0.8 ? "info" : ((data.estimated_confidence as number) ?? 0.5) >= 0.5 ? "warning" : "error",
    timestamp: new Date().toISOString(),
  };
}

export function usePlan() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const { running, planResult, diffs, progress, error } = useOperationStore();
  const setPlanResult = useOperationStore((s) => s.setPlanResult);
  const setDiffs = useOperationStore((s) => s.setDiffs);
  const setRunning = useOperationStore((s) => s.setRunning);
  const setError = useOperationStore((s) => s.setError);

  const createPlan = useCallback((): Promise<void> => {
    if (!activeProject || running) return Promise.reject(new Error("Already running or no project"));

    setRunning(true);
    setError(null);
    setPlanResult(null);
    setDiffs([]);

    return planApi.create(activeProject.id, activeProject.id).then((res) => {
      if (!res.success) {
        const msg = res.error ?? "Plan creation failed";
        setError(msg);
        setRunning(false);
        return Promise.reject(new Error(msg));
      }
      if (!res.data) {
        setError("Plan creation failed");
        setRunning(false);
        return Promise.reject(new Error("Plan creation failed"));
      }
      const jobId = "job_id" in res.data ? res.data.job_id : (res.data as { id: string }).id;
      const pollMs = 1500;
      const maxAttempts = 120;
      let attempts = 0;
      return new Promise<void>((resolve, reject) => {
        const poll = async () => {
          attempts += 1;
          const planRes = await planApi.get(jobId);
          if (planRes.success && planRes.data) {
            const raw = planRes.data as unknown as Record<string, unknown>;
            if (raw.error) {
              setError(String(raw.error));
              setRunning(false);
              reject(new Error(String(raw.error)));
              return;
            }
            setPlanResult(mapPlanResponse(raw, jobId));
            const diffRes = await planApi.getDiffs(jobId);
            if (diffRes.success && diffRes.data) setDiffs(diffRes.data);
            setRunning(false);
            resolve();
            return;
          }
          const errMsg = !planRes.success ? planRes.error : undefined;
          if (attempts >= maxAttempts) {
            setError(errMsg ?? "Plan timed out");
            setRunning(false);
            reject(new Error(errMsg ?? "Plan timed out"));
            return;
          }
          if (errMsg?.toLowerCase().includes("not found") || errMsg?.toLowerCase().includes("in progress")) {
            setTimeout(poll, pollMs);
          } else {
            setError(errMsg ?? "Plan failed");
            setRunning(false);
            reject(new Error(errMsg ?? "Plan failed"));
          }
        };
        poll();
      });
    });
  }, [activeProject, running, setRunning, setError, setPlanResult, setDiffs]);

  return { createPlan, running, planResult, diffs, progress, error };
}
