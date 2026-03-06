import { useCallback, useState } from "react";
import { applyApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";
import type { ApplyResult } from "../types";

export function useApply() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const planResult = useOperationStore((s) => s.planResult);
  const running = useOperationStore((s) => s.running);
  const progress = useOperationStore((s) => s.progress);
  const setRunning = useOperationStore((s) => s.setRunning);
  const setError = useOperationStore((s) => s.setError);

  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null);

  const startApply = useCallback(async () => {
    if (!activeProject || !planResult || running) return;

    setRunning(true);
    setError(null);
    setApplyResult(null);

    const res = await applyApi.start(activeProject.id, planResult.id);
    if (res.success) {
      setApplyResult(res.data);
    } else {
      setError(res.error ?? "Apply failed");
    }
    setRunning(false);
  }, [activeProject, planResult, running, setRunning, setError]);

  return { startApply, running, applyResult, progress };
}
