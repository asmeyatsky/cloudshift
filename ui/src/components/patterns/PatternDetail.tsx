import { ArrowLeft, Tag, ArrowRight } from "lucide-react";
import type { Pattern } from "../../types";

interface Props {
  pattern: Pattern;
  onBack: () => void;
}

const SEVERITY_STYLES = {
  error: "bg-red-100 text-red-700",
  warning: "bg-amber-100 text-amber-700",
  info: "bg-blue-100 text-blue-700",
} as const;

export default function PatternDetail({ pattern, onBack }: Props) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={onBack}
          className="mb-3 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to patterns
        </button>
        <h2 className="text-xl font-semibold text-gray-900">{pattern.name}</h2>
        <p className="mt-1 text-sm text-gray-600">{pattern.description}</p>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium uppercase text-blue-700">
            {pattern.sourceProvider}
          </span>
          <ArrowRight className="h-3 w-3 text-gray-400" />
          <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium uppercase text-emerald-700">
            {pattern.targetProvider}
          </span>
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
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
                className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-600"
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
          <h3 className="text-sm font-semibold text-gray-700">Examples</h3>
          {pattern.examples.map((example, idx) => (
            <div
              key={idx}
              className="overflow-hidden rounded-xl border border-gray-200 bg-white"
            >
              <div className="border-b border-gray-200 bg-gray-50 px-4 py-2">
                <p className="text-sm font-medium text-gray-700">
                  {example.title}
                </p>
                {example.description && (
                  <p className="text-xs text-gray-500">
                    {example.description}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 divide-x divide-gray-200">
                <div className="p-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-red-500">
                    Before
                  </p>
                  <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-700">
                    {example.before}
                  </pre>
                </div>
                <div className="p-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-green-600">
                    After
                  </p>
                  <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-700">
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
