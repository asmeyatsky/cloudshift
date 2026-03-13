import { useState, useMemo } from "react";
import {
  Search,
  AlertCircle,
  AlertTriangle,
  Info,
  FileCode,
  Wrench,
} from "lucide-react";
import type { ValidationIssue, Severity } from "../../types";

interface Props {
  issues: ValidationIssue[];
  onFix?: (issue: ValidationIssue) => void;
}

const SEVERITY_CONFIG: Record<
  Severity,
  { icon: typeof AlertCircle; color: string; bg: string; border: string }
> = {
  error: {
    icon: AlertCircle,
    color: "text-red-400",
    bg: "bg-red-500/[0.06]",
    border: "border-red-500/15",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-amber-400",
    bg: "bg-amber-500/[0.06]",
    border: "border-amber-500/15",
  },
  info: {
    icon: Info,
    color: "text-blue-400",
    bg: "bg-blue-500/[0.06]",
    border: "border-blue-500/15",
  },
};

export default function IssueList({ issues, onFix }: Props) {
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
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-600" />
          <input
            type="text"
            placeholder="Search issues..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-white/[0.08] bg-surface-200 py-2 pl-9 pr-3 text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
          />
        </div>
        <div className="flex gap-1">
          {(["", "error", "warning", "info"] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                severityFilter === sev
                  ? "bg-primary-500/15 text-primary-400"
                  : "bg-white/[0.04] text-gray-500 hover:bg-white/[0.08] hover:text-gray-300"
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
          <div className="flex flex-col items-center justify-center rounded-xl border border-white/[0.06] bg-surface-100 py-12 text-gray-600">
            <Info className="mb-2 h-8 w-8" />
            <p className="text-sm text-gray-400">No issues match your filters.</p>
          </div>
        ) : (
          filtered.map((issue) => {
            const cfg = SEVERITY_CONFIG[issue.severity as Severity] ?? SEVERITY_CONFIG.info;
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
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${cfg.color}`}
                      >
                        {issue.severity}
                      </span>
                      <span className="font-mono text-xs text-gray-500">
                        {issue.code}
                      </span>
                    </div>
                    <p className="mt-1 text-base text-gray-300">
                      {issue.message}
                    </p>
                    <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                      <FileCode className="h-3 w-3" />
                      <span className="font-mono">
                        {issue.filePath}:{issue.line}:{issue.column}
                      </span>
                    </div>
                    {issue.suggestion && (
                      <div className="mt-2 flex items-center gap-2">
                        <p className="flex-1 rounded-lg bg-white/[0.03] px-3 py-2 text-sm text-gray-400">
                          Suggestion: {issue.suggestion}
                        </p>
                        {onFix && (
                          <button
                            onClick={() => onFix(issue)}
                            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-gradient-to-r from-accent-purple to-accent-cyan px-3 py-2 text-xs font-semibold text-white shadow-lg shadow-purple-500/15 hover:brightness-110"
                          >
                            <Wrench className="h-3 w-3" />
                            Fix
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <p className="text-xs text-gray-600">
        Showing {filtered.length} of {issues.length} issues
      </p>
    </div>
  );
}
