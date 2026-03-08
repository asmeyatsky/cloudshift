import { useState } from "react";
import {
  X,
  GitBranch,
  FolderOpen,
  ArrowRight,
  Loader2,
  Download,
} from "lucide-react";
import type { CloudProvider } from "../types";
import {
  useProjectStore,
  useManifestStore,
  useOperationStore,
  useValidationStore,
} from "../store";

interface Props {
  open: boolean;
  onClose: () => void;
}

type ImportMode = "git" | "local";

const PROVIDERS: { value: CloudProvider; label: string }[] = [
  { value: "aws", label: "AWS" },
  { value: "gcp", label: "GCP" },
  { value: "azure", label: "Azure" },
];

export default function ImportProjectModal({ open, onClose }: Props) {
  const [mode, setMode] = useState<ImportMode>("git");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [localPath, setLocalPath] = useState("");
  const [projectName, setProjectName] = useState("");
  const [source, setSource] = useState<CloudProvider>("aws");
  const [target, setTarget] = useState<CloudProvider>("gcp");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");

  const setProjects = useProjectStore((s) => s.setProjects);
  const projects = useProjectStore((s) => s.projects);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const setEntries = useManifestStore((s) => s.setEntries);
  const resetOps = useOperationStore((s) => s.reset);
  const setValidationResult = useValidationStore((s) => s.setResult);

  const deriveName = (input: string) => {
    if (!input) return "";
    // Extract repo name from URL or path
    const cleaned = input.replace(/\.git$/, "").replace(/\/$/, "");
    const parts = cleaned.split(/[/\\]/);
    return parts[parts.length - 1] || "";
  };

  const handleUrlChange = (url: string) => {
    setRepoUrl(url);
    if (!projectName || projectName === deriveName(repoUrl)) {
      setProjectName(deriveName(url));
    }
  };

  const handlePathChange = (path: string) => {
    setLocalPath(path);
    if (!projectName || projectName === deriveName(localPath)) {
      setProjectName(deriveName(path));
    }
  };

  const handleImport = async () => {
    setError("");

    const inputPath = mode === "git" ? repoUrl : localPath;
    if (!inputPath.trim()) {
      setError(mode === "git" ? "Enter a repository URL" : "Enter a file path");
      return;
    }
    if (!projectName.trim()) {
      setError("Enter a project name");
      return;
    }
    if (source === target) {
      setError("Source and target providers must be different");
      return;
    }

    setImporting(true);

    // Simulate import delay (clone / index)
    await new Promise((r) => setTimeout(r, 2000));

    const newProject = {
      id: `proj-${Date.now().toString(36)}`,
      name: projectName.trim(),
      path: mode === "git" ? `/tmp/cloudshift/${projectName.trim()}` : localPath.trim(),
      sourceProvider: source,
      targetProvider: target,
      config: {
        excludePaths: ["node_modules/**", ".git/**", "dist/**", "__pycache__/**"],
        includePatterns: ["**/*.py", "**/*.ts", "**/*.js", "**/*.tf", "**/*.yaml", "**/*.json"],
        autoValidate: true,
        dryRun: false,
        maxConcurrency: 4,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    // Clear previous pipeline state
    resetOps();
    setValidationResult(null);
    setEntries([]);

    // Add project and set active
    setProjects([...projects, newProject]);
    setActiveProject(newProject);

    setImporting(false);
    onClose();

    // Reset form
    setRepoUrl("");
    setLocalPath("");
    setProjectName("");
    setBranch("main");
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg overflow-hidden rounded-2xl border border-white/[0.08] bg-surface-50 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-accent-purple">
              <Download className="h-4 w-4 text-white" />
            </div>
            <h2 className="text-sm font-semibold text-white">Import Project</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-white/[0.06] hover:text-gray-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Mode tabs */}
          <div className="flex rounded-lg bg-surface-200/60 p-1">
            <button
              onClick={() => setMode("git")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-all ${
                mode === "git"
                  ? "bg-surface-100 text-white shadow"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <GitBranch className="h-3.5 w-3.5" />
              Git Repository
            </button>
            <button
              onClick={() => setMode("local")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-all ${
                mode === "local"
                  ? "bg-surface-100 text-white shadow"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <FolderOpen className="h-3.5 w-3.5" />
              Local Path
            </button>
          </div>

          {/* Source input */}
          {mode === "git" ? (
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-400">
                  Repository URL
                </label>
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => handleUrlChange(e.target.value)}
                  placeholder="https://github.com/org/repo.git"
                  className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-400">
                  Branch
                </label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
                />
              </div>
            </div>
          ) : (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-400">
                Directory Path
              </label>
              <input
                type="text"
                value={localPath}
                onChange={(e) => handlePathChange(e.target.value)}
                placeholder="/Users/you/projects/my-service"
                className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              />
            </div>
          )}

          {/* Project name */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-400">
              Project Name
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="my-service"
              className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
            />
          </div>

          {/* Providers */}
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-medium text-gray-400">
                Source Provider
              </label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value as CloudProvider)}
                className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              >
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex h-10 items-center">
              <ArrowRight className="h-4 w-4 text-gray-600" />
            </div>

            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-medium text-gray-400">
                Target Provider
              </label>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value as CloudProvider)}
                className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              >
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <p className="rounded-lg border border-red-500/20 bg-red-500/[0.06] px-3 py-2 text-xs text-red-400">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-white/[0.06] px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-white/[0.08] px-4 py-2 text-sm font-medium text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={importing}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary-600 to-accent-purple px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-primary-500/20 hover:brightness-110 disabled:opacity-50"
          >
            {importing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {mode === "git" ? "Cloning..." : "Importing..."}
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Import Project
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
