import { useCallback } from "react";
import { validationApi } from "../services/api";
import { useProjectStore, useValidationStore } from "../store";

export function useValidation() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const { result, loading, error } = useValidationStore();
  const setResult = useValidationStore((s) => s.setResult);
  const setLoading = useValidationStore((s) => s.setLoading);
  const setError = useValidationStore((s) => s.setError);

  const runValidation = useCallback(async () => {
    if (!activeProject || loading) return;

    setLoading(true);
    setError(null);

    const res = await validationApi.run(activeProject.id);
    if (res.success && res.data) {
      const jobId = "job_id" in res.data ? res.data.job_id : "";
      const statusRes = await validationApi.status(jobId);
      if (statusRes.success && statusRes.data) setResult(statusRes.data);
      else setError(!statusRes.success && "error" in statusRes ? (statusRes.error ?? null) : "Validation failed");
    } else {
      setError(!res.success && "error" in res ? (res.error ?? null) : "Validation failed");
    }
    setLoading(false);
  }, [activeProject, loading, setLoading, setError, setResult]);

  const fetchLatest = useCallback(async () => {
    if (!activeProject) return;

    setLoading(true);
    const res = await validationApi.latest(activeProject.id);
    if (res.success && res.data) setResult(res.data);
    setLoading(false);
  }, [activeProject, setLoading, setResult]);

  return { runValidation, fetchLatest, result, loading, error };
}
