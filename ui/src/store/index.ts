import { create } from "zustand";
import type {
  ApplyResult,
  FileDiff,
  Manifest,
  ManifestEntry,
  Pattern,
  PlanResult,
  ProgressPayload,
  Project,
  ScanResult,
  ValidationResult,
} from "../types";

/* ------------------------------------------------------------------ */
/*  Project store                                                      */
/* ------------------------------------------------------------------ */

interface ProjectState {
  projects: Project[];
  activeProject: Project | null;
  loading: boolean;
  error: string | null;
  setProjects: (projects: Project[]) => void;
  setActiveProject: (project: Project | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeProject: null,
  loading: false,
  error: null,
  setProjects: (projects) => set({ projects }),
  setActiveProject: (activeProject) => set({ activeProject }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));

/* ------------------------------------------------------------------ */
/*  Manifest store                                                     */
/* ------------------------------------------------------------------ */

interface ManifestState {
  manifest: Manifest | null;
  entries: ManifestEntry[];
  selectedEntry: ManifestEntry | null;
  loading: boolean;
  filter: { status: string; resourceType: string; search: string };
  setManifest: (manifest: Manifest | null) => void;
  setEntries: (entries: ManifestEntry[]) => void;
  setSelectedEntry: (entry: ManifestEntry | null) => void;
  setLoading: (loading: boolean) => void;
  setFilter: (filter: Partial<ManifestState["filter"]>) => void;
}

export const useManifestStore = create<ManifestState>((set) => ({
  manifest: null,
  entries: [],
  selectedEntry: null,
  loading: false,
  filter: { status: "", resourceType: "", search: "" },
  setManifest: (manifest) => set({ manifest }),
  setEntries: (entries) => set({ entries }),
  setSelectedEntry: (selectedEntry) => set({ selectedEntry }),
  setLoading: (loading) => set({ loading }),
  setFilter: (filter) =>
    set((s) => ({ filter: { ...s.filter, ...filter } })),
}));

/* ------------------------------------------------------------------ */
/*  Validation store                                                   */
/* ------------------------------------------------------------------ */

interface ValidationState {
  result: ValidationResult | null;
  loading: boolean;
  error: string | null;
  setResult: (result: ValidationResult | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  resolveIssue: (issueId: string) => void;
}

export const useValidationStore = create<ValidationState>((set) => ({
  result: null,
  loading: false,
  error: null,
  setResult: (result) => set({ result }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  resolveIssue: (issueId) =>
    set((s) => {
      if (!s.result) return s;
      const removed = s.result.issues.find((i) => i.id === issueId);
      const issues = s.result.issues.filter((i) => i.id !== issueId);
      const summary = { ...s.result.summary };
      if (removed) {
        summary.totalIssues = issues.length;
        if (removed.severity === "error") summary.errors--;
        else if (removed.severity === "warning") summary.warnings--;
        else summary.infos--;
        const ruleCount = summary.issuesByRule[removed.ruleId];
        if (ruleCount !== undefined) {
          if (ruleCount <= 1) {
            delete summary.issuesByRule[removed.ruleId];
          } else {
            summary.issuesByRule[removed.ruleId] = ruleCount - 1;
          }
        }
      }
      return {
        result: {
          ...s.result,
          issues,
          summary,
          passed: issues.filter((i) => i.severity === "error").length === 0,
        },
      };
    }),
}));

/* ------------------------------------------------------------------ */
/*  Patterns store                                                     */
/* ------------------------------------------------------------------ */

interface PatternsState {
  patterns: Pattern[];
  selectedPattern: Pattern | null;
  loading: boolean;
  filter: { category: string; provider: string; search: string };
  setPatterns: (patterns: Pattern[]) => void;
  setSelectedPattern: (pattern: Pattern | null) => void;
  setLoading: (loading: boolean) => void;
  setFilter: (filter: Partial<PatternsState["filter"]>) => void;
}

export const usePatternsStore = create<PatternsState>((set) => ({
  patterns: [],
  selectedPattern: null,
  loading: false,
  filter: { category: "", provider: "", search: "" },
  setPatterns: (patterns) => set({ patterns }),
  setSelectedPattern: (selectedPattern) => set({ selectedPattern }),
  setLoading: (loading) => set({ loading }),
  setFilter: (filter) =>
    set((s) => ({ filter: { ...s.filter, ...filter } })),
}));

/* ------------------------------------------------------------------ */
/*  Operation store (refactor progress, diffs, validation)             */
/* ------------------------------------------------------------------ */

interface RefactorProgress {
  current: number;
  total: number;
  currentFile: string;
}

interface RefactorSummary {
  total: number;
  changed: number;
  patternCount: number;
  llmCount: number;
  skipped: number;
  llmConfigured: boolean;
  servicesMigrated: Array<{source: string; target: string}>;
  packageChanges: {remove: string[]; install: string[]};
}

interface OperationState {
  scanResult: ScanResult | null;
  planResult: PlanResult | null;
  applyResult: ApplyResult | null;
  diffs: FileDiff[];
  progress: ProgressPayload | null;
  running: boolean;
  error: string | null;
  /** Set by Dashboard when user cancels; hooks stop polling when true. */
  pipelineAborted: boolean;
  /** When true, Dashboard auto-runs pipeline once (e.g. after importing from snippet). */
  runPipelineAfterSnippetImport: boolean;
  refactorProgress: RefactorProgress | null;
  refactorSummary: RefactorSummary | null;
  setScanResult: (r: ScanResult | null) => void;
  setPlanResult: (r: PlanResult | null) => void;
  setApplyResult: (r: ApplyResult | null) => void;
  setDiffs: (d: FileDiff[]) => void;
  setProgress: (p: ProgressPayload | null) => void;
  setRunning: (running: boolean) => void;
  setError: (error: string | null) => void;
  setPipelineAborted: (v: boolean) => void;
  setRunPipelineAfterSnippetImport: (v: boolean) => void;
  setRefactorProgress: (p: RefactorProgress | null) => void;
  setRefactorSummary: (s: RefactorSummary | null) => void;
  reset: () => void;
}

export const useOperationStore = create<OperationState>((set) => ({
  scanResult: null,
  planResult: null,
  applyResult: null,
  diffs: [],
  progress: null,
  running: false,
  error: null,
  pipelineAborted: false,
  runPipelineAfterSnippetImport: false,
  refactorProgress: null,
  refactorSummary: null,
  setScanResult: (scanResult) => set({ scanResult }),
  setPlanResult: (planResult) => set({ planResult }),
  setApplyResult: (applyResult) => set({ applyResult }),
  setDiffs: (diffs) => set({ diffs }),
  setProgress: (progress) => set({ progress }),
  setRunning: (running) => set({ running }),
  setError: (error) => set({ error }),
  setPipelineAborted: (pipelineAborted) => set({ pipelineAborted }),
  setRunPipelineAfterSnippetImport: (runPipelineAfterSnippetImport) => set({ runPipelineAfterSnippetImport }),
  setRefactorProgress: (refactorProgress) => set({ refactorProgress }),
  setRefactorSummary: (refactorSummary) => set({ refactorSummary }),
  reset: () =>
    set({
      scanResult: null,
      planResult: null,
      applyResult: null,
      diffs: [],
      progress: null,
      running: false,
      error: null,
      pipelineAborted: false,
      runPipelineAfterSnippetImport: false,
      refactorProgress: null,
      refactorSummary: null,
    }),
}));
