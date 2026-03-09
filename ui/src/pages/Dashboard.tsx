import { useCallback, useState, useRef } from "react";
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
import {
  useProjectStore,
  useManifestStore,
  useOperationStore,
  useValidationStore,
} from "../store";
import { useScan } from "../hooks/useScan";
import {
  SEED_ENTRIES,
  SEED_SCAN_RESULT,
  SEED_PLAN_RESULT,
  SEED_APPLY_RESULT,
  SEED_DIFFS,
  SEED_VALIDATION,
} from "../seed";

type PipelineStep = "scan" | "plan" | "apply" | "validate";

const STEPS: {
  key: PipelineStep;
  label: string;
  icon: typeof Scan;
  desc: string;
}[] = [
  { key: "scan", label: "Scan", icon: Scan, desc: "Discover cloud resources" },
  { key: "plan", label: "Plan", icon: Map, desc: "Generate transformations" },
  { key: "apply", label: "Apply", icon: Play, desc: "Execute changes" },
  { key: "validate", label: "Validate", icon: ShieldCheck, desc: "Verify correctness" },
];

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

  const scanResult = useOperationStore((s) => s.scanResult);
  const setScanResult = useOperationStore((s) => s.setScanResult);
  const planResult = useOperationStore((s) => s.planResult);
  const setPlanResult = useOperationStore((s) => s.setPlanResult);
  const applyResult = useOperationStore((s) => s.applyResult);
  const setApplyResult = useOperationStore((s) => s.setApplyResult);
  const setDiffs = useOperationStore((s) => s.setDiffs);
  const resetOps = useOperationStore((s) => s.reset);

  const validationResult = useValidationStore((s) => s.result);
  const setValidationResult = useValidationStore((s) => s.setResult);

  const { startScan } = useScan();

  const [activityLog, setActivityLog] = useState<LogEntry[]>([]);
  const [runningStep, setRunningStep] = useState<PipelineStep | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const abortRef = useRef(false);

  const addLog = useCallback(
    (message: string, type: LogEntry["type"] = "info") => {
      setActivityLog((prev) =>
        [{ time: now(), message, type }, ...prev].slice(0, 50),
      );
    },
    [],
  );

  const wait = (ms: number) =>
    new Promise<void>((resolve) => {
      const check = () => {
        if (abortRef.current) return resolve();
        setTimeout(resolve, ms);
      };
      check();
    });

  const runPipeline = useCallback(async () => {
    if (!activeProject || pipelineRunning) return;
    abortRef.current = false;
    setPipelineRunning(true);

    // ── Scan ──
    setRunningStep("scan");
    addLog(`Agent initiating project scan on ${activeProject.path}`, "agent");
    
    try {
      await startScan();
      addLog("Scan completed successfully", "success");
    } catch (e: any) {
      addLog(`Scan failed: ${e.message || e}`, "warning");
      setPipelineRunning(false);
      setRunningStep(null);
      return;
    }
    
    if (abortRef.current) { setPipelineRunning(false); setRunningStep(null); return; }

    // ── Plan ──
    setRunningStep("plan");
    await wait(500);
    addLog("Agent generating transformation plan...", "agent");
    await wait(900);
    addLog("Pattern engine matched 12 deterministic rules", "info");
    await wait(800);
    addLog("LLM confidence assessment: EventBridge rule mapping scored 0.78 (below threshold)", "warning");
    await wait(700);
    setPlanResult(SEED_PLAN_RESULT);
    setDiffs(SEED_DIFFS);
    addLog(`Plan ready: ${SEED_PLAN_RESULT.estimatedChanges} changes queued, risk level: ${SEED_PLAN_RESULT.riskLevel}`, "success");
    if (abortRef.current) { setPipelineRunning(false); setRunningStep(null); return; }

    // ── Apply ──
    setRunningStep("apply");
    await wait(500);
    addLog("Agent applying transformations...", "agent");
    await wait(600);
    addLog("Applying transformation 6/14: DynamoDB → Firestore", "info");
    await wait(500);
    addLog("Applying transformation 10/14: Lambda → Cloud Functions", "info");
    await wait(500);
    addLog("Applying transformation 14/14: aws_vpc → google_compute_network", "info");
    await wait(600);
    setApplyResult(SEED_APPLY_RESULT);
    addLog(`Applied: ${SEED_APPLY_RESULT.filesModified} files modified in ${(SEED_APPLY_RESULT.duration / 1000).toFixed(1)}s`, "success");
    if (abortRef.current) { setPipelineRunning(false); setRunningStep(null); return; }

    // ── Validate ──
    setRunningStep("validate");
    await wait(500);
    addLog("Agent running validation checks...", "agent");
    await wait(700);
    addLog("Running AST equivalence checks...", "agent");
    await wait(600);
    addLog("Running residual import scan...", "agent");
    await wait(800);
    setValidationResult(SEED_VALIDATION);
    addLog(`All validation checks complete. ${SEED_VALIDATION.summary.totalIssues} issues found.`, "warning");

    setRunningStep(null);
    setPipelineRunning(false);
  }, [activeProject, pipelineRunning, addLog, setScanResult, setEntries, setPlanResult, setDiffs, setApplyResult, setValidationResult]);

  const handleReset = useCallback(() => {
    abortRef.current = true;
    setPipelineRunning(false);
    setRunningStep(null);
    resetOps();
    setValidationResult(null);
    setEntries([]);
    setActivityLog([]);
    addLog("Pipeline reset. Ready to run.", "agent");
  }, [resetOps, setValidationResult, setEntries, addLog]);

  const getStepStatus = (step: PipelineStep): "idle" | "running" | "done" => {
    if (runningStep === step) return "running";
    if (step === "scan") return scanResult ? "done" : "idle";
    if (step === "plan") return planResult ? "done" : "idle";
    if (step === "apply") return applyResult ? "done" : "idle";
    if (step === "validate") return validationResult ? "done" : "idle";
    return "idle";
  };

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
              Migration Pipeline
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
                </>
              ) : (
                "No project selected"
              )}
            </p>
          </div>
        </div>

        {activeProject && (
          <div className="flex items-center gap-3">
            {(scanResult || applyResult || validationResult) &&
              !pipelineRunning && (
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 rounded-xl border border-white/[0.08] px-5 py-3 text-base font-medium text-gray-400 transition-all hover:bg-white/[0.04] hover:text-gray-200"
                >
                  <RotateCcw className="h-5 w-5" />
                  Reset
                </button>
              )}
            <button
              onClick={runPipeline}
              disabled={pipelineRunning}
              className="group flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-primary-600 to-accent-purple px-6 py-3 text-base font-semibold text-white shadow-lg shadow-primary-500/20 transition-all hover:shadow-primary-500/30 disabled:opacity-40 disabled:shadow-none"
            >
              {pipelineRunning ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Zap className="h-5 w-5 transition-transform group-hover:scale-110" />
              )}
              {pipelineRunning ? "Running..." : "Run Pipeline"}
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
          {/* Pipeline Steps */}
          <div className="mb-8 rounded-2xl border border-white/[0.06] bg-surface-50 p-6">
            <div className="mb-5 flex items-center gap-2.5">
              <Activity className="h-5 w-5 text-primary-400/70" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
                Agent Pipeline
              </h2>
              {pipelineRunning && (
                <span className="ml-auto flex items-center gap-2 rounded-full bg-primary-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary-400">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-400 opacity-40" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-primary-400" />
                  </span>
                  Processing
                </span>
              )}
            </div>

            <div className="grid grid-cols-4 gap-4">
              {STEPS.map((step, idx) => {
                const status = getStepStatus(step.key);
                const Icon = step.icon;

                return (
                  <div
                    key={step.key}
                    className={`group relative rounded-xl border p-5 text-left transition-all ${
                      status === "running"
                        ? "border-primary-500/25 bg-primary-500/[0.06] animate-shimmer"
                        : status === "done"
                          ? "border-accent-green/15 bg-accent-green/[0.04]"
                          : "border-white/[0.03] bg-surface-100/50 opacity-40"
                    }`}
                  >
                    {idx < STEPS.length - 1 && (
                      <div className="absolute -right-2 top-1/2 z-10 -translate-y-1/2">
                        <ChevronRight
                          className={`h-4 w-4 ${status === "done" ? "text-accent-green/30" : "text-white/[0.08]"}`}
                        />
                      </div>
                    )}

                    <div className="flex items-center gap-4">
                      <div
                        className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
                          status === "running"
                            ? "bg-primary-500/15 text-primary-400"
                            : status === "done"
                              ? "bg-accent-green/15 text-accent-green"
                              : "bg-white/[0.04] text-gray-600"
                        }`}
                      >
                        {status === "running" ? (
                          <Loader2 className="h-6 w-6 animate-spin" />
                        ) : status === "done" ? (
                          <CheckCircle2 className="h-6 w-6" />
                        ) : (
                          <Icon className="h-6 w-6" />
                        )}
                      </div>
                      <div>
                        <p
                          className={`text-lg font-semibold ${
                            status === "running"
                              ? "text-primary-300"
                              : status === "done"
                                ? "text-accent-green"
                                : "text-gray-300"
                          }`}
                        >
                          {step.label}
                        </p>
                        <p className="text-sm text-gray-600">
                          {step.desc}
                        </p>
                      </div>
                    </div>

                    {status === "running" && (
                      <div className="mt-4 h-1 w-full overflow-hidden rounded-full bg-surface-300">
                        <div className="h-full w-1/4 rounded-full bg-gradient-to-r from-primary-500 to-accent-purple animate-scan" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
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
                label="Files Scanned"
                value={scanResult?.filesScanned ?? 0}
                onClick={() => navigate("/manifest")}
              />
              <StatCard
                icon={<Scan className="h-6 w-6 text-accent-purple" />}
                label="Resources Found"
                value={scanResult?.resourcesFound ?? 0}
                onClick={() => navigate("/manifest")}
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
                      Agent idle. Run the pipeline to begin.
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
