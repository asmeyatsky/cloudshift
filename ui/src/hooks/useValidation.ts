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
    if (res.success) {
      setResult(res.data);
    } else {
      setError(res.error ?? "Validation failed");
    }
    setLoading(false);
  }, [activeProject, loading, setLoading, setError, setResult]);

  const fetchLatest = useCallback(async () => {
    if (!activeProject) return;

    setLoading(true);
    const res = await validationApi.latest(activeProject.id);
    if (res.success) {
      setResult(res.data);
    }
    setLoading(false);
  }, [activeProject, setLoading, setResult]);

  return { runValidation, fetchLatest, result, loading, error };
}
