import { useEffect, useCallback } from "react";
import {
  Scan,
  Map,
  Play,
  ShieldCheck,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ArrowRight,
  FolderOpen,
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
  const { startApply, running: applyRunning, applyResult } = useApply();
  const {
    runValidation,
    loading: validating,
  } = useValidation();

  // Load projects on mount
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

  const isRunning = scanRunning || planRunning || applyRunning || validating;

  const handleScan = useCallback(() => { startScan(); }, [startScan]);
  const handlePlan = useCallback(() => { createPlan(); }, [createPlan]);
  const handleApply = useCallback(() => { startApply(); }, [startApply]);
  const handleValidate = useCallback(() => { runValidation(); }, [runValidation]);

  return (
    <div className="p-6">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Cloud migration workflow for{" "}
          {activeProject ? (
            <span className="font-medium text-gray-700">
              {activeProject.name}
            </span>
          ) : (
            "your project"
          )}
        </p>
      </div>

      {!activeProject && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white py-16 text-gray-400">
          <FolderOpen className="mb-3 h-10 w-10" />
          <p className="text-sm">No project loaded.</p>
          <p className="text-xs">
            Configure a project in Settings to get started.
          </p>
          <button
            onClick={() => navigate("/settings")}
            className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Go to Settings
          </button>
        </div>
      )}

      {activeProject && (
        <>
          {/* Workflow steps */}
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <WorkflowCard
              step={1}
              title="Scan"
              description="Scan project files and discover cloud resources"
              icon={<Scan className="h-5 w-5" />}
              action={handleScan}
              actionLabel={scanRunning ? "Scanning..." : "Start Scan"}
              disabled={isRunning}
              done={!!scanResult}
              running={scanRunning}
            />
            <WorkflowCard
              step={2}
              title="Plan"
              description="Generate migration transformations and preview diffs"
              icon={<Map className="h-5 w-5" />}
              action={handlePlan}
              actionLabel={planRunning ? "Planning..." : "Create Plan"}
              disabled={isRunning || !scanResult}
              done={!!planResult}
              running={planRunning}
            />
            <WorkflowCard
              step={3}
              title="Apply"
              description="Apply transformations to project files"
              icon={<Play className="h-5 w-5" />}
              action={handleApply}
              actionLabel={applyRunning ? "Applying..." : "Apply Changes"}
              disabled={isRunning || !planResult}
              done={!!applyResult}
              running={applyRunning}
            />
            <WorkflowCard
              step={4}
              title="Validate"
              description="Validate migration correctness and completeness"
              icon={<ShieldCheck className="h-5 w-5" />}
              action={handleValidate}
              actionLabel={validating ? "Validating..." : "Validate"}
              disabled={isRunning || !applyResult}
              done={!!validationResult}
              running={validating}
            />
          </div>

          {/* Progress bar */}
          {isRunning && progress && (
            <div className="mb-8 rounded-xl border border-primary-200 bg-primary-50 px-5 py-4">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="font-medium text-primary-800">
                  {progress.operation}
                </span>
                <span className="text-primary-600">
                  {progress.percentage}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-primary-200">
                <div
                  className="h-full rounded-full bg-primary-600 transition-all duration-300"
                  style={{ width: `${progress.percentage}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-primary-600">
                {progress.message}
              </p>
            </div>
          )}

          {/* Quick stats */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <QuickStat
              icon={<FileText className="h-5 w-5 text-blue-500" />}
              label="Manifest Entries"
              value={entries.length}
              onClick={() => navigate("/manifest")}
            />
            <QuickStat
              icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
              label="Validation Issues"
              value={validationResult?.summary.totalIssues ?? 0}
              onClick={() => navigate("/validation")}
            />
            <QuickStat
              icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
              label="Files Scanned"
              value={scanResult?.filesScanned ?? 0}
              onClick={() => navigate("/manifest")}
            />
          </div>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function WorkflowCard({
  step,
  title,
  description,
  icon,
  action,
  actionLabel,
  disabled,
  done,
  running,
}: {
  step: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  actionLabel: string;
  disabled: boolean;
  done: boolean;
  running: boolean;
}) {
  return (
    <div
      className={`relative rounded-xl border bg-white p-5 transition-shadow ${
        done
          ? "border-green-200 shadow-sm"
          : running
            ? "border-primary-300 shadow-md"
            : "border-gray-200"
      }`}
    >
      <div className="mb-3 flex items-center gap-3">
        <span
          className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
            done
              ? "bg-green-100 text-green-700"
              : running
                ? "bg-primary-100 text-primary-700"
                : "bg-gray-100 text-gray-500"
          }`}
        >
          {done ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : running ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            step
          )}
        </span>
        <div className="flex items-center gap-2 text-gray-700">
          {icon}
          <span className="font-semibold">{title}</span>
        </div>
      </div>
      <p className="mb-4 text-xs text-gray-500">{description}</p>
      <button
        onClick={action}
        disabled={disabled}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {running && <Loader2 className="h-4 w-4 animate-spin" />}
        {actionLabel}
      </button>
    </div>
  );
}

function QuickStat({
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
      className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-5 py-4 text-left transition-shadow hover:shadow-sm"
    >
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
      <ArrowRight className="h-4 w-4 text-gray-300" />
    </button>
  );
}
