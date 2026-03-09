import type {
  ApiResponse,
  ApplyResult,
  FileDiff,
  Manifest,
  ManifestEntry,
  PaginatedResponse,
  Pattern,
  PlanResult,
  Project,
  ProjectConfig,
  ScanResult,
  ValidationResult,
  JobAccepted,
} from "../types";

const BASE = "/api";

/* ------------------------------------------------------------------ */
/*  Generic helpers                                                    */
/* ------------------------------------------------------------------ */
// ... existing code ...

/* ------------------------------------------------------------------ */
/*  Scan / Plan / Apply endpoints                                      */
/* ------------------------------------------------------------------ */

export const scanApi = {
  start: (rootPath: string, sourceProvider: string, targetProvider: string) =>
    post<JobAccepted>("/scan", {
      root_path: rootPath,
      source_provider: sourceProvider,
      target_provider: targetProvider,
    }),
  status: (jobId: string) =>
    get<ScanResult>(`/scan/${jobId}`),
};

export const planApi = {
  create: (projectId: string, manifestId: string) =>
    post<JobAccepted>("/plan", {
      project_id: projectId,
      manifest_id: manifestId,
    }),
  get: (jobId: string) =>
    get<PlanResult>(`/plan/${jobId}`),
  // getDiffs kept same if backend supports it or needs update?
  // Backend `PlanResult` has diffs inside?
  // Let's check schemas.py `PlanResultResponse` -> no diffs, it has steps.
  // Apply returns diffs.
  // We'll leave getDiffs alone for now or remove if unused.
};

export const applyApi = {
  start: (planId: string) =>
    post<JobAccepted>("/apply", { plan_id: planId }),
  status: (jobId: string) =>
    get<ApplyResult>(`/apply/${jobId}`),
};

/* ------------------------------------------------------------------ */
/*  Validation endpoints                                               */
/* ------------------------------------------------------------------ */

export const validationApi = {
  start: (planId: string) =>
    post<JobAccepted>("/validate", { plan_id: planId }),
  status: (jobId: string) =>
    get<ValidationResult>(`/validate/${jobId}`),
};

/* ------------------------------------------------------------------ */
/*  Patterns endpoints                                                 */
/* ------------------------------------------------------------------ */

export const patternsApi = {
  list: (params?: { category?: string; provider?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.provider) query.set("provider", params.provider);
    if (params?.search) query.set("q", params.search);
    const qs = query.toString();
    return get<Pattern[]>(`/patterns${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => get<Pattern>(`/patterns/${id}`),
};

/* ------------------------------------------------------------------ */
/*  Report endpoints                                                   */
/* ------------------------------------------------------------------ */

export const reportApi = {
  generate: (projectId: string) =>
    post<{ url: string }>(`/projects/${projectId}/report`),
  get: (projectId: string) =>
    get<{ html: string }>(`/projects/${projectId}/report/latest`),
};
