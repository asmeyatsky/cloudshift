import { useState } from "react";
import {
  X,
  GitBranch,
  FolderOpen,
  FileCode,
  ArrowRight,
  Loader2,
  Download,
} from "lucide-react";
import type { CloudProvider } from "../types";
import { projectApi } from "../services/api";
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

type ImportMode = "git" | "local" | "snippet";

/** Cloud-to-cloud: only migrate TO GCP (AWS→GCP, Azure→GCP). */
const SOURCE_PROVIDERS: { value: CloudProvider; label: string }[] = [
  { value: "aws", label: "AWS" },
  { value: "azure", label: "Azure" },
];
const TARGET_PROVIDER_GCP: { value: CloudProvider; label: string } = { value: "gcp", label: "GCP" };

export default function ImportProjectModal({ open, onClose }: Props) {
  const [mode, setMode] = useState<ImportMode>("git");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [subpath, setSubpath] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [projectName, setProjectName] = useState("");
  const [source, setSource] = useState<CloudProvider>("aws");
  const target: CloudProvider = "gcp"; // GCP only for migration target
  const [snippetContent, setSnippetContent] = useState("");
  const [snippetLanguage, setSnippetLanguage] = useState("PYTHON");
  const [snippetFilename, setSnippetFilename] = useState("");
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

  /** Derive subfolder from GitHub/GitLab tree URL (e.g. .../tree/main/python/ -> "python"). */
  const deriveSubpathFromUrl = (url: string): string => {
    const u = url.trim();
    const treeMatch = u.match(/\/tree\/[^/]+\/([^/#?]+)/);
    const treePath = treeMatch?.[1];
    if (treePath) return treePath.replace(/\/$/, "").split("/")[0] ?? "";
    const blobMatch = u.match(/\/blob\/[^/]+\/([^/#?]+)/);
    const blobPath = blobMatch?.[1];
    if (blobPath) return blobPath.replace(/\/$/, "").split("/")[0] ?? "";
    return "";
  };

  const handleUrlChange = (url: string) => {
    setRepoUrl(url);
    if (!projectName || projectName === deriveName(repoUrl)) {
      setProjectName(deriveName(url));
    }
    const derived = deriveSubpathFromUrl(url);
    if (derived) setSubpath(derived);
  };

  const handlePathChange = (path: string) => {
    setLocalPath(path);
    if (!projectName || projectName === deriveName(localPath)) {
      setProjectName(deriveName(path));
    }
  };

  const handleImport = async () => {
    setError("");

    if (mode === "snippet") {
      if (!snippetContent.trim()) {
        setError("Paste your code snippet");
        return;
      }
      if (!projectName.trim()) {
        setError("Enter a project name");
        return;
      }
      setImporting(true);
      const res = await projectApi.createFromSnippet({
        name: projectName.trim(),
        content: snippetContent.trim(),
        language: snippetLanguage,
        source_provider: source.toUpperCase(),
        target_provider: target.toUpperCase(),
        filename: snippetFilename.trim() || undefined,
      });
      setImporting(false);
      if (!res.success) {
        setError(res.error ?? "Failed to create project from snippet");
        return;
      }
      const newProject = {
        id: res.data.project_id,
        name: res.data.name,
        path: res.data.root_path,
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
      resetOps();
      setValidationResult(null);
      setEntries([]);
      setProjects([...projects, newProject]);
      setActiveProject(newProject);
      onClose();
      setSnippetContent("");
      setSnippetFilename("");
      setProjectName("");
      return;
    }

    if (mode === "git") {
      if (!repoUrl.trim()) {
        setError("Enter a repository URL");
        return;
      }
      if (!projectName.trim()) {
        setError("Enter a project name");
        return;
      }
      setImporting(true);
      const res = await projectApi.createFromGit({
        repo_url: repoUrl.trim(),
        branch: branch.trim() || "main",
        name: projectName.trim(),
        subpath: subpath.trim() || undefined,
        source_provider: source.toUpperCase(),
        target_provider: target.toUpperCase(),
      });
      setImporting(false);
      if (!res.success) {
        setError(res.error ?? "Failed to clone repository");
        return;
      }
      const newProject = {
        id: res.data.project_id,
        name: res.data.name,
        path: res.data.root_path,
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
      resetOps();
      setValidationResult(null);
      setEntries([]);
      setProjects([...projects, newProject]);
      setActiveProject(newProject);
      onClose();
      setRepoUrl("");
      setProjectName("");
      setBranch("main");
      setSubpath("");
      return;
    }

    if (mode === "local") {
      if (!localPath.trim()) {
        setError("Enter a file path");
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
    }

    setImporting(true);
    await new Promise((r) => setTimeout(r, 500));

    const newProject = {
      id: `proj-${Date.now().toString(36)}`,
      name: projectName.trim(),
      path: localPath.trim(),
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

    resetOps();
    setValidationResult(null);
    setEntries([]);
    setProjects([...projects, newProject]);
    setActiveProject(newProject);
    setImporting(false);
    onClose();
    setLocalPath("");
    setProjectName("");
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
              Git Repo
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
            <button
              onClick={() => setMode("snippet")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-all ${
                mode === "snippet"
                  ? "bg-surface-100 text-white shadow"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <FileCode className="h-3.5 w-3.5" />
              Code Snippet
            </button>
          </div>

          {/* Source input */}
          {mode === "snippet" ? (
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-400">
                  Paste code
                </label>
                <textarea
                  value={snippetContent}
                  onChange={(e) => setSnippetContent(e.target.value)}
                  placeholder="Paste your source file content here..."
                  rows={8}
                  className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-gray-400">
                    Language
                  </label>
                  <select
                    value={snippetLanguage}
                    onChange={(e) => setSnippetLanguage(e.target.value)}
                    className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
                  >
                    <option value="PYTHON">Python</option>
                    <option value="TYPESCRIPT">TypeScript</option>
                    <option value="HCL">HCL (Terraform)</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-gray-400">
                    Filename (optional)
                  </label>
                  <input
                    type="text"
                    value={snippetFilename}
                    onChange={(e) => setSnippetFilename(e.target.value)}
                    placeholder="main.py"
                    className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
                  />
                </div>
              </div>
            </div>
          ) : mode === "git" ? (
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
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-400">
                  Subfolder to scan (optional)
                </label>
                <input
                  type="text"
                  value={subpath}
                  onChange={(e) => setSubpath(e.target.value)}
                  placeholder="e.g. python — only this folder is used as project root"
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

          {/* Cloud-to-cloud: AWS or Azure → GCP only */}
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-medium text-gray-400">
                Source Cloud
              </label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value as CloudProvider)}
                className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              >
                {SOURCE_PROVIDERS.map((p) => (
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
                Target Cloud
              </label>
              <select
                value={target}
                className="w-full rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2.5 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
                disabled
              >
                <option value={TARGET_PROVIDER_GCP.value}>{TARGET_PROVIDER_GCP.label}</option>
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
