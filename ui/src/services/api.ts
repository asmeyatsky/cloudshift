import type {
  ApplyResult,
  Manifest,
  PlanResult,
  ProjectConfig,
  ScanResult,
  ValidationResult,
  JobAccepted,
  Pattern,
  FileDiff,
} from "../types";
import { useAuthStore.getState } from "../store/authStore";

const BASE = "/api";

type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error?: string };

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const { token } = useAuthStore.getState();
  if (token) return { Authorization: `Bearer ${token}` };
  const apiKey = (window as unknown as { __CLOUDSHIFT_API_KEY__?: string }).__CLOUDSHIFT_API_KEY__;
  if (apiKey) return { "X-API-Key": apiKey };
  return {};
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<ApiResult<T>> {
  try {
    const res = await fetch(BASE + path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && typeof window !== "undefined") {
      const { authMode, setToken, setSessionExpired } = useAuthStore.getState();
      if (authMode === "password") {
        setToken(null);
        setSessionExpired(true);
      }
    }
    if (!res.ok) {
      return {
        success: false,
        error: typeof data.detail === "string" ? data.detail : data.detail?.[0]?.msg ?? res.statusText,
      };
    }
    return { success: true, data: data as T };
  } catch (e) {
    return { success: false, error: e instanceof Error ? e.message : "Network error" };
  }
}

function get<T>(path: string): Promise<ApiResult<T>> {
  return request<T>("GET", path);
}

function post<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  return request<T>("POST", path, body);
}

function put<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  return request<T>("PUT", path, body);
}

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
  status: (jobId: string) => get<ScanResult>(`/scan/${jobId}`),
};

export const planApi = {
  create: (projectId: string, manifestId: string) =>
    post<JobAccepted>("/plan", {
      project_id: projectId,
      manifest_id: manifestId,
    }),
  get: (jobId: string) => get<PlanResult>(`/plan/${jobId}`),
  getDiffs: async (jobId: string): Promise<ApiResult<FileDiff[]>> => {
    const res = await get<PlanResult>(`/plan/${jobId}`);
    if (!res.success) return res;
    const diffs = (res.data as { steps?: { diffs?: FileDiff[] }[] })?.steps?.flatMap((s) => s.diffs ?? []) ?? [];
    return { success: true, data: diffs };
  },
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
  run: (planId: string) =>
    post<JobAccepted>("/validate", { plan_id: planId }),
  latest: (jobId: string) =>
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
    post<{ report_id: string }>("/report", { project_id: projectId }),
  get: (jobId: string) =>
    get<{ report_id: string; html?: string }>(`/report/${jobId}`),
};

/* ------------------------------------------------------------------ */
/*  Config (global; project-scoped in UI)                              */
/* ------------------------------------------------------------------ */

export const configApi = {
  get: () => get<{ source_provider?: string; target_provider?: string; default_strategy?: string; max_parallel?: number; backup_enabled?: boolean; extra?: Record<string, unknown> }>("/config"),
  update: (body: Record<string, unknown>) => put("/config", body),
};

/* ------------------------------------------------------------------ */
/*  Auth (mode, login for client)                                      */
/* ------------------------------------------------------------------ */

export const authApi = {
  mode: () => get<{ auth_mode: string; deployment_mode: string }>("/auth/mode"),
  login: (username: string, password: string) =>
    post<{ token: string; expires_in: number }>("/auth/login", { username, password }),
};

/* ------------------------------------------------------------------ */
/*  Project / Manifest (UI concepts; map to backend where possible)   */
/* ------------------------------------------------------------------ */

export interface FromSnippetResponse {
  project_id: string;
  root_path: string;
  name: string;
}

export const projectApi = {
  updateConfig: async (_projectId: string, config: ProjectConfig): Promise<ApiResult<unknown>> => {
    return put("/config", {
      extra: {
        excludePaths: config.excludePaths,
        includePatterns: config.includePatterns,
        autoValidate: config.autoValidate,
        dryRun: config.dryRun,
        maxConcurrency: config.maxConcurrency,
      },
    });
  },
  /** Create a project from pasted code (client mode). */
  createFromSnippet: (body: {
    name: string;
    content: string;
    language: string;
    source_provider: string;
    target_provider: string;
    filename?: string;
  }) => post<FromSnippetResponse>("/projects/from-snippet", body),
};

export const manifestApi = {
  get: async (projectId: string): Promise<ApiResult<Manifest>> => {
    return {
      success: true,
      data: {
        id: `manifest-${projectId}`,
        projectId,
        entries: [],
        summary: {
          totalEntries: 0,
          byStatus: { pending: 0, scanned: 0, planned: 0, applied: 0, validated: 0, skipped: 0 },
          byResourceType: {},
          byProvider: { aws: 0, azure: 0, gcp: 0 },
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    };
  },
};
