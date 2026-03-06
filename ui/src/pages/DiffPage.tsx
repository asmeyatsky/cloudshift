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
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Diff Viewer</h1>
        <p className="mt-1 text-sm text-gray-500">
          Side-by-side comparison of planned transformations
        </p>
      </div>

      {planResult && (
        <div className="mb-4 flex items-center gap-4 rounded-xl border border-gray-200 bg-white px-5 py-3">
          <GitCompare className="h-5 w-5 text-purple-500" />
          <div className="text-sm">
            <p className="font-medium text-gray-800">
              Plan: {planResult.id.slice(0, 8)}
            </p>
            <p className="text-xs text-gray-500">
              {planResult.estimatedChanges} estimated changes | Risk:{" "}
              <span
                className={
                  planResult.riskLevel === "error"
                    ? "text-red-600"
                    : planResult.riskLevel === "warning"
                      ? "text-amber-600"
                      : "text-blue-600"
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
