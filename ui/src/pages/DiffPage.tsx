import { GitCompare } from "lucide-react";
import DiffViewer from "../components/diff/DiffViewer";
import { useProjectStore, useOperationStore } from "../store";

export default function DiffPage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const diffs = useOperationStore((s) => s.diffs);
  const refactorSummary = useOperationStore((s) => s.refactorSummary);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Diff Viewer</h1>
        <p className="mt-1 text-base text-gray-500">
          {activeProject
            ? `${activeProject.sourceProvider.toUpperCase()} code (left) \u2192 refactored GCP code (right)`
            : "Side-by-side: original code \u2192 refactored GCP code"}
        </p>
      </div>

      {refactorSummary && (
        <div className="mb-4 flex items-center gap-4 rounded-xl border border-white/[0.06] bg-surface-100 px-5 py-3">
          <GitCompare className="h-5 w-5 text-accent-purple" />
          <div className="text-base">
            <p className="font-medium text-gray-200">
              Refactor Results
            </p>
            <p className="text-sm text-gray-500">
              {refactorSummary.changed} file(s) changed out of {refactorSummary.total}
              {refactorSummary.patternCount > 0 && <> &middot; {refactorSummary.patternCount} via patterns</>}
              {refactorSummary.llmCount > 0 && <> &middot; {refactorSummary.llmCount} via LLM</>}
            </p>
          </div>
        </div>
      )}

      {diffs.length === 0 && !refactorSummary && (
        <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm">
          <p className="font-medium text-amber-200">
            No diffs yet.
          </p>
          <p className="mt-2 text-gray-400">
            Go to the <strong>Refactor</strong> page and click <strong>Refactor</strong> to convert
            {activeProject ? ` ${activeProject.sourceProvider.toUpperCase()}` : " AWS/Azure"} code to GCP.
            For a quick try, use <strong>AWS Demo</strong> or <strong>Azure Demo</strong> from the project dropdown,
            or paste a code snippet.
          </p>
        </div>
      )}

      {diffs.length === 0 && refactorSummary && refactorSummary.changed === 0 && !refactorSummary.llmConfigured && (
        <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm">
          <p className="font-medium text-amber-200">
            Refactor completed but no files were changed.
          </p>
          <p className="mt-2 text-gray-400">
            No LLM is configured on the server. Enable <strong>Gemini</strong> or <strong>Ollama</strong> for
            LLM-based refactoring when patterns don't match.
          </p>
        </div>
      )}

      <DiffViewer
        diffs={diffs}
        sourceLabel={activeProject ? `${activeProject.sourceProvider.toUpperCase()} code` : "Original"}
        targetLabel="GCP code"
      />
    </div>
  );
}
