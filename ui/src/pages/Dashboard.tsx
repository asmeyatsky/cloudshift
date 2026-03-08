import { useEffect, useCallback, useState } from "react";
import {
  Scan,
  Map,
  Play,
  ShieldCheck,
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
} from "lucide-react";
import { useNavigate } from "react-router";
import { useScan } from "../hooks/useScan";
import { usePlan } from "../hooks/usePlan";
import { useApply } from "../hooks/useApply";
import { useValidation } from "../hooks/useValidation";
import {
  useProjectStore,
  useManifestStore,
  useOperationStore,
  useValidationStore,
} from "../store";
import { projectApi } from "../services/api";

type PipelineStep = "scan" | "plan" | "apply" | "validate";

const STEPS: {
  key: PipelineStep;
  label: string;
  icon: typeof Scan;
  desc: string;
}[] = [
  { key: "scan", label: "Scan", icon: Scan, desc: "Discover cloud resources" },
  {
    key: "plan",
    label: "Plan",
    icon: Map,
    desc: "Generate transformations",
  },
  { key: "apply", label: "Apply", icon: Play, desc: "Execute changes" },
  {
    key: "validate",
    label: "Validate",
    icon: ShieldCheck,
    desc: "Verify correctness",
  },
];

interface LogEntry {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "agent";
}

export default function Dashboard() {
  const navigate = useNavigate();
  const activeProject = useProjectStore((s) => s.activeProject);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const setProjects = useProjectStore((s) => s.setProjects);
  const entries = useManifestStore((s) => s.entries);
  const progress = useOperationStore((s) => s.progress);
  const validationResult = useValidationStore((s) => s.result);

  const { startScan, running: scanRunning, scanResult } = useScan();
  const { createPlan, running: planRunning, planResult } = usePlan();
  const { startApply, running: applyRunning } = useApply();
  const applyResult = useOperationStore((s) => s.applyResult);
  const { runValidation, loading: validating } = useValidation();

  const [activityLog, setActivityLog] = useState<LogEntry[]>([
    { time: "14:22:01", message: "All validation checks complete. 5 issues found.", type: "warning" },
    { time: "14:21:58", message: "Running residual import scan...", type: "agent" },
    { time: "14:21:55", message: "Running AST equivalence checks...", type: "agent" },
    { time: "14:21:50", message: "Agent running validation checks...", type: "agent" },
    { time: "14:20:12", message: "Applied: 8 files modified in 2.4s", type: "success" },
    { time: "14:20:10", message: "Applying transformation 14/14: aws_vpc → google_compute_network", type: "info" },
    { time: "14:20:08", message: "Applying transformation 10/14: Lambda → Cloud Functions", type: "info" },
    { time: "14:20:05", message: "Applying transformation 6/14: DynamoDB → Firestore", type: "info" },
    { time: "14:20:02", message: "Agent applying transformations...", type: "agent" },
    { time: "14:15:30", message: "Plan ready: 14 changes queued, risk level: warning", type: "success" },
    { time: "14:15:22", message: "LLM confidence assessment: EventBridge rule mapping scored 0.78 (below threshold)", type: "warning" },
    { time: "14:15:18", message: "Pattern engine matched 12 deterministic rules", type: "info" },
    { time: "14:15:10", message: "Agent generating transformation plan...", type: "agent" },
    { time: "14:10:05", message: "Scan complete: 147 files, 12 resources found", type: "success" },
    { time: "14:10:02", message: "Detected: 3 Lambda functions, 2 DynamoDB tables, 1 SQS queue, 2 S3 buckets...", type: "info" },
    { time: "14:09:55", message: "Scanning infra/ (Terraform HCL)...", type: "info" },
    { time: "14:09:50", message: "Scanning src/ (Python, TypeScript)...", type: "info" },
    { time: "14:09:45", message: "Agent initiating project scan on /srv/payments-service", type: "agent" },
  ]);

  useEffect(() => {
    projectApi.list().then((res) => {
      if (res.success && res.data.length > 0) {
        setProjects(res.data);
        if (!activeProject) {
          setActiveProject(res.data[0]!);
        }
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const addLog = useCallback(
    (message: string, type: LogEntry["type"] = "info") => {
      const time = new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      setActivityLog((prev) =>
        [{ time, message, type }, ...prev].slice(0, 50),
      );
    },
    [],
  );

  const resetOps = useOperationStore((s) => s.reset);
  const setValidationResult = useValidationStore((s) => s.setResult);
  const setEntries = useManifestStore((s) => s.setEntries);

  const isRunning = scanRunning || planRunning || applyRunning || validating;

  const handleReset = useCallback(() => {
    resetOps();
    setValidationResult(null);
    setEntries([]);
    setActivityLog([]);
    addLog("Pipeline reset. Ready to run.", "agent");
  }, [resetOps, setValidationResult, setEntries, addLog]);

  const handleScan = useCallback(() => {
    addLog("Initiating project scan...", "agent");
    startScan();
  }, [startScan, addLog]);

  const handlePlan = useCallback(() => {
    addLog("Generating transformation plan...", "agent");
    createPlan();
  }, [createPlan, addLog]);

  const handleApply = useCallback(() => {
    addLog("Applying transformations...", "agent");
    startApply();
  }, [startApply, addLog]);

  const handleValidate = useCallback(() => {
    addLog("Running validation checks...", "agent");
    runValidation();
  }, [runValidation, addLog]);

  useEffect(() => {
    if (scanResult)
      addLog(
        `Scan complete: ${scanResult.filesScanned} files, ${scanResult.resourcesFound} resources found`,
        "success",
      );
  }, [scanResult, addLog]);

  useEffect(() => {
    if (planResult)
      addLog(
        `Plan ready: ${planResult.estimatedChanges} changes queued, risk level: ${planResult.riskLevel}`,
        "success",
      );
  }, [planResult, addLog]);

  useEffect(() => {
    if (applyResult)
      addLog(
        `Applied: ${applyResult.filesModified} files modified in ${(applyResult.duration / 1000).toFixed(1)}s`,
        "success",
      );
  }, [applyResult, addLog]);

  useEffect(() => {
    if (validationResult)
      addLog(
        validationResult.passed
          ? "All validation checks passed"
          : `Validation found ${validationResult.summary.totalIssues} issue(s)`,
        validationResult.passed ? "success" : "warning",
      );
  }, [validationResult, addLog]);

  const getStepStatus = (
    step: PipelineStep,
  ): "idle" | "running" | "done" => {
    if (step === "scan")
      return scanRunning ? "running" : scanResult ? "done" : "idle";
    if (step === "plan")
      return planRunning ? "running" : planResult ? "done" : "idle";
    if (step === "apply")
      return applyRunning ? "running" : applyResult ? "done" : "idle";
    if (step === "validate")
      return validating ? "running" : validationResult ? "done" : "idle";
    return "idle";
  };

  const getStepAction = (step: PipelineStep) => {
    if (step === "scan") return handleScan;
    if (step === "plan") return handlePlan;
    if (step === "apply") return handleApply;
    return handleValidate;
  };

  const isStepEnabled = (step: PipelineStep) => {
    if (isRunning) return false;
    if (step === "scan") return true;
    if (step === "plan") return !!scanResult;
    if (step === "apply") return !!planResult;
    if (step === "validate") return !!applyResult;
    return false;
  };

  return (
    <div className="min-h-full p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-purple/20 ring-1 ring-white/[0.08]">
            <Zap className="h-5 w-5 text-primary-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">
              Migration Pipeline
            </h1>
            <p className="text-sm text-gray-500">
              {activeProject ? (
                <>
                  <span className="text-gray-400">{activeProject.name}</span>
                  <span className="mx-2 text-gray-700">|</span>
                  <span className="font-mono text-[11px] uppercase text-primary-400/80">
                    {activeProject.sourceProvider}
                  </span>
                  <ArrowRight className="mx-1 inline h-3 w-3 text-gray-700" />
                  <span className="font-mono text-[11px] uppercase text-accent-green/80">
                    {activeProject.targetProvider}
                  </span>
                </>
              ) : (
                "No project selected"
              )}
            </p>
          </div>
        </div>

        {activeProject && (
          <div className="flex items-center gap-2">
            {(scanResult || applyResult || validationResult) && !isRunning && (
              <button
                onClick={handleReset}
                className="flex items-center gap-2 rounded-xl border border-white/[0.08] px-4 py-2.5 text-sm font-medium text-gray-400 transition-all hover:bg-white/[0.04] hover:text-gray-200"
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </button>
            )}
            <button
              onClick={handleScan}
              disabled={isRunning}
              className="group flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary-600 to-accent-purple px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary-500/20 transition-all hover:shadow-primary-500/30 disabled:opacity-40 disabled:shadow-none"
            >
              {isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4 transition-transform group-hover:scale-110" />
              )}
              {isRunning ? "Running..." : "Run Pipeline"}
            </button>
          </div>
        )}
      </div>

      {!activeProject && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/[0.06] bg-surface-100 py-20">
          <FolderOpen className="mb-4 h-12 w-12 text-gray-700" />
          <p className="text-sm font-medium text-gray-400">
            No project loaded
          </p>
          <p className="mt-1 text-xs text-gray-600">
            Configure a project in Settings to get started
          </p>
          <button
            onClick={() => navigate("/settings")}
            className="mt-6 rounded-lg bg-white/[0.04] px-5 py-2.5 text-sm font-medium text-gray-300 ring-1 ring-white/[0.08] transition-all hover:bg-white/[0.08] hover:text-white"
          >
            Go to Settings
          </button>
        </div>
      )}

      {activeProject && (
        <>
          {/* Pipeline Steps */}
          <div className="mb-6 rounded-2xl border border-white/[0.06] bg-surface-50 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary-400/70" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                Agent Pipeline
              </h2>
              {isRunning && (
                <span className="ml-auto flex items-center gap-1.5 rounded-full bg-primary-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary-400">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-400 opacity-40" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary-400" />
                  </span>
                  Processing
                </span>
              )}
            </div>

            <div className="grid grid-cols-4 gap-3">
              {STEPS.map((step, idx) => {
                const status = getStepStatus(step.key);
                const enabled = isStepEnabled(step.key);
                const Icon = step.icon;

                return (
                  <button
                    key={step.key}
                    onClick={getStepAction(step.key)}
                    disabled={!enabled}
                    className={`group relative rounded-xl border p-4 text-left transition-all ${
                      status === "running"
                        ? "border-primary-500/25 bg-primary-500/[0.06] animate-shimmer"
                        : status === "done"
                          ? "border-accent-green/15 bg-accent-green/[0.04]"
                          : enabled
                            ? "border-white/[0.06] bg-surface-100 hover:border-white/[0.1] hover:bg-surface-200/60"
                            : "border-white/[0.03] bg-surface-100/50 opacity-40"
                    }`}
                  >
                    {idx < STEPS.length - 1 && (
                      <div className="absolute -right-1.5 top-1/2 z-10 -translate-y-1/2">
                        <ChevronRight
                          className={`h-3 w-3 ${status === "done" ? "text-accent-green/30" : "text-white/[0.08]"}`}
                        />
                      </div>
                    )}

                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                          status === "running"
                            ? "bg-primary-500/15 text-primary-400"
                            : status === "done"
                              ? "bg-accent-green/15 text-accent-green"
                              : "bg-white/[0.04] text-gray-600"
                        }`}
                      >
                        {status === "running" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : status === "done" ? (
                          <CheckCircle2 className="h-4 w-4" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </div>
                      <div>
                        <p
                          className={`text-sm font-semibold ${
                            status === "running"
                              ? "text-primary-300"
                              : status === "done"
                                ? "text-accent-green"
                                : "text-gray-300"
                          }`}
                        >
                          {step.label}
                        </p>
                        <p className="text-[10px] text-gray-600">
                          {step.desc}
                        </p>
                      </div>
                    </div>

                    {status === "running" && (
                      <div className="mt-3 h-0.5 w-full overflow-hidden rounded-full bg-surface-300">
                        <div className="h-full w-1/4 rounded-full bg-gradient-to-r from-primary-500 to-accent-purple animate-scan" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Progress */}
          {isRunning && progress && (
            <div className="mb-6 rounded-2xl border border-primary-500/15 bg-primary-500/[0.04] p-5">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-accent-purple" />
                  <span className="text-sm font-semibold text-gray-200">
                    {progress.operation}
                  </span>
                </div>
                <span className="font-mono text-sm text-primary-400">
                  {progress.percentage}%
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-300">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-purple transition-all duration-300"
                  style={{ width: `${progress.percentage}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-gray-500">{progress.message}</p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Stats */}
            <div className="space-y-2 lg:col-span-1">
              <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-600">
                <Activity className="h-3 w-3" />
                Metrics
              </h3>
              <StatCard
                icon={<FileText className="h-4 w-4 text-primary-400" />}
                label="Files Scanned"
                value={scanResult?.filesScanned ?? 0}
                onClick={() => navigate("/manifest")}
              />
              <StatCard
                icon={<Scan className="h-4 w-4 text-accent-purple" />}
                label="Resources Found"
                value={scanResult?.resourcesFound ?? 0}
                onClick={() => navigate("/manifest")}
              />
              <StatCard
                icon={<FileText className="h-4 w-4 text-accent-cyan" />}
                label="Manifest Entries"
                value={entries.length}
                onClick={() => navigate("/manifest")}
              />
              <StatCard
                icon={<AlertTriangle className="h-4 w-4 text-amber-400" />}
                label="Validation Issues"
                value={validationResult?.summary.totalIssues ?? 0}
                onClick={() => navigate("/validation")}
              />
            </div>

            {/* Activity Log */}
            <div className="lg:col-span-2">
              <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-600">
                <Clock className="h-3 w-3" />
                Agent Activity
              </h3>
              <div className="rounded-2xl border border-white/[0.06] bg-surface-50 p-4">
                {activityLog.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-gray-700">
                    <Brain className="mb-3 h-8 w-8" />
                    <p className="text-xs text-gray-600">
                      Agent idle. Run the pipeline to begin.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-0.5 font-mono text-xs">
                    {activityLog.map((log, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/[0.02]"
                      >
                        <span className="shrink-0 text-gray-700">
                          {log.time}
                        </span>
                        <span
                          className={`mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full ${
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
        </>
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
      className="flex w-full items-center justify-between rounded-xl border border-white/[0.06] bg-surface-50 px-4 py-3.5 text-left transition-all hover:border-white/[0.1] hover:bg-surface-100"
    >
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-lg font-bold text-white">{value}</p>
          <p className="text-[10px] text-gray-500">{label}</p>
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-gray-700" />
    </button>
  );
}
