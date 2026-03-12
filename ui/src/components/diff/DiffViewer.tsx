import { useState } from "react";
import JSZip from "jszip";
import { DiffEditor } from "@monaco-editor/react";
import { ChevronDown, ChevronRight, FileCode, Plus, Minus, Download, Archive } from "lucide-react";
import type { FileDiff } from "../../types";

function downloadFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

interface Props {
  diffs: FileDiff[];
  /** Label for left side (original/source), e.g. "AWS code" or "Azure code". */
  sourceLabel?: string;
  /** Label for right side (refactored output), e.g. "GCP code". */
  targetLabel?: string;
}

export default function DiffViewer({ diffs, sourceLabel = "Original", targetLabel = "Refactored" }: Props) {
  const [expandedFile, setExpandedFile] = useState<string | null>(
    diffs[0]?.filePath ?? null,
  );

  if (diffs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-white/[0.06] bg-surface-100 py-16 text-gray-600">
        <FileCode className="mb-3 h-10 w-10" />
        <p className="text-sm text-gray-400">No diffs to display.</p>
        <p className="text-xs">Run the pipeline (Scan → Plan → Apply) to see AWS/Azure code refactored to GCP.</p>
      </div>
    );
  }

  async function downloadAllAsZip() {
    const zip = new JSZip();
    for (const d of diffs) {
      zip.file(d.filePath, d.modified);
    }
    const blob = await zip.generateAsync({ type: "blob" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "refactored-gcp-code.zip";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={downloadAllAsZip}
          className="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-surface-100 px-4 py-2 text-sm text-gray-300 hover:bg-white/[0.06] hover:text-white"
        >
          <Archive className="h-4 w-4" />
          Download all as ZIP
        </button>
      </div>
      {diffs.map((diff) => {
        const isExpanded = expandedFile === diff.filePath;
        return (
          <div
            key={diff.filePath}
            className="overflow-hidden rounded-xl border border-white/[0.06] bg-surface-100"
          >
            {/* File header */}
            <button
              onClick={() =>
                setExpandedFile(isExpanded ? null : diff.filePath)
              }
              className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-white/[0.03]"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 shrink-0 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0 text-gray-500" />
              )}
              <FileCode className="h-4 w-4 shrink-0 text-gray-500" />
              <span className="flex-1 truncate font-mono text-xs text-gray-300">
                {diff.filePath}
              </span>
              <span className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-0.5 text-green-400">
                  <Plus className="h-3 w-3" />
                  {diff.stats.additions}
                </span>
                <span className="flex items-center gap-0.5 text-red-400">
                  <Minus className="h-3 w-3" />
                  {diff.stats.deletions}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    const base = diff.filePath.replace(/^.*[/\\]/, "");
                    downloadFile(base || "file", diff.modified);
                  }}
                  className="flex items-center gap-1 rounded px-2 py-1 text-gray-400 hover:bg-white/[0.06] hover:text-white"
                  title="Download refactored (GCP) file"
                >
                  <Download className="h-3 w-3" />
                  Download
                </button>
              </span>
            </button>

            {/* Monaco diff editor: left = source (AWS/Azure), right = GCP */}
            {isExpanded && (
              <div className="border-t border-white/[0.06]">
                <div className="flex border-b border-white/[0.06] bg-surface-200/50 px-3 py-2 text-xs font-medium text-gray-500">
                  <span className="w-1/2">{sourceLabel}</span>
                  <span className="w-1/2">{targetLabel}</span>
                </div>
                <DiffEditor
                  height="480px"
                  language={detectLanguage(diff.filePath)}
                  original={diff.original}
                  modified={diff.modified}
                  theme="vs-dark"
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
