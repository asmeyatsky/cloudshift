import { ArrowLeft, Tag, ArrowRight } from "lucide-react";
import type { Pattern } from "../../types";

interface Props {
  pattern: Pattern;
  onBack: () => void;
}

const SEVERITY_STYLES = {
  error: "bg-red-500/10 text-red-400",
  warning: "bg-amber-500/10 text-amber-400",
  info: "bg-blue-500/10 text-blue-400",
} as const;

export default function PatternDetail({ pattern, onBack }: Props) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={onBack}
          className="mb-3 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-300"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to patterns
        </button>
        <h2 className="text-xl font-semibold text-white">{pattern.name}</h2>
        <p className="mt-1 text-sm text-gray-400">{pattern.description}</p>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="rounded bg-blue-500/10 px-2 py-0.5 text-xs font-medium uppercase text-blue-400">
            {pattern.sourceProvider}
          </span>
          <ArrowRight className="h-3 w-3 text-gray-600" />
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-medium uppercase text-emerald-400">
            {pattern.targetProvider}
          </span>
          <span className="rounded bg-white/[0.06] px-2 py-0.5 text-xs text-gray-400">
            {pattern.resourceType}
          </span>
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium capitalize ${SEVERITY_STYLES[pattern.severity]}`}
          >
            {pattern.severity}
          </span>
        </div>

        {pattern.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {pattern.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-full bg-white/[0.06] px-2.5 py-0.5 text-xs text-gray-400"
              >
                <Tag className="h-3 w-3" />
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Examples */}
      {pattern.examples.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Examples</h3>
          {pattern.examples.map((example, idx) => (
            <div
              key={idx}
              className="overflow-hidden rounded-xl border border-white/[0.06] bg-surface-100"
            >
              <div className="border-b border-white/[0.06] bg-surface-200/50 px-4 py-2">
                <p className="text-sm font-medium text-gray-300">
                  {example.title}
                </p>
                {example.description && (
                  <p className="text-xs text-gray-500">
                    {example.description}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 divide-x divide-white/[0.06]">
                <div className="p-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-red-400">
                    Before
                  </p>
                  <pre className="overflow-x-auto rounded-lg bg-surface-200/50 p-3 font-mono text-xs text-gray-400">
                    {example.before}
                  </pre>
                </div>
                <div className="p-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-accent-green">
                    After
                  </p>
                  <pre className="overflow-x-auto rounded-lg bg-surface-200/50 p-3 font-mono text-xs text-gray-400">
                    {example.after}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
