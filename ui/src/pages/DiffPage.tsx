import { useEffect } from "react";
import { GitCompare } from "lucide-react";
import DiffViewer from "../components/diff/DiffViewer";
import { useProjectStore, useOperationStore } from "../store";
import { planApi } from "../services/api";

export default function DiffPage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const planResult = useOperationStore((s) => s.planResult);
  const diffs = useOperationStore((s) => s.diffs);
  const setDiffs = useOperationStore((s) => s.setDiffs);

  useEffect(() => {
    if (!activeProject || !planResult || diffs.length > 0) return;
    planApi.getDiffs(planResult.jobId ?? planResult.id).then((res: { success: boolean; data?: unknown }) => {
      if (res.success && Array.isArray(res.data)) {
        setDiffs(res.data);
      }
    });
  }, [activeProject, planResult, diffs.length, setDiffs]);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Diff Viewer</h1>
        <p className="mt-1 text-base text-gray-500">
          {activeProject
            ? `${activeProject.sourceProvider.toUpperCase()} code (left) → refactored GCP code (right)`
            : "Side-by-side: original code → refactored GCP code"}
        </p>
      </div>

      {planResult && (
        <>
          <div className="mb-4 flex items-center gap-4 rounded-xl border border-white/[0.06] bg-surface-100 px-5 py-3">
            <GitCompare className="h-5 w-5 text-accent-purple" />
            <div className="text-base">
              <p className="font-medium text-gray-200">
                Plan: {planResult.id.slice(0, 8)}
              </p>
              <p className="text-sm text-gray-500">
                {planResult.estimatedChanges} estimated changes | Risk:{" "}
                <span
                  className={
                    planResult.riskLevel === "error"
                      ? "text-red-400"
                      : planResult.riskLevel === "warning"
                        ? "text-amber-400"
                        : "text-blue-400"
                  }
                >
                  {planResult.riskLevel}
                </span>
              </p>
            </div>
          </div>
          {planResult.estimatedChanges === 0 && planResult.riskLevel === "error" && (
            <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm">
              <p className="font-medium text-amber-200">
                No transformations were found for this plan.
              </p>
              {planResult.error && (
                <p className="mt-1 text-amber-200/90">{planResult.error}</p>
              )}
              {planResult.warnings && planResult.warnings.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-amber-200/80">
                  {planResult.warnings.slice(0, 5).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-gray-400">
                If you just pasted a <strong>code snippet</strong>, pick the correct source (AWS or Azure) and use code that calls supported APIs (e.g. <code className="rounded bg-white/10 px-1">boto3</code>, <code className="rounded bg-white/10 px-1">azure.storage.blob</code>, Lambda, Azure Functions). Otherwise run <strong>Scan</strong> first on a project with AWS/Azure code; the path must exist where the backend runs. For a quick try, use <strong>AWS Demo</strong> or <strong>Azure Demo</strong> from the project dropdown.
              </p>
            </div>
          )}
        </>
      )}

      <DiffViewer
        diffs={diffs}
        sourceLabel={activeProject ? `${activeProject.sourceProvider.toUpperCase()} code` : "Original"}
        targetLabel="GCP code"
      />
    </div>
  );
}
