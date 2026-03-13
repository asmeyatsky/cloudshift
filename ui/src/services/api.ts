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
import { useAuthStore } from "../store/authStore";

const BASE = "/api";

type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error?: string };

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const { token, apiKey } = useAuthStore.getState();
  if (token) return { Authorization: `Bearer ${token}` };
  const key = apiKey ?? (window as unknown as { __CLOUDSHIFT_API_KEY__?: string }).__CLOUDSHIFT_API_KEY__;
  if (key) return { "X-API-Key": key };
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
      const msg =
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail[0]?.msg
            : data.error ?? data.message;
      return {
        success: false,
        error: msg && String(msg).trim() ? String(msg) : res.status === 429 ? "Too many requests. Try again in a minute." : res.statusText,
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

export interface ScanEstimate {
  total_files: number;
  scannable_files: number;
  by_extension: Record<string, number>;
  estimated_plan_minutes: number;
  message: string;
}

export const scanApi = {
  start: (
    rootPath: string,
    sourceProvider: string,
    targetProvider: string,
    projectId?: string,
  ) =>
    post<JobAccepted>("/scan", {
      root_path: rootPath,
      source_provider: sourceProvider,
      target_provider: targetProvider,
      ...(projectId != null && { project_id: projectId }),
    }),
  status: (jobId: string) => get<ScanResult>(`/scan/${jobId}`),
  estimate: (rootPath: string) =>
    post<ScanEstimate>("/scan/estimate", { root_path: rootPath }),
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
  /** Start apply. Pass optional stepIds to apply only those steps (e.g. from approved pattern groups). */
  start: (planId: string, stepIds?: string[]) =>
    post<JobAccepted>("/apply", { plan_id: planId, step_ids: stepIds ?? [] }),
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

/** Map backend pattern (snake_case, uppercase providers) to UI Pattern shape so filters work for AWS and Azure. */
function mapPatternFromApi(raw: Record<string, unknown>): Pattern {
  const src = String(raw.source_provider ?? raw.sourceProvider ?? "").toLowerCase();
  const tgt = String(raw.target_provider ?? raw.targetProvider ?? "").toLowerCase();
  const id = String(raw.pattern_id ?? raw.id ?? "");
  const tags = Array.isArray(raw.tags) ? (raw.tags as string[]) : [];
  const category = tags[0] ?? (raw.category as string) ?? "Migration";
  return {
    id,
    name: String(raw.name ?? ""),
    description: String(raw.description ?? ""),
    sourceProvider: (src || "aws") as Pattern["sourceProvider"],
    targetProvider: (tgt || "gcp") as Pattern["targetProvider"],
    resourceType: (raw.resourceType as string) ?? category,
    category,
    severity: ((raw.severity as string) ?? "info") as Pattern["severity"],
    examples: Array.isArray(raw.examples) ? (raw.examples as Pattern["examples"]) : [],
    tags,
  };
}

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
  /** Normalize list response so UI Pattern (camelCase, lowercase providers) works for AWS and Azure. */
  listNormalized: async (params?: { category?: string; provider?: string; search?: string }) => {
    const res = await patternsApi.list(params);
    if (!res.success || !res.data) return res;
    return { ...res, data: res.data.map((p) => mapPatternFromApi(p as unknown as Record<string, unknown>)) };
  },
};

/* ------------------------------------------------------------------ */
/*  Refactor (project-wide streaming)                                  */
/* ------------------------------------------------------------------ */

export const refactorApi = {
  /** Start a streaming project refactor. Returns raw Response for NDJSON reading. */
  startProject: (body: {
    project_id: string;
    source_provider: string;
    target_provider: string;
    root_path?: string;
  }, signal?: AbortSignal) =>
    fetch(BASE + "/refactor/project", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(body),
      signal,
    }),
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

/** Response from POST /projects/from-git (includes repo_url/branch for Re-import). */
export interface FromGitResponse extends FromSnippetResponse {
  repo_url?: string;
  branch?: string;
  subpath?: string | null;
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
  /** Clone a Git repo and register for scanning (AWS/Azure → GCP pipeline). */
  createFromGit: (body: {
    repo_url: string;
    branch: string;
    name: string;
    subpath?: string;
    source_provider: string;
    target_provider: string;
  }) => post<FromGitResponse>("/projects/from-git", body),
};

export const manifestApi = {
  get: async (projectId: string): Promise<ApiResult<Manifest>> => {
    const res = await get<Array<{ file: string; patterns: unknown[]; status: string }>>(`/manifest?project_id=${encodeURIComponent(projectId)}`);
    if (!res.success) return res as ApiResult<Manifest>;
    const entries = (res.data ?? []).map((e, idx) => ({
      id: `e-${idx}`,
      filePath: e.file,
      resourceType: "Unknown",
      sourceProvider: "aws" as const,
      targetProvider: "gcp" as const,
      status: (e.status ?? "pending") as "pending" | "scanned" | "planned" | "applied" | "validated" | "skipped",
      transformations: [],
      issues: [],
      metadata: {},
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }));
    const byStatus = { pending: 0, scanned: 0, planned: 0, applied: 0, validated: 0, skipped: 0 };
    for (const e of entries) byStatus[e.status] = (byStatus[e.status] ?? 0) + 1;
    return {
      success: true,
      data: {
        id: `manifest-${projectId}`,
        projectId,
        entries,
        summary: {
          totalEntries: entries.length,
          byStatus,
          byResourceType: {},
          byProvider: { aws: 0, azure: 0, gcp: 0 },
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    };
  },
};
