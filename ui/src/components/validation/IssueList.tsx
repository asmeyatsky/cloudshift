import { useState, useMemo } from "react";
import {
  Search,
  AlertCircle,
  AlertTriangle,
  Info,
  FileCode,
} from "lucide-react";
import type { ValidationIssue, Severity } from "../../types";

interface Props {
  issues: ValidationIssue[];
}

const SEVERITY_CONFIG: Record<
  Severity,
  { icon: typeof AlertCircle; color: string; bg: string; border: string }
> = {
  error: {
    icon: AlertCircle,
    color: "text-red-600",
    bg: "bg-red-50",
    border: "border-red-200",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  info: {
    icon: Info,
    color: "text-blue-600",
    bg: "bg-blue-50",
    border: "border-blue-200",
  },
};

export default function IssueList({ issues }: Props) {
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<Severity | "">("");

  const filtered = useMemo(() => {
    let result = [...issues];
    if (severityFilter) {
      result = result.filter((i) => i.severity === severityFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (i) =>
          i.message.toLowerCase().includes(q) ||
          i.filePath.toLowerCase().includes(q) ||
          i.code.toLowerCase().includes(q),
      );
    }
    return result;
  }, [issues, search, severityFilter]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search issues..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div className="flex gap-1">
          {(["", "error", "warning", "info"] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                severityFilter === sev
                  ? "bg-primary-100 text-primary-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {sev || "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Issue list */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-12 text-gray-400">
            <Info className="mb-2 h-8 w-8" />
            <p className="text-sm">No issues match your filters.</p>
          </div>
        ) : (
          filtered.map((issue) => {
            const cfg = SEVERITY_CONFIG[issue.severity];
            const Icon = cfg.icon;
            return (
              <div
                key={issue.id}
                className={`rounded-xl border ${cfg.border} ${cfg.bg} px-4 py-3`}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cfg.color}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${cfg.color} ${cfg.bg}`}
                      >
                        {issue.severity}
                      </span>
                      <span className="font-mono text-xs text-gray-500">
                        {issue.code}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-800">
                      {issue.message}
                    </p>
                    <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                      <FileCode className="h-3 w-3" />
                      <span className="font-mono">
                        {issue.filePath}:{issue.line}:{issue.column}
                      </span>
                    </div>
                    {issue.suggestion && (
                      <p className="mt-2 rounded-lg bg-white/60 px-3 py-2 text-xs text-gray-600">
                        Suggestion: {issue.suggestion}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <p className="text-xs text-gray-400">
        Showing {filtered.length} of {issues.length} issues
      </p>
    </div>
  );
}
