import { GoogleAuth } from "google-auth-library";
import * as http from "http";
import * as https from "https";
import * as vscode from "vscode";

export interface ScanResult {
  file: string;
  patterns: PatternMatch[];
}

export interface PatternMatch {
  line: number;
  endLine: number;
  column: number;
  endColumn: number;
  patternId: string;
  patternName: string;
  severity: "info" | "warning" | "error";
  message: string;
  sourceProvider: string;
  targetProvider: string;
}

export interface RefactorResult {
  originalFile: string;
  refactoredContent: string;
  changes: RefactorChange[];
}

export interface RefactorChange {
  line: number;
  original: string;
  replacement: string;
  description: string;
}

export interface ValidationResult {
  file: string;
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  line: number;
  column: number;
  message: string;
  rule: string;
}

export interface ValidationWarning {
  line: number;
  column: number;
  message: string;
  rule: string;
}

export interface ManifestEntry {
  file: string;
  patterns: PatternMatch[];
  status: "pending" | "refactored" | "validated";
}

export class CloudShiftApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
  ) {
    super(message);
    this.name = "CloudShiftApiError";
  }
}

export class ApiClient {
  private getBaseUrl(): string {
    const config = vscode.workspace.getConfiguration("cloudshift");
    return config.get<string>("serverUrl", "http://localhost:8000") || "http://localhost:8000";
  }

  private getApiKey(): string {
    const config = vscode.workspace.getConfiguration("cloudshift");
    return (config.get<string>("apiKey", "") || "").trim();
  }

  private getBearerToken(): string {
    const config = vscode.workspace.getConfiguration("cloudshift");
    return (config.get<string>("bearerToken", "") || "").trim();
  }

  private getIapClientId(): string {
    const config = vscode.workspace.getConfiguration("cloudshift");
    return (config.get<string>("iapClientId", "") || "").trim();
  }

  private getIapCredentialsPath(): string {
    const config = vscode.workspace.getConfiguration("cloudshift");
    return (config.get<string>("iapCredentialsPath", "") || "").trim();
  }

  private shouldUseIap(): boolean {
    const baseUrl = this.getBaseUrl();
    if (!baseUrl.startsWith("https://")) return false;
    try {
      const u = new URL(baseUrl);
      if (u.hostname === "localhost" || u.hostname === "127.0.0.1") return false;
    } catch {
      return false;
    }
    return this.getIapClientId().length > 0;
  }

  private async getIapToken(): Promise<string | null> {
    const clientId = this.getIapClientId();
    if (!clientId) return null;
    const keyPath = this.getIapCredentialsPath();
    try {
      const opts: { keyFilename?: string } = {};
      if (keyPath) opts.keyFilename = keyPath;
      const auth = new GoogleAuth(opts);
      const client = await auth.getIdTokenClient(clientId);
      const headers = await client.getRequestHeaders();
      const authz = headers?.Authorization;
      if (typeof authz === "string" && /^Bearer\s+/i.test(authz)) {
        return authz.replace(/^Bearer\s+/i, "").trim();
      }
      return null;
    } catch {
      return null;
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const baseUrl = this.getBaseUrl();
    let bearerToken = this.getBearerToken();
    if (!bearerToken && this.shouldUseIap()) {
      bearerToken = (await this.getIapToken()) || "";
      if (!bearerToken) {
        const keyPath = this.getIapCredentialsPath();
        const hint = keyPath
          ? "Check that the key file is valid and the service account has IAP access."
          : "Use a service account: create one, add it to IAP access, download key JSON, set cloudshift.iapCredentialsPath to the file path.";
        return Promise.reject(
          new CloudShiftApiError(
            `IAP auth failed. ${hint} Set cloudshift.iapClientId to your IAP OAuth Client ID.`,
          ),
        );
      }
    }
    const apiKey = this.getApiKey();
    const url = new URL(path, baseUrl);
    return new Promise((resolve, reject) => {
      const isHttps = url.protocol === "https:";
      const transport = isHttps ? https : http;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "application/json",
      };

      if (bearerToken) {
        headers["Authorization"] = `Bearer ${bearerToken}`;
      }
      if (apiKey && !headers["Authorization"]) {
        headers["X-API-Key"] = apiKey;
        headers["X-Searce-ID"] = apiKey;
      }

      const options: http.RequestOptions = {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname + url.search,
        method,
        headers,
        timeout: 60000,
      };

      const req = transport.request(options, (res) => {
        let data = "";

        res.on("data", (chunk: Buffer) => {
          data += chunk.toString();
        });

        res.on("end", () => {
          if (
            res.statusCode &&
            res.statusCode >= 200 &&
            res.statusCode < 300
          ) {
            try {
              resolve(JSON.parse(data) as T);
            } catch {
              reject(
                new CloudShiftApiError("Invalid JSON response from server"),
              );
            }
          } else {
            let message = `Server returned status ${res.statusCode}`;
            try {
              const errorBody = JSON.parse(data);
              if (errorBody.detail) {
                message = errorBody.detail;
              }
            } catch {
              // Use default message
            }
            reject(new CloudShiftApiError(message, res.statusCode));
          }
        });
      });

      req.on("error", (err: NodeJS.ErrnoException) => {
        if (err.code === "ECONNREFUSED") {
          reject(
            new CloudShiftApiError(
              `Cannot connect to CloudShift server at ${baseUrl}. Is it running?`,
            ),
          );
        } else {
          reject(new CloudShiftApiError(`Network error: ${err.message}`));
        }
      });

      req.on("timeout", () => {
        req.destroy();
        reject(new CloudShiftApiError("Request timed out"));
      });

      if (body !== undefined) {
        req.write(JSON.stringify(body));
      }

      req.end();
    });
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.request<{ status: string }>("GET", "/health");
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Start a project scan (async job), poll until complete, then return one ScanResult per file.
   * Pattern matches are not included; use scanFile() per file if you need patterns.
   */
  async scanProject(
    rootPath: string,
    options?: { sourceProvider?: string; targetProvider?: string },
  ): Promise<ScanResult[]> {
    const source = options?.sourceProvider ?? "AWS";
    const target = options?.targetProvider ?? "GCP";
    const accepted = await this.request<{ job_id: string }>("POST", "/api/scan", {
      root_path: rootPath,
      source_provider: source,
      target_provider: target,
    });
    const jobId = accepted.job_id;
    const pollMs = 2000;
    const maxAttempts = 150; // 5 min
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const res = await this.request<{
          error?: string;
          files?: { path?: string }[];
          project_id?: string;
        }>("GET", `/api/scan/${jobId}`);
        if (res.error) {
          throw new CloudShiftApiError(res.error);
        }
        if (res.files !== undefined) {
          return (res.files || []).map((f) => ({
            file: f.path ?? "",
            patterns: [],
          }));
        }
      } catch (err) {
        if (err instanceof CloudShiftApiError && err.statusCode === 404) {
          await new Promise((r) => setTimeout(r, pollMs));
          continue;
        }
        throw err;
      }
      await new Promise((r) => setTimeout(r, pollMs));
    }
    throw new CloudShiftApiError("Scan timed out (5 min)");
  }

  async scanFile(filePath: string, content: string): Promise<ScanResult> {
    return this.request<ScanResult>("POST", "/api/scan/file", {
      filePath,
      content,
    });
  }

  async refactorFile(
    filePath: string,
    content: string,
    sourceProvider: "AWS" | "Azure",
  ): Promise<RefactorResult> {
    const body = { filePath, content, sourceProvider, targetProvider: "GCP" };
    try {
      return await this.request<RefactorResult>("POST", "/api/refactor/file", body);
    } catch (err) {
      if (err instanceof CloudShiftApiError && err.statusCode === 503) {
        await new Promise((r) => setTimeout(r, 2000));
        return this.request<RefactorResult>("POST", "/api/refactor/file", body);
      }
      throw err;
    }
  }

  async refactorSelection(
    filePath: string,
    content: string,
    startLine: number,
    endLine: number,
    sourceProvider: "AWS" | "Azure",
  ): Promise<RefactorResult> {
    const body = {
      filePath,
      content,
      startLine,
      endLine,
      sourceProvider,
      targetProvider: "GCP",
    };
    try {
      return await this.request<RefactorResult>("POST", "/api/refactor/selection", body);
    } catch (err) {
      if (err instanceof CloudShiftApiError && err.statusCode === 503) {
        await new Promise((r) => setTimeout(r, 2000));
        return this.request<RefactorResult>("POST", "/api/refactor/selection", body);
      }
      throw err;
    }
  }

  async validate(filePath: string, content: string): Promise<ValidationResult> {
    return this.request<ValidationResult>("POST", "/api/validate/file", {
      filePath,
      content,
    });
  }

  async getManifest(projectId?: string): Promise<ManifestEntry[]> {
    const path = projectId
      ? `/api/manifest?project_id=${encodeURIComponent(projectId)}`
      : "/api/manifest";
    return this.request<ManifestEntry[]>("GET", path);
  }
}
