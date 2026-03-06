import {
  FileBarChart,
  Download,
  RefreshCw,
  ShieldCheck,
  FileText,
  GitCompare,
  AlertTriangle,
} from "lucide-react";
import { useManifestStore, useValidationStore, useOperationStore } from "../../store";

interface Props {
  loading: boolean;
  reportHtml: string | null;
  onGenerate: () => void;
}

export default function AuditReport({ loading, reportHtml, onGenerate }: Props) {
  const entries = useManifestStore((s) => s.entries);
  const validationResult = useValidationStore((s) => s.result);
  const scanResult = useOperationStore((s) => s.scanResult);
  const planResult = useOperationStore((s) => s.planResult);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Audit Report</h2>
          <p className="text-sm text-gray-500">
            Comprehensive migration audit summary
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onGenerate}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            {loading ? "Generating..." : "Generate Report"}
          </button>
          {reportHtml && (
            <button
              onClick={() => {
                const blob = new Blob([reportHtml], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "cloudshift-audit-report.html";
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <Download className="h-4 w-4" />
              Download HTML
            </button>
          )}
        </div>
      </div>

      {/* Quick summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <ReportCard
          icon={<FileText className="h-5 w-5 text-blue-500" />}
          label="Files Scanned"
          value={scanResult?.filesScanned ?? 0}
        />
        <ReportCard
          icon={<GitCompare className="h-5 w-5 text-purple-500" />}
          label="Transformations"
          value={planResult?.transformations.length ?? 0}
        />
        <ReportCard
          icon={<FileBarChart className="h-5 w-5 text-emerald-500" />}
          label="Manifest Entries"
          value={entries.length}
        />
        <ReportCard
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
          label="Validation Issues"
          value={validationResult?.summary.totalIssues ?? 0}
        />
      </div>

      {/* Validation status */}
      {validationResult && (
        <div
          className={`flex items-center gap-3 rounded-xl border px-5 py-4 ${
            validationResult.passed
              ? "border-green-200 bg-green-50"
              : "border-red-200 bg-red-50"
          }`}
        >
          <ShieldCheck
            className={`h-5 w-5 ${validationResult.passed ? "text-green-600" : "text-red-500"}`}
          />
          <p
            className={`text-sm font-medium ${validationResult.passed ? "text-green-800" : "text-red-800"}`}
          >
            {validationResult.passed
              ? "Migration passed all validation checks"
              : `${validationResult.summary.errors} error(s) and ${validationResult.summary.warnings} warning(s) require attention`}
          </p>
        </div>
      )}

      {/* Entry status breakdown */}
      {entries.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">
            Entry Status Breakdown
          </h3>
          <div className="space-y-2">
            {Object.entries(
              entries.reduce<Record<string, number>>((acc, e) => {
                acc[e.status] = (acc[e.status] ?? 0) + 1;
                return acc;
              }, {}),
            ).map(([status, count]) => {
              const pct = Math.round((count / entries.length) * 100);
              return (
                <div key={status}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium capitalize text-gray-600">
                      {status}
                    </span>
                    <span className="text-gray-400">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-primary-500 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Rendered HTML report */}
      {reportHtml && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">
            Full Report
          </h3>
          <div
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: reportHtml }}
          />
        </div>
      )}

      {!reportHtml && !loading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16 text-gray-400">
          <FileBarChart className="mb-3 h-10 w-10" />
          <p className="text-sm">No report generated yet.</p>
          <p className="text-xs">
            Click "Generate Report" to create an audit report.
          </p>
        </div>
      )}
    </div>
  );
}

function ReportCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}
