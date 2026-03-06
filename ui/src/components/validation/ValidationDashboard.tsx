import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Info,
  RefreshCw,
} from "lucide-react";
import type { ValidationResult } from "../../types";

interface Props {
  result: ValidationResult | null;
  loading: boolean;
  onRunValidation: () => void;
}

export default function ValidationDashboard({
  result,
  loading,
  onRunValidation,
}: Props) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Validation Results
          </h2>
          {result && (
            <p className="text-xs text-gray-500">
              Last run: {new Date(result.timestamp).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={onRunValidation}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          {loading ? "Validating..." : "Run Validation"}
        </button>
      </div>

      {/* Status banner */}
      {result && (
        <div
          className={`flex items-center gap-3 rounded-xl border px-5 py-4 ${
            result.passed
              ? "border-green-200 bg-green-50"
              : "border-red-200 bg-red-50"
          }`}
        >
          {result.passed ? (
            <ShieldCheck className="h-6 w-6 text-green-600" />
          ) : (
            <ShieldAlert className="h-6 w-6 text-red-500" />
          )}
          <div>
            <p
              className={`font-medium ${result.passed ? "text-green-800" : "text-red-800"}`}
            >
              {result.passed
                ? "All validations passed"
                : "Validation issues detected"}
            </p>
            <p
              className={`text-sm ${result.passed ? "text-green-600" : "text-red-600"}`}
            >
              {result.summary.totalIssues} issue
              {result.summary.totalIssues !== 1 ? "s" : ""} found
            </p>
          </div>
        </div>
      )}

      {/* Summary cards */}
      {result && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SummaryCard
            icon={<ShieldAlert className="h-5 w-5 text-red-500" />}
            label="Errors"
            count={result.summary.errors}
            bg="bg-red-50"
            border="border-red-200"
            text="text-red-700"
          />
          <SummaryCard
            icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
            label="Warnings"
            count={result.summary.warnings}
            bg="bg-amber-50"
            border="border-amber-200"
            text="text-amber-700"
          />
          <SummaryCard
            icon={<Info className="h-5 w-5 text-blue-500" />}
            label="Info"
            count={result.summary.infos}
            bg="bg-blue-50"
            border="border-blue-200"
            text="text-blue-700"
          />
        </div>
      )}

      {/* Issues by rule */}
      {result && Object.keys(result.summary.issuesByRule).length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold text-gray-700">
            Issues by Rule
          </h3>
          <div className="space-y-2">
            {Object.entries(result.summary.issuesByRule)
              .sort(([, a], [, b]) => b - a)
              .map(([rule, count]) => (
                <div
                  key={rule}
                  className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm"
                >
                  <span className="font-mono text-xs text-gray-600">
                    {rule}
                  </span>
                  <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
                    {count}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {!result && !loading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16 text-gray-400">
          <ShieldCheck className="mb-3 h-10 w-10" />
          <p className="text-sm">No validation results yet.</p>
          <p className="text-xs">
            Click "Run Validation" to check your migration.
          </p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  count,
  bg,
  border,
  text,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  bg: string;
  border: string;
  text: string;
}) {
  return (
    <div className={`rounded-xl border ${border} ${bg} px-5 py-4`}>
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className={`text-2xl font-bold ${text}`}>{count}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}
