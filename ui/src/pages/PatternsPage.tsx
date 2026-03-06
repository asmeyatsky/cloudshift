import { useEffect } from "react";
import PatternBrowser from "../components/patterns/PatternBrowser";
import PatternDetail from "../components/patterns/PatternDetail";
import { usePatternsStore } from "../store";
import { patternsApi } from "../services/api";
import type { Pattern } from "../types";

export default function PatternsPage() {
  const patterns = usePatternsStore((s) => s.patterns);
  const setPatterns = usePatternsStore((s) => s.setPatterns);
  const selectedPattern = usePatternsStore((s) => s.selectedPattern);
  const setSelectedPattern = usePatternsStore((s) => s.setSelectedPattern);
  const loading = usePatternsStore((s) => s.loading);
  const setLoading = usePatternsStore((s) => s.setLoading);

  useEffect(() => {
    if (patterns.length > 0) return;
    setLoading(true);
    patternsApi.list().then((res) => {
      if (res.success) {
        setPatterns(res.data);
      }
      setLoading(false);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (pattern: Pattern) => {
    setSelectedPattern(pattern);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Patterns</h1>
        <p className="mt-1 text-sm text-gray-500">
          Browse and explore cloud migration transformation patterns
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-400">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" />
          <span className="ml-3 text-sm">Loading patterns...</span>
        </div>
      ) : selectedPattern ? (
        <PatternDetail
          pattern={selectedPattern}
          onBack={() => setSelectedPattern(null)}
        />
      ) : (
        <PatternBrowser onSelect={handleSelect} />
      )}
    </div>
  );
}
