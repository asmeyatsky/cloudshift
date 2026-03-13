import {
  FileBarChart,
  Download,
  RefreshCw,
  ShieldCheck,
  FileText,
  GitCompare,
  AlertTriangle,
  Zap,
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
  const diffs = useOperationStore((s) => s.diffs);
  const refactorSummary = useOperationStore((s) => s.refactorSummary);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Audit Report</h2>
          <p className="text-sm text-gray-500">
            Comprehensive migration audit summary
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onGenerate}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary-600 to-primary-500 px-4 py-2 text-sm font-medium text-white hover:shadow-lg hover:shadow-primary-500/20 disabled:opacity-50"
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
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] px-4 py-2 text-sm font-medium text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
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
          icon={<FileText className="h-5 w-5 text-primary-400" />}
          label="Files Processed"
          value={refactorSummary?.total ?? 0}
        />
        <ReportCard
          icon={<GitCompare className="h-5 w-5 text-accent-purple" />}
          label="Files Changed"
          value={diffs.length}
        />
        <ReportCard
          icon={<Zap className="h-5 w-5 text-accent-green" />}
          label="Via Patterns"
          value={refactorSummary?.patternCount ?? 0}
        />
        <ReportCard
          icon={<AlertTriangle className="h-5 w-5 text-amber-400" />}
          label="Validation Issues"
          value={validationResult?.summary.totalIssues ?? 0}
        />
      </div>

      {/* Validation status */}
      {validationResult && (
        <div
          className={`flex items-center gap-3 rounded-xl border px-5 py-4 ${
            validationResult.passed
              ? "border-green-500/20 bg-green-500/[0.06]"
              : "border-red-500/20 bg-red-500/[0.06]"
          }`}
        >
          <ShieldCheck
            className={`h-5 w-5 ${validationResult.passed ? "text-green-400" : "text-red-400"}`}
          />
          <p
            className={`text-sm font-medium ${validationResult.passed ? "text-green-300" : "text-red-300"}`}
          >
            {validationResult.passed
              ? "Migration passed all validation checks"
              : `${validationResult.summary.errors} error(s) and ${validationResult.summary.warnings} warning(s) require attention`}
          </p>
        </div>
      )}

      {/* Entry status breakdown */}
      {entries.length > 0 && (
        <div className="rounded-xl border border-white/[0.06] bg-surface-100 p-5">
          <h3 className="mb-4 text-sm font-semibold text-gray-300">
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
                    <span className="font-medium capitalize text-gray-400">
                      {status}
                    </span>
                    <span className="text-gray-600">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-300">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-purple transition-all"
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
        <div className="rounded-xl border border-white/[0.06] bg-surface-100 p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-300">
            Full Report
          </h3>
          <div
            className="prose prose-invert prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: reportHtml }}
          />
        </div>
      )}

      {!reportHtml && !loading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/[0.06] bg-surface-100 py-16 text-gray-600">
          <FileBarChart className="mb-3 h-10 w-10" />
          <p className="text-sm text-gray-400">No report generated yet.</p>
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
    <div className="rounded-xl border border-white/[0.06] bg-surface-100 px-5 py-4">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}
