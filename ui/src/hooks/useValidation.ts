import { useCallback } from "react";
import { validationApi } from "../services/api";
import { useProjectStore, useValidationStore } from "../store";
import type { ValidationResult } from "../types";

function mapValidationResponse(data: Record<string, unknown>): ValidationResult {
  const issues = (data.issues as Array<Record<string, unknown>>) ?? [];
  return {
    id: (data.plan_id as string) ?? "",
    manifestId: (data.plan_id as string) ?? "",
    timestamp: new Date().toISOString(),
    issues: issues.map((i, idx) => ({
      id: `issue-${idx}`,
      entryId: "",
      filePath: (i.file_path as string) ?? "",
      line: (i.line as number) ?? 0,
      column: 0,
      severity: ((i.severity as string) ?? "info") as "error" | "warning" | "info",
      code: "",
      message: (i.message as string) ?? "",
      ruleId: (i.rule as string) ?? "",
    })),
    summary: {
      totalIssues: issues.length,
      errors: issues.filter((i) => (i.severity as string) === "error").length,
      warnings: issues.filter((i) => (i.severity as string) === "warning").length,
      infos: issues.filter((i) => (i.severity as string) === "info").length,
      issuesByRule: {},
    },
    passed: (data.passed as boolean) ?? false,
  };
}

export function useValidation() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const { result, loading, error } = useValidationStore();
  const setResult = useValidationStore((s) => s.setResult);
  const setLoading = useValidationStore((s) => s.setLoading);
  const setError = useValidationStore((s) => s.setError);

  /** Run validation for a plan (use plan_id from plan/apply result). Returns a promise that resolves when done. */
  const runValidation = useCallback((planId: string): Promise<void> => {
    if (!activeProject || loading) return Promise.reject(new Error("No project or already loading"));

    setLoading(true);
    setError(null);

    return validationApi.run(planId).then((res) => {
      if (!res.success) {
        const msg = res.error ?? "Validation failed to start";
        setError(msg);
        setLoading(false);
        return Promise.reject(new Error(msg));
      }
      if (!res.data) {
        setError("Validation failed to start");
        setLoading(false);
        return Promise.reject(new Error("Validation failed to start"));
      }
      const jobId = "job_id" in res.data ? res.data.job_id : "";
      const pollMs = 1500;
      const maxAttempts = 60;
      let attempts = 0;
      return new Promise<void>((resolve, reject) => {
        const poll = async () => {
          attempts += 1;
          const statusRes = await validationApi.status(jobId);
          if (statusRes.success && statusRes.data) {
            setResult(mapValidationResponse(statusRes.data as unknown as Record<string, unknown>));
            setLoading(false);
            resolve();
            return;
          }
          const errMsg = !statusRes.success ? statusRes.error : undefined;
          if (attempts >= maxAttempts) {
            setError(errMsg ?? "Validation timed out");
            setLoading(false);
            reject(new Error(errMsg ?? "Validation timed out"));
            return;
          }
          if (errMsg?.toLowerCase().includes("not found") || errMsg?.toLowerCase().includes("in progress")) {
            setTimeout(poll, pollMs);
          } else {
            setError(errMsg ?? "Validation failed");
            setLoading(false);
            reject(new Error(errMsg ?? "Validation failed"));
          }
        };
        poll();
      });
    });
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
