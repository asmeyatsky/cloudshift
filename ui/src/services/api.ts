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
} from "../types";

const BASE = "/api";

/* ------------------------------------------------------------------ */
/*  Generic helpers                                                    */
/* ------------------------------------------------------------------ */

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    return {
      data: undefined as unknown as T,
      success: false,
      error: (body as Record<string, string>).detail ?? res.statusText,
    };
  }

  const data: T = await res.json();
  return { data, success: true };
}

function get<T>(path: string) {
  return request<T>(path);
}

function post<T>(path: string, body?: unknown) {
  return request<T>(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

function put<T>(path: string, body: unknown) {
  return request<T>(path, { method: "PUT", body: JSON.stringify(body) });
}

function del<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}

/* ------------------------------------------------------------------ */
/*  Project endpoints                                                  */
/* ------------------------------------------------------------------ */

export const projectApi = {
  list: () => get<Project[]>("/projects"),
  get: (id: string) => get<Project>(`/projects/${id}`),
  create: (data: Partial<Project>) => post<Project>("/projects", data),
  update: (id: string, data: Partial<Project>) =>
    put<Project>(`/projects/${id}`, data),
  delete: (id: string) => del<void>(`/projects/${id}`),
  updateConfig: (id: string, config: Partial<ProjectConfig>) =>
    put<ProjectConfig>(`/projects/${id}/config`, config),
};

/* ------------------------------------------------------------------ */
/*  Manifest endpoints                                                 */
/* ------------------------------------------------------------------ */

export const manifestApi = {
  get: (projectId: string) => get<Manifest>(`/projects/${projectId}/manifest`),
  getEntry: (projectId: string, entryId: string) =>
    get<ManifestEntry>(`/projects/${projectId}/manifest/entries/${entryId}`),
  listEntries: (
    projectId: string,
    params?: { status?: string; resourceType?: string; page?: number; pageSize?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.resourceType) query.set("resource_type", params.resourceType);
    if (params?.page) query.set("page", String(params.page));
    if (params?.pageSize) query.set("page_size", String(params.pageSize));
    const qs = query.toString();
    return get<PaginatedResponse<ManifestEntry>>(
      `/projects/${projectId}/manifest/entries${qs ? `?${qs}` : ""}`,
    );
  },
};

/* ------------------------------------------------------------------ */
/*  Scan / Plan / Apply endpoints                                      */
/* ------------------------------------------------------------------ */

export const scanApi = {
  start: (projectId: string) =>
    post<ScanResult>(`/projects/${projectId}/scan`),
  status: (projectId: string, scanId: string) =>
    get<ScanResult>(`/projects/${projectId}/scan/${scanId}`),
};

export const planApi = {
  create: (projectId: string) =>
    post<PlanResult>(`/projects/${projectId}/plan`),
  get: (projectId: string, planId: string) =>
    get<PlanResult>(`/projects/${projectId}/plan/${planId}`),
  getDiffs: (projectId: string, planId: string) =>
    get<FileDiff[]>(`/projects/${projectId}/plan/${planId}/diffs`),
};

export const applyApi = {
  start: (projectId: string, planId: string) =>
    post<ApplyResult>(`/projects/${projectId}/apply`, { planId }),
  status: (projectId: string, applyId: string) =>
    get<ApplyResult>(`/projects/${projectId}/apply/${applyId}`),
};

/* ------------------------------------------------------------------ */
/*  Validation endpoints                                               */
/* ------------------------------------------------------------------ */

export const validationApi = {
  run: (projectId: string) =>
    post<ValidationResult>(`/projects/${projectId}/validate`),
  get: (projectId: string, validationId: string) =>
    get<ValidationResult>(
      `/projects/${projectId}/validate/${validationId}`,
    ),
  latest: (projectId: string) =>
    get<ValidationResult>(`/projects/${projectId}/validate/latest`),
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
