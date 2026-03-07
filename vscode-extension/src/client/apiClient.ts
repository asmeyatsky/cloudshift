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
    return config.get<string>("apiKey", "") || "";
  }

  private request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const baseUrl = this.getBaseUrl();
      const apiKey = this.getApiKey();
      const url = new URL(path, baseUrl);
      const isHttps = url.protocol === "https:";
      const transport = isHttps ? https : http;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "application/json",
      };

      if (apiKey) {
        headers["X-API-Key"] = apiKey;
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

  async scanProject(
    rootPath: string,
  ): Promise<ScanResult[]> {
    return this.request<ScanResult[]>("POST", "/api/scan", {
      rootPath,
    });
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
  ): Promise<RefactorResult> {
    return this.request<RefactorResult>("POST", "/api/refactor/file", {
      filePath,
      content,
    });
  }

  async refactorSelection(
    filePath: string,
    content: string,
    startLine: number,
    endLine: number,
  ): Promise<RefactorResult> {
    return this.request<RefactorResult>("POST", "/api/refactor/selection", {
      filePath,
      content,
      startLine,
      endLine,
    });
  }

  async validate(filePath: string, content: string): Promise<ValidationResult> {
    return this.request<ValidationResult>("POST", "/api/validate", {
      filePath,
      content,
    });
  }

  async getManifest(): Promise<ManifestEntry[]> {
    return this.request<ManifestEntry[]>("GET", "/api/manifest");
  }
}
