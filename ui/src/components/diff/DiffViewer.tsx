import { useState } from "react";
import { DiffEditor } from "@monaco-editor/react";
import { ChevronDown, ChevronRight, FileCode, Plus, Minus } from "lucide-react";
import type { FileDiff } from "../../types";

interface Props {
  diffs: FileDiff[];
}

export default function DiffViewer({ diffs }: Props) {
  const [expandedFile, setExpandedFile] = useState<string | null>(
    diffs[0]?.filePath ?? null,
  );

  if (diffs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16 text-gray-400">
        <FileCode className="mb-3 h-10 w-10" />
        <p className="text-sm">No diffs to display.</p>
        <p className="text-xs">Run a plan to generate transformation diffs.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {diffs.map((diff) => {
        const isExpanded = expandedFile === diff.filePath;
        return (
          <div
            key={diff.filePath}
            className="overflow-hidden rounded-xl border border-gray-200 bg-white"
          >
            {/* File header */}
            <button
              onClick={() =>
                setExpandedFile(isExpanded ? null : diff.filePath)
              }
              className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-gray-50"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 shrink-0 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0 text-gray-400" />
              )}
              <FileCode className="h-4 w-4 shrink-0 text-gray-400" />
              <span className="flex-1 truncate font-mono text-xs text-gray-700">
                {diff.filePath}
              </span>
              <span className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-0.5 text-green-600">
                  <Plus className="h-3 w-3" />
                  {diff.stats.additions}
                </span>
                <span className="flex items-center gap-0.5 text-red-500">
                  <Minus className="h-3 w-3" />
                  {diff.stats.deletions}
                </span>
              </span>
            </button>

            {/* Monaco diff editor */}
            {isExpanded && (
              <div className="border-t border-gray-200">
                <DiffEditor
                  height="480px"
                  language={detectLanguage(diff.filePath)}
                  original={diff.original}
                  modified={diff.modified}
                  theme="vs"
                  options={{
                    readOnly: true,
                    renderSideBySide: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    lineNumbers: "on",
                    folding: true,
                    wordWrap: "off",
                    renderOverviewRuler: false,
                    diffWordWrap: "off",
                  }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function detectLanguage(filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase();
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    tf: "hcl",
    hcl: "hcl",
    toml: "ini",
    xml: "xml",
    html: "html",
    css: "css",
    sh: "shell",
    bash: "shell",
    md: "markdown",
  };
  return map[ext ?? ""] ?? "plaintext";
}
