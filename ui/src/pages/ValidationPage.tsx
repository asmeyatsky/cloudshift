import { useEffect } from "react";
import ValidationDashboard from "../components/validation/ValidationDashboard";
import IssueList from "../components/validation/IssueList";
import { useValidation } from "../hooks/useValidation";

export default function ValidationPage() {
  const { runValidation, fetchLatest, result, loading, error } =
    useValidation();

  useEffect(() => {
    if (!result) {
      fetchLatest();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Validation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Check migration correctness and identify potential issues
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="space-y-8">
        <ValidationDashboard
          result={result}
          loading={loading}
          onRunValidation={runValidation}
        />

        {result && result.issues.length > 0 && (
          <div>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              All Issues
            </h2>
            <IssueList issues={result.issues} />
          </div>
        )}
      </div>
    </div>
  );
}
