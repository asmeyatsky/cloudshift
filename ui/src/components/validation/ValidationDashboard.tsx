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
  hasPlanId?: boolean;
}

export default function ValidationDashboard({
  result,
  loading,
  onRunValidation,
  hasPlanId = true,
}: Props) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">
            Validation Results
          </h2>
          {result && (
            <p className="text-sm text-gray-500">
              Last run: {new Date(result.timestamp).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={onRunValidation}
          disabled={loading || !hasPlanId}
          title={!hasPlanId ? "Run Plan first to get a plan ID for validation" : undefined}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary-600 to-primary-500 px-4 py-2 text-sm font-medium text-white transition-all hover:shadow-lg hover:shadow-primary-500/20 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          {loading ? "Validating..." : !hasPlanId ? "Run Plan first" : "Run Validation"}
        </button>
      </div>

      {/* Status banner */}
      {result && (
        <div
          className={`flex items-center gap-3 rounded-xl border px-5 py-4 ${
            result.passed
              ? "border-green-500/20 bg-green-500/[0.06]"
              : "border-red-500/20 bg-red-500/[0.06]"
          }`}
        >
          {result.passed ? (
            <ShieldCheck className="h-6 w-6 text-green-400" />
          ) : (
            <ShieldAlert className="h-6 w-6 text-red-400" />
          )}
          <div>
            <p
              className={`font-medium ${result.passed ? "text-green-300" : "text-red-300"}`}
            >
              {result.passed
                ? "All validations passed"
                : "Validation issues detected"}
            </p>
            <p
              className={`text-sm ${result.passed ? "text-green-400/70" : "text-red-400/70"}`}
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
            icon={<ShieldAlert className="h-5 w-5 text-red-400" />}
            label="Errors"
            count={result.summary.errors}
            color="red"
          />
          <SummaryCard
            icon={<AlertTriangle className="h-5 w-5 text-amber-400" />}
            label="Warnings"
            count={result.summary.warnings}
            color="amber"
          />
          <SummaryCard
            icon={<Info className="h-5 w-5 text-blue-400" />}
            label="Info"
            count={result.summary.infos}
            color="blue"
          />
        </div>
      )}

      {/* Issues by rule */}
      {result && Object.keys(result.summary.issuesByRule).length > 0 && (
        <div className="rounded-xl border border-white/[0.06] bg-surface-100 p-5">
          <h3 className="mb-3 text-sm font-semibold text-gray-300">
            Issues by Rule
          </h3>
          <div className="space-y-2">
            {Object.entries(result.summary.issuesByRule)
              .sort(([, a], [, b]) => b - a)
              .map(([rule, count]) => (
                <div
                  key={rule}
                  className="flex items-center justify-between rounded-lg bg-surface-200/50 px-3 py-2 text-sm"
                >
                  <span className="font-mono text-xs text-gray-400">
                    {rule}
                  </span>
                  <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-xs font-medium text-gray-300">
                    {count}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {!result && !loading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/[0.06] bg-surface-100 py-16 text-gray-600">
          <ShieldCheck className="mb-3 h-10 w-10" />
          <p className="text-sm text-gray-400">No validation results yet.</p>
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
  color,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  color: "red" | "amber" | "blue";
}) {
  const styles = {
    red: "border-red-500/15 bg-red-500/[0.06]",
    amber: "border-amber-500/15 bg-amber-500/[0.06]",
    blue: "border-blue-500/15 bg-blue-500/[0.06]",
  };
  const textStyles = {
    red: "text-red-300",
    amber: "text-amber-300",
    blue: "text-blue-300",
  };

  return (
    <div className={`rounded-xl border ${styles[color]} px-5 py-4`}>
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className={`text-2xl font-bold ${textStyles[color]}`}>{count}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}
