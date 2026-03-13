import { useState } from "react";
import ValidationDashboard from "../components/validation/ValidationDashboard";
import IssueList from "../components/validation/IssueList";
import FixOverlay from "../components/validation/FixOverlay";
import { useValidation } from "../hooks/useValidation";
import { useProjectStore, useValidationStore } from "../store";
import { SEED_FIX_DATA } from "../seed";
import type { ValidationIssue } from "../types";

export default function ValidationPage() {
  const { runValidation, result, loading, error } = useValidation();
  const activeProject = useProjectStore((s) => s.activeProject);
  const [fixIssue, setFixIssue] = useState<ValidationIssue | null>(null);
  const resolveIssue = useValidationStore((s) => s.resolveIssue);

  const handleRunValidation = () => {
    if (activeProject?.id) runValidation(activeProject.id);
  };

  const fixData = fixIssue ? SEED_FIX_DATA[fixIssue.id] : null;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Validation</h1>
        <p className="mt-1 text-base text-gray-500">
          Check migration correctness and identify potential issues
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-500/20 bg-red-500/[0.06] px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="space-y-8">
        <ValidationDashboard
          result={result}
          loading={loading}
          onRunValidation={handleRunValidation}
          hasPlanId={!!activeProject?.id}
        />

        {result && result.issues.length > 0 && (
          <div>
            <h2 className="mb-4 text-xl font-semibold text-white">
              All Issues
            </h2>
            <IssueList
              issues={result.issues}
              onFix={(issue) => {
                if (SEED_FIX_DATA[issue.id]) {
                  setFixIssue(issue);
                }
              }}
            />
          </div>
        )}
      </div>

      {fixIssue && fixData && (
        <FixOverlay
          issue={fixIssue}
          fixData={fixData}
          onAccept={() => {
            resolveIssue(fixIssue.id);
            setFixIssue(null);
          }}
          onDismiss={() => setFixIssue(null)}
        />
      )}
    </div>
  );
}
