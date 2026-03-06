import { useEffect } from "react";
import { X, ArrowRight } from "lucide-react";
import ManifestViewer from "../components/manifest/ManifestViewer";
import { useManifestStore, useProjectStore } from "../store";
import { manifestApi } from "../services/api";
import type { EntryStatus } from "../types";

const STATUS_STYLES: Record<EntryStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  scanned: "bg-blue-100 text-blue-700",
  planned: "bg-amber-100 text-amber-700",
  applied: "bg-emerald-100 text-emerald-700",
  validated: "bg-green-100 text-green-700",
  skipped: "bg-gray-100 text-gray-500",
};

export default function ManifestPage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const setEntries = useManifestStore((s) => s.setEntries);
  const setManifest = useManifestStore((s) => s.setManifest);
  const setLoading = useManifestStore((s) => s.setLoading);
  const loading = useManifestStore((s) => s.loading);
  const selectedEntry = useManifestStore((s) => s.selectedEntry);
  const setSelectedEntry = useManifestStore((s) => s.setSelectedEntry);

  useEffect(() => {
    if (!activeProject) return;
    setLoading(true);
    manifestApi.get(activeProject.id).then((res) => {
      if (res.success) {
        setManifest(res.data);
        setEntries(res.data.entries);
      }
      setLoading(false);
    });
  }, [activeProject, setEntries, setManifest, setLoading]);

  return (
    <div className="flex h-full">
      {/* Main list */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Manifest</h1>
          <p className="mt-1 text-sm text-gray-500">
            All discovered cloud resources and their migration status
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" />
            <span className="ml-3 text-sm">Loading manifest...</span>
          </div>
        ) : (
          <ManifestViewer />
        )}
      </div>

      {/* Detail sidebar */}
      {selectedEntry && (
        <div className="w-96 shrink-0 overflow-y-auto border-l border-gray-200 bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              Entry Details
            </h2>
            <button
              onClick={() => setSelectedEntry(null)}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-gray-500">File Path</p>
              <p className="mt-0.5 break-all font-mono text-xs text-gray-800">
                {selectedEntry.filePath}
              </p>
            </div>

            <div className="flex gap-4">
              <div>
                <p className="text-xs text-gray-500">Resource Type</p>
                <p className="mt-0.5 text-sm font-medium text-gray-800">
                  {selectedEntry.resourceType}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Status</p>
                <span
                  className={`mt-0.5 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[selectedEntry.status]}`}
                >
                  {selectedEntry.status}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium uppercase text-blue-700">
                {selectedEntry.sourceProvider}
              </span>
              <ArrowRight className="h-3 w-3 text-gray-400" />
              <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium uppercase text-emerald-700">
                {selectedEntry.targetProvider}
              </span>
            </div>

            {/* Transformations */}
            {selectedEntry.transformations.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold text-gray-600">
                  Transformations ({selectedEntry.transformations.length})
                </p>
                <div className="space-y-2">
                  {selectedEntry.transformations.map((t) => (
                    <div
                      key={t.id}
                      className="rounded-lg border border-gray-100 bg-gray-50 p-3"
                    >
                      <p className="text-xs font-medium text-gray-700">
                        {t.patternName}
                      </p>
                      <p className="mt-0.5 text-[10px] text-gray-500">
                        Lines {t.lineStart}-{t.lineEnd} | Confidence:{" "}
                        {Math.round(t.confidence * 100)}%
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Issues */}
            {selectedEntry.issues.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold text-gray-600">
                  Issues ({selectedEntry.issues.length})
                </p>
                <div className="space-y-2">
                  {selectedEntry.issues.map((issue) => (
                    <div
                      key={issue.id}
                      className={`rounded-lg border px-3 py-2 text-xs ${
                        issue.severity === "error"
                          ? "border-red-200 bg-red-50 text-red-700"
                          : issue.severity === "warning"
                            ? "border-amber-200 bg-amber-50 text-amber-700"
                            : "border-blue-200 bg-blue-50 text-blue-700"
                      }`}
                    >
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-0.5 opacity-70">
                        Line {issue.line} | {issue.code}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            {Object.keys(selectedEntry.metadata).length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold text-gray-600">
                  Metadata
                </p>
                <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 font-mono text-[10px] text-gray-600">
                  {JSON.stringify(selectedEntry.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
