import { useCallback } from "react";
import { planApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";

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

    const res = await planApi.create(activeProject.id);
    if (res.success) {
      setPlanResult(res.data);
      // Fetch associated diffs
      const diffRes = await planApi.getDiffs(activeProject.id, res.data.id);
      if (diffRes.success) {
        setDiffs(diffRes.data);
      }
    } else {
      setError(res.error ?? "Plan creation failed");
    }
    setRunning(false);
  }, [activeProject, running, setRunning, setError, setPlanResult, setDiffs]);

  return { createPlan, running, planResult, diffs, progress, error };
}
