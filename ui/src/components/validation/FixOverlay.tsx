import { useState, useEffect } from "react";
import { X, Sparkles, Check, XCircle } from "lucide-react";
import { DiffEditor } from "@monaco-editor/react";
import type { ValidationIssue } from "../../types";
import type { FixData } from "../../seed";

interface Props {
  issue: ValidationIssue;
  fixData: FixData;
  onAccept: () => void;
  onDismiss: () => void;
}

export default function FixOverlay({
  issue,
  fixData,
  onAccept,
  onDismiss,
}: Props) {
  const [phase, setPhase] = useState<"analyzing" | "ready">("analyzing");

  useEffect(() => {
    const timer = setTimeout(() => setPhase("ready"), 1800);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="flex h-[85vh] w-[90vw] max-w-6xl flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-surface-50 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent-purple to-accent-cyan">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">
                Agent Fix — {issue.code}
              </h2>
              <p className="text-xs text-gray-500">
                {issue.filePath}:{issue.line}
              </p>
            </div>
          </div>
          <button
            onClick={onDismiss}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-white/[0.06] hover:text-gray-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Issue context */}
        <div className="border-b border-white/[0.06] px-6 py-3">
          <p className="text-xs text-gray-400">{issue.message}</p>
          {issue.suggestion && (
            <p className="mt-1 text-xs text-accent-cyan">
              Suggestion: {issue.suggestion}
            </p>
          )}
        </div>

        {/* Editor area */}
        <div className="relative flex-1">
          {phase === "analyzing" ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <div className="relative">
                <div className="h-12 w-12 animate-spin rounded-full border-2 border-white/[0.06] border-t-accent-purple" />
                <Sparkles className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 text-accent-purple" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-white">
                  Agent analyzing issue...
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  Generating fix for {issue.code} in{" "}
                  {issue.filePath.split("/").pop()}
                </p>
              </div>
              <div className="h-1 w-48 overflow-hidden rounded-full bg-white/[0.06]">
                <div className="animate-scan h-full w-1/3 rounded-full bg-gradient-to-r from-accent-purple to-accent-cyan" />
              </div>
            </div>
          ) : (
            <DiffEditor
              original={fixData.original}
              modified={fixData.fixed}
              language={fixData.language}
              theme="vs-dark"
              options={{
                readOnly: true,
                renderSideBySide: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 13,
                lineNumbers: "on",
                renderOverviewRuler: false,
                padding: { top: 12 },
              }}
            />
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-white/[0.06] px-6 py-4">
          <p className="text-xs text-gray-600">
            {phase === "analyzing"
              ? "Preparing diff..."
              : "Review the proposed changes before accepting"}
          </p>
          <div className="flex gap-3">
            <button
              onClick={onDismiss}
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] px-4 py-2 text-sm font-medium text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
            >
              <XCircle className="h-4 w-4" />
              Dismiss
            </button>
            <button
              onClick={onAccept}
              disabled={phase === "analyzing"}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-accent-green to-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:brightness-110 disabled:opacity-40 disabled:hover:brightness-100"
            >
              <Check className="h-4 w-4" />
              Accept Fix
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
