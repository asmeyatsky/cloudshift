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
    planApi.getDiffs(activeProject.id, planResult.id).then((res) => {
      if (res.success) {
        setDiffs(res.data);
      }
    });
  }, [activeProject, planResult, diffs.length, setDiffs]);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Diff Viewer</h1>
        <p className="mt-1 text-base text-gray-500">
          Side-by-side comparison of planned transformations
        </p>
      </div>

      {planResult && (
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
      )}

      <DiffViewer diffs={diffs} />
    </div>
  );
}
