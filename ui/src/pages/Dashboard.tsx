import { useCallback, useState, useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  FolderOpen,
  Zap,
  Brain,
  FileText,
  ArrowRight,
  ChevronRight,
  Clock,
  Activity,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { useNavigate } from "react-router";
import {
  useProjectStore,
  useManifestStore,
  useOperationStore,
  useValidationStore,
} from "../store";
import { useRefactor } from "../hooks/useRefactor";
import { useValidation } from "../hooks/useValidation";
import { scanApi, projectApi, type ScanEstimate } from "../services/api";

interface LogEntry {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "agent";
}

function now() {
  return new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function Dashboard() {
  const navigate = useNavigate();
  const activeProject = useProjectStore((s) => s.activeProject);

  const entries = useManifestStore((s) => s.entries);
  const setEntries = useManifestStore((s) => s.setEntries);

  const diffs = useOperationStore((s) => s.diffs);
  const running = useOperationStore((s) => s.running);
  const resetOps = useOperationStore((s) => s.reset);
  const refactorProgress = useOperationStore((s) => s.refactorProgress);
  const refactorSummary = useOperationStore((s) => s.refactorSummary);
  const runPipelineAfterSnippetImport = useOperationStore((s) => s.runPipelineAfterSnippetImport);
  const setRunPipelineAfterSnippetImport = useOperationStore((s) => s.setRunPipelineAfterSnippetImport);

  const validationResult = useValidationStore((s) => s.result);
  const setValidationResult = useValidationStore((s) => s.setResult);

  const { startRefactor, cancelRefactor } = useRefactor();
  const { runValidation } = useValidation();

  const [activityLog, setActivityLog] = useState<LogEntry[]>([]);
  const [repoEstimate, setRepoEstimate] = useState<ScanEstimate | null>(null);
  const [repoEstimateLoading, setRepoEstimateLoading] = useState(false);
  const [repoEstimateError, setRepoEstimateError] = useState<string | null>(null);
  const [reimporting, setReimporting] = useState(false);
  const [showRunConfirm, setShowRunConfirm] = useState(false);
  const [validating, setValidating] = useState(false);

  const handleReimportFromGit = useCallback(async () => {
    if (!activeProject?.repoUrl) return;
    setReimporting(true);
    setRepoEstimateError(null);
    const res = await projectApi.createFromGit({
      repo_url: activeProject.repoUrl,
      branch: activeProject.branch ?? "main",
      name: activeProject.name,
      subpath: activeProject.subpath ?? undefined,
      source_provider: activeProject.sourceProvider.toUpperCase(),
      target_provider: activeProject.targetProvider.toUpperCase(),
    });
    setReimporting(false);
    if (!res.success) {
      setRepoEstimateError(res.error ?? "Re-import failed");
      return;
    }
    const setProjects = useProjectStore.getState().setProjects;
    const setActiveProject = useProjectStore.getState().setActiveProject;
    const projects = useProjectStore.getState().projects;
    const updated = { ...activeProject, id: res.data.project_id, path: res.data.root_path };
    setProjects(projects.map((p) => (p.id === activeProject.id ? updated : p)));
    setActiveProject(updated);
    setRepoEstimate(null);
    setRepoEstimateError(null);
    setRepoEstimateLoading(true);
    scanApi.estimate(res.data.root_path).then((r) => {
      setRepoEstimateLoading(false);
      if (r.success && r.data) setRepoEstimate(r.data);
    }).catch(() => setRepoEstimateLoading(false));
  }, [activeProject]);

  useEffect(() => {
    if (!activeProject?.path) {
      setRepoEstimate(null);
      setRepoEstimateError(null);
      return;
    }
    setRepoEstimateLoading(true);
    setRepoEstimateError(null);
    scanApi.estimate(activeProject.path).then((res) => {
      setRepoEstimateLoading(false);
      if (res.success && res.data) {
        setRepoEstimate(res.data);
        setRepoEstimateError(null);
      } else {
        setRepoEstimate(null);
        setRepoEstimateError(res.success === false ? (res.error ?? "Could not estimate repo size.") : "Could not estimate repo size.");
      }
    }).catch((err: any) => {
      setRepoEstimateLoading(false);
      setRepoEstimate(null);
      const msg = err?.response?.data?.detail ?? err?.message ?? "Could not estimate repo size.";
      setRepoEstimateError(typeof msg === "string" ? msg : String(msg));
    });
  }, [activeProject?.id, activeProject?.path]);

  const addLog = useCallback(
    (message: string, type: LogEntry["type"] = "info") => {
      setActivityLog((prev) =>
        [{ time: now(), message, type }, ...prev].slice(0, 50),
      );
    },
    [],
  );

  const runRefactor = useCallback(async () => {
    if (!activeProject || running) return;
    addLog(`Starting refactor on ${activeProject.path}`, "agent");
    try {
      await startRefactor();
      const summary = useOperationStore.getState().refactorSummary;
      if (summary) {
        addLog(
          `Refactor complete: ${summary.changed} file(s) changed (${summary.patternCount} via patterns, ${summary.llmCount} via LLM, ${summary.skipped} skipped)`,
          summary.changed > 0 ? "success" : "warning",
        );
        if (summary.changed === 0 && !summary.llmConfigured) {
          addLog("No LLM configured. Set GEMINI_API_KEY on the server for LLM fallback.", "warning");
        }
      } else {
        addLog("Refactor complete", "success");
      }
    } catch (e: any) {
      addLog(`Refactor failed: ${e.message || e}`, "warning");
    }
  }, [activeProject, running, startRefactor, addLog]);

  // Auto-run after snippet import
  useEffect(() => {
    if (!runPipelineAfterSnippetImport || !activeProject) return;
    setRunPipelineAfterSnippetImport(false);
    runRefactor();
  }, [runPipelineAfterSnippetImport, activeProject?.id, setRunPipelineAfterSnippetImport, runRefactor]);

  const handleValidate = useCallback(async () => {
    if (!activeProject || validating) return;
    setValidating(true);
    addLog("Running validation checks...", "agent");
    try {
      await runValidation(activeProject.id);
      const valAfter = useValidationStore.getState().result;
      if (valAfter) {
        addLog(
          `Validation complete. Passed: ${valAfter.passed}. Issues: ${valAfter.summary.totalIssues}`,
          valAfter.passed ? "success" : "warning",
        );
        if (!valAfter.passed && valAfter.issues?.length > 0) {
          valAfter.issues.slice(0, 5).forEach((issue) => {
            addLog(`  \u2022 ${issue.message}`, "warning");
          });
          if (valAfter.issues.length > 5) {
            addLog(`  \u2026 and ${valAfter.issues.length - 5} more (see Validation page)`, "warning");
          }
        }
      }
    } catch (e: any) {
      addLog(`Validation failed: ${e.message || e}`, "warning");
    } finally {
      setValidating(false);
    }
  }, [activeProject, validating, runValidation, addLog]);

  const handleReset = useCallback(() => {
    cancelRefactor();
    resetOps();
    setValidationResult(null);
    setEntries([]);
    setActivityLog([]);
    addLog("Reset. Ready to refactor.", "agent");
  }, [cancelRefactor, resetOps, setValidationResult, setEntries, addLog]);

  // Derive status for progress display
  const isDone = !running && refactorSummary != null;

  return (
    <div className="flex min-h-full flex-col p-8 lg:p-10">
      {/* Header */}
      <div className="mb-10 flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-purple/20 ring-1 ring-white/[0.08]">
            <Zap className="h-7 w-7 text-primary-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">
              Refactor
            </h1>
            <p className="mt-1 text-base text-gray-500">
              {activeProject ? (
                <>
                  <span className="text-gray-400">{activeProject.name}</span>
                  <span className="mx-2 text-gray-700">|</span>
                  <span className="font-mono text-sm uppercase text-primary-400/80">
                    {activeProject.sourceProvider}
                  </span>
                  <ArrowRight className="mx-1.5 inline h-4 w-4 text-gray-700" />
                  <span className="font-mono text-sm uppercase text-accent-green/80">
                    {activeProject.targetProvider}
                  </span>
                  <span className="ml-2 text-gray-600">
                    — refactor {activeProject.sourceProvider} code to GCP
                  </span>
                </>
              ) : (
                "No project selected"
              )}
            </p>
            {activeProject && (repoEstimateLoading || repoEstimate || repoEstimateError) && (
              <p className="mt-2 text-sm text-gray-600">
                {repoEstimateLoading ? (
                  "Estimating repo size\u2026"
                ) : repoEstimateError ? (
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-amber-400/90">{repoEstimateError}</span>
                    {activeProject.repoUrl && (
                      <button
                        type="button"
                        onClick={handleReimportFromGit}
                        disabled={reimporting}
                        className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-sm font-medium text-amber-400 hover:bg-amber-500/20 disabled:opacity-50"
                      >
                        {reimporting ? "Re-importing\u2026" : "Re-import repository"}
                      </button>
                    )}
                  </span>
                ) : repoEstimate ? (
                  <>
                    <span className="text-gray-500">
                      ~{repoEstimate.total_files.toLocaleString()} files
                      {repoEstimate.scannable_files > 0 && (
                        <> ({repoEstimate.scannable_files.toLocaleString()} scannable)</>
                      )}
                      {repoEstimate.scannable_files === 0 && repoEstimate.total_files === 0 && (
                        <span className="text-amber-400/90"> No files found. Path may not exist on the server\u2014import from Git or use a path that exists where the backend runs.</span>
                      )}
                    </span>
                    {repoEstimate.message && repoEstimate.scannable_files > 0 && (
                      <span className="ml-2 text-amber-400/90">{repoEstimate.message}</span>
                    )}
                  </>
                ) : null}
              </p>
            )}
          </div>
        </div>

        {activeProject && (
          <div className="flex items-center gap-3">
            {showRunConfirm && repoEstimate && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true">
                <div className="w-full max-w-md rounded-2xl border border-white/10 bg-surface-100 p-6 shadow-xl">
                  <h3 className="text-lg font-semibold text-white">Large repo</h3>
                  <p className="mt-2 text-sm text-gray-400">
                    This repo has {repoEstimate.scannable_files.toLocaleString()} scannable files.
                    {repoEstimate.message && ` ${repoEstimate.message}`}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    Refactoring may take a few minutes. You can Cancel anytime.
                  </p>
                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setShowRunConfirm(false)}
                      className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-400 hover:bg-white/5"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowRunConfirm(false); runRefactor(); }}
                      className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500"
                    >
                      Refactor
                    </button>
                  </div>
                </div>
              </div>
            )}
            {running && (
              <button
                onClick={() => { cancelRefactor(); addLog("Refactor cancelled", "warning"); }}
                className="flex items-center gap-2 rounded-xl border border-amber-500/30 px-5 py-3 text-base font-medium text-amber-400 transition-all hover:bg-amber-500/10 hover:text-amber-300"
              >
                Cancel
              </button>
            )}
            {isDone && (
              <>
                <button
                  onClick={handleValidate}
                  disabled={validating}
                  className="flex items-center gap-2 rounded-xl border border-white/[0.08] px-5 py-3 text-base font-medium text-gray-400 transition-all hover:bg-white/[0.04] hover:text-gray-200 disabled:opacity-40"
                >
                  {validating ? <Loader2 className="h-5 w-5 animate-spin" /> : <ShieldCheck className="h-5 w-5" />}
                  Validate
                </button>
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 rounded-xl border border-white/[0.08] px-5 py-3 text-base font-medium text-gray-400 transition-all hover:bg-white/[0.04] hover:text-gray-200"
                >
                  <RotateCcw className="h-5 w-5" />
                  Reset
                </button>
              </>
            )}
            <button
              onClick={() => {
                if (running) return;
                if (repoEstimate && repoEstimate.scannable_files > 200) {
                  setShowRunConfirm(true);
                } else {
                  runRefactor();
                }
              }}
              disabled={running}
              className="group flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-primary-600 to-accent-purple px-6 py-3 text-base font-semibold text-white shadow-lg shadow-primary-500/20 transition-all hover:shadow-primary-500/30 disabled:opacity-40 disabled:shadow-none"
            >
              {running ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Zap className="h-5 w-5 transition-transform group-hover:scale-110" />
              )}
              {running ? "Refactoring..." : "Refactor"}
            </button>
          </div>
        )}
      </div>

      {!activeProject && (
        <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-white/[0.06] bg-surface-100 py-24">
          <FolderOpen className="mb-5 h-16 w-16 text-gray-700" />
          <p className="text-lg font-medium text-gray-400">
            No project loaded
          </p>
          <p className="mt-2 text-base text-gray-600">
            Configure a project in Settings to get started
          </p>
          <button
            onClick={() => navigate("/settings")}
            className="mt-8 rounded-lg bg-white/[0.04] px-6 py-3 text-base font-medium text-gray-300 ring-1 ring-white/[0.08] transition-all hover:bg-white/[0.08] hover:text-white"
          >
            Go to Settings
          </button>
        </div>
      )}

      {activeProject && (
        <div className="flex flex-1 flex-col">
          {/* Refactor Progress */}
          <div className="mb-8 rounded-2xl border border-white/[0.06] bg-surface-50 p-6">
            <div className="mb-5 flex items-center gap-2.5">
              <Activity className="h-5 w-5 text-primary-400/70" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
                Refactor Status
              </h2>
              {running && (
                <span className="ml-auto flex items-center gap-2 rounded-full bg-primary-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary-400">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-400 opacity-40" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-primary-400" />
                  </span>
                  Processing
                </span>
              )}
            </div>

            {/* Idle state */}
            {!running && !refactorSummary && (
              <div className="flex items-center gap-4 rounded-xl border border-white/[0.03] bg-surface-100/50 p-5">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.04] text-gray-600">
                  <Zap className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-300">Ready to refactor</p>
                  <p className="text-sm text-gray-600">Click Refactor to convert {activeProject.sourceProvider.toUpperCase()} code to GCP</p>
                </div>
              </div>
            )}

            {/* Running state */}
            {running && refactorProgress && (
              <div className="space-y-3">
                <div className="flex items-center gap-4 rounded-xl border border-primary-500/25 bg-primary-500/[0.06] p-5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-500/15 text-primary-400">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-lg font-semibold text-primary-300">
                      Refactoring file {refactorProgress.current} of {refactorProgress.total}
                    </p>
                    <p className="truncate text-sm text-gray-500">{refactorProgress.currentFile}</p>
                  </div>
                  <span className="text-sm font-medium text-primary-400">
                    {diffs.length} changed
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-300">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-purple transition-all duration-300"
                    style={{ width: `${Math.round((refactorProgress.current / refactorProgress.total) * 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Running but no progress yet (initial loading) */}
            {running && !refactorProgress && (
              <div className="flex items-center gap-4 rounded-xl border border-primary-500/25 bg-primary-500/[0.06] p-5">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-500/15 text-primary-400">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-primary-300">Starting refactor...</p>
                  <p className="text-sm text-gray-500">Walking project files</p>
                </div>
              </div>
            )}

            {/* Done state */}
            {isDone && refactorSummary && (
              <div className="flex items-center gap-4 rounded-xl border border-accent-green/15 bg-accent-green/[0.04] p-5">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent-green/15 text-accent-green">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-accent-green">Refactor complete</p>
                  <p className="text-sm text-gray-500">
                    {refactorSummary.changed} file(s) changed out of {refactorSummary.total}
                    {refactorSummary.patternCount > 0 && <> &middot; {refactorSummary.patternCount} via patterns</>}
                    {refactorSummary.llmCount > 0 && <> &middot; {refactorSummary.llmCount} via LLM</>}
                    {!refactorSummary.llmConfigured && <> &middot; <span className="text-amber-400/80">LLM not configured</span></>}
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="grid flex-1 grid-cols-1 gap-8 lg:grid-cols-3">
            {/* Stats */}
            <div className="space-y-3 lg:col-span-1">
              <h3 className="mb-4 flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wider text-gray-600">
                <Activity className="h-4 w-4" />
                Metrics
              </h3>
              <StatCard
                icon={<FileText className="h-6 w-6 text-primary-400" />}
                label="Files Processed"
                value={refactorSummary?.total ?? 0}
                onClick={() => navigate("/manifest")}
              />
              <StatCard
                icon={<Zap className="h-6 w-6 text-accent-purple" />}
                label="Files Changed"
                value={diffs.length}
                onClick={() => navigate("/diff")}
              />
              <StatCard
                icon={<FileText className="h-6 w-6 text-accent-cyan" />}
                label="Manifest Entries"
                value={entries.length}
                onClick={() => navigate("/manifest")}
              />
              <StatCard
                icon={<AlertTriangle className="h-6 w-6 text-amber-400" />}
                label="Validation Issues"
                value={validationResult?.summary.totalIssues ?? 0}
                onClick={() => navigate("/validation")}
              />
            </div>

            {/* Activity Log */}
            <div className="flex flex-col lg:col-span-2">
              <h3 className="mb-4 flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wider text-gray-600">
                <Clock className="h-4 w-4" />
                Agent Activity
              </h3>
              <div className="flex-1 rounded-2xl border border-white/[0.06] bg-surface-50 p-6">
                {activityLog.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center py-20 text-gray-700">
                    <Brain className="mb-4 h-12 w-12" />
                    <p className="text-base text-gray-600">
                      Agent idle. Click Refactor to begin.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1 font-mono text-sm">
                    {activityLog.map((log, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-4 rounded-lg px-3 py-2 transition-colors hover:bg-white/[0.02]"
                      >
                        <span className="shrink-0 text-gray-700">
                          {log.time}
                        </span>
                        <span
                          className={`mt-[7px] h-2 w-2 shrink-0 rounded-full ${
                            log.type === "success"
                              ? "bg-accent-green"
                              : log.type === "warning"
                                ? "bg-amber-400"
                                : log.type === "agent"
                                  ? "bg-accent-purple"
                                  : "bg-gray-600"
                          }`}
                        />
                        <span
                          className={
                            log.type === "success"
                              ? "text-accent-green/80"
                              : log.type === "warning"
                                ? "text-amber-400/80"
                                : log.type === "agent"
                                  ? "text-accent-purple/80"
                                  : "text-gray-500"
                          }
                        >
                          {log.message}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-xl border border-white/[0.06] bg-surface-50 px-5 py-4 text-left transition-all hover:border-white/[0.1] hover:bg-surface-100"
    >
      <div className="flex items-center gap-4">
        {icon}
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
      <ChevronRight className="h-5 w-5 text-gray-700" />
    </button>
  );
}
