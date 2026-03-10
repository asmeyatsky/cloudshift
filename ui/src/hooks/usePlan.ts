import { useCallback } from "react";
import { planApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";
import type { PlanResult } from "../types";

export function usePlan() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const { running, planResult, diffs, progress, error } = useOperationStore();
  const setPlanResult = useOperationStore((s) => s.setPlanResult);
  const setDiffs = useOperationStore((s) => s.setDiffs);
  const setRunning = useOperationStore((s) => s.setRunning);
  const setError = useOperationStore((s) => s.setError);

  const createPlan = useCallback(async () => {
    if (!activeProject || running) return;

    setRunning(true);
    setError(null);
    setPlanResult(null);
    setDiffs([]);

    const res = await planApi.create(activeProject.id, activeProject.id);
    if (res.success && res.data) {
      const jobId = "job_id" in res.data ? res.data.job_id : (res.data as { id: string }).id;
      const planRes = await planApi.get(jobId);
      if (planRes.success && planRes.data) setPlanResult(planRes.data as unknown as PlanResult);
      const diffRes = await planApi.getDiffs(jobId);
      if (diffRes.success) setDiffs(diffRes.data);
    } else {
      setError(!res.success && "error" in res ? (res.error ?? null) : "Plan creation failed");
    }
    setRunning(false);
  }, [activeProject, running, setRunning, setError, setPlanResult, setDiffs]);

  return { createPlan, running, planResult, diffs, progress, error };
}
