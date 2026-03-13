/* ------------------------------------------------------------------ */
/*  Core domain types for CloudShift UI                                */
/* ------------------------------------------------------------------ */

/** Severity levels shared across validation issues and patterns. */
export type Severity = "error" | "warning" | "info";

/** Status of a manifest entry through the migration lifecycle. */
export type EntryStatus =
  | "pending"
  | "scanned"
  | "planned"
  | "applied"
  | "validated"
  | "skipped";

/** Supported cloud providers. */
export type CloudProvider = "aws" | "azure" | "gcp";

/* ----------------------------- Manifest --------------------------- */

export interface ManifestEntry {
  id: string;
  filePath: string;
  resourceType: string;
  sourceProvider: CloudProvider;
  targetProvider: CloudProvider;
  status: EntryStatus;
  transformations: Transformation[];
  issues: ValidationIssue[];
  diff?: DiffHunk[];
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Manifest {
  id: string;
  projectId: string;
  entries: ManifestEntry[];
  summary: ManifestSummary;
  createdAt: string;
  updatedAt: string;
}

export interface ManifestSummary {
  totalEntries: number;
  byStatus: Record<EntryStatus, number>;
  byResourceType: Record<string, number>;
  byProvider: Record<CloudProvider, number>;
}

/* -------------------------- Patterns ------------------------------ */

export interface Pattern {
  id: string;
  name: string;
  description: string;
  sourceProvider: CloudProvider;
  targetProvider: CloudProvider;
  resourceType: string;
  category: string;
  severity: Severity;
  examples: PatternExample[];
  tags: string[];
}

export interface PatternExample {
  title: string;
  before: string;
  after: string;
  description: string;
}

/* ----------------------- Transformations -------------------------- */

export interface Transformation {
  id: string;
  patternId: string;
  patternName: string;
  filePath: string;
  lineStart: number;
  lineEnd: number;
  before: string;
  after: string;
  confidence: number;
  status: "pending" | "applied" | "rejected";
}

/* ------------------------- Validation ----------------------------- */

export interface ValidationIssue {
  id: string;
  entryId: string;
  filePath: string;
  line: number;
  column: number;
  severity: Severity;
  code: string;
  message: string;
  suggestion?: string;
  ruleId: string;
}

export interface ValidationResult {
  id: string;
  manifestId: string;
  timestamp: string;
  issues: ValidationIssue[];
  summary: ValidationSummary;
  passed: boolean;
}

export interface ValidationSummary {
  totalIssues: number;
  errors: number;
  warnings: number;
  infos: number;
  issuesByRule: Record<string, number>;
}

/* ----------------------------- Diff ------------------------------- */

export interface DiffHunk {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  content: string;
  changes: DiffChange[];
}

export interface DiffChange {
  type: "add" | "remove" | "normal";
  content: string;
  oldLine?: number;
  newLine?: number;
}

export interface FileDiff {
  filePath: string;
  original: string;
  modified: string;
  hunks: DiffHunk[];
  stats: { additions: number; deletions: number };
}

/* ---------------------- Scan / Plan / Apply ----------------------- */

export interface JobAccepted {
  job_id: string;
  status: string;
}

export interface ScanResult {
  project_id: string;
  root_path: string;
  source_provider?: string;
  target_provider?: string;
  files: unknown[];
  total_files_scanned: number;
  services_found: string[];
  error?: string;
  /** UI alias for total_files_scanned */
  filesScanned?: number;
  /** UI alias for services_found */
  resourcesFound?: string[];
}

/** Steps grouped by pattern for approve-by-pattern (approve once, apply to all similar). */
export interface StepsByPattern {
  pattern_id: string;
  description: string;
  count: number;
  step_ids: string[];
  file_paths_sample: string[];
}

export interface PlanResult {
  id: string;
  /** Job ID from POST /plan (use for GET /plan/{job_id} e.g. diffs). */
  jobId?: string;
  manifestId: string;
  transformations: Transformation[];
  /** Steps grouped by pattern; use for approve-by-pattern UX. */
  stepsByPattern: StepsByPattern[];
  diffs: FileDiff[];
  estimatedChanges: number;
  riskLevel: Severity;
  timestamp: string;
  /** Backend error (e.g. manifest not found). */
  error?: string;
  /** Backend warnings (e.g. no patterns matched). */
  warnings?: string[];
}

export interface ApplyResult {
  id: string;
  planId: string;
  filesModified: number;
  transformationsApplied: number;
  errors: string[];
  duration: number;
  timestamp: string;
}

/* ----------------------- Project / Config ------------------------- */

export interface Project {
  id: string;
  name: string;
  path: string;
  sourceProvider: CloudProvider;
  targetProvider: CloudProvider;
  config: ProjectConfig;
  createdAt: string;
  updatedAt: string;
  /** Set when project was imported from Git; used for Re-import when path is missing on server. */
  repoUrl?: string;
  branch?: string;
  subpath?: string;
}

export interface ProjectConfig {
  excludePaths: string[];
  includePatterns: string[];
  autoValidate: boolean;
  dryRun: boolean;
  maxConcurrency: number;
}

/* ---------------------- WebSocket Messages ------------------------ */

export type WSMessageType =
  | "progress"
  | "scan_complete"
  | "plan_complete"
  | "apply_complete"
  | "validation_complete"
  | "error";

export interface WSMessage {
  type: WSMessageType;
  payload: unknown;
}

export interface ProgressPayload {
  operation: string;
  current: number;
  total: number;
  message: string;
  percentage: number;
}

/* ----------------------------- API -------------------------------- */

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}
