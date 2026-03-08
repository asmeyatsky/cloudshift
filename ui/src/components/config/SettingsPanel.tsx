import { useState } from "react";
import { Save, RotateCcw, Plus, X } from "lucide-react";
import { useProjectStore } from "../../store";
import { projectApi } from "../../services/api";
import type { ProjectConfig } from "../../types";

export default function SettingsPanel() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);

  const [config, setConfig] = useState<ProjectConfig>(
    activeProject?.config ?? {
      excludePaths: [],
      includePatterns: [],
      autoValidate: true,
      dryRun: false,
      maxConcurrency: 4,
    },
  );

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [newExclude, setNewExclude] = useState("");
  const [newInclude, setNewInclude] = useState("");

  const handleSave = async () => {
    if (!activeProject) return;
    setSaving(true);
    const res = await projectApi.updateConfig(activeProject.id, config);
    if (res.success) {
      setActiveProject({ ...activeProject, config: res.data });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
    setSaving(false);
  };

  const handleReset = () => {
    if (activeProject) {
      setConfig(activeProject.config);
    }
  };

  const addExclude = () => {
    if (newExclude.trim()) {
      setConfig((c) => ({
        ...c,
        excludePaths: [...c.excludePaths, newExclude.trim()],
      }));
      setNewExclude("");
    }
  };

  const removeExclude = (idx: number) => {
    setConfig((c) => ({
      ...c,
      excludePaths: c.excludePaths.filter((_, i) => i !== idx),
    }));
  };

  const addInclude = () => {
    if (newInclude.trim()) {
      setConfig((c) => ({
        ...c,
        includePatterns: [...c.includePatterns, newInclude.trim()],
      }));
      setNewInclude("");
    }
  };

  const removeInclude = (idx: number) => {
    setConfig((c) => ({
      ...c,
      includePatterns: c.includePatterns.filter((_, i) => i !== idx),
    }));
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-white/[0.06] bg-surface-100 py-16 text-gray-600">
        <p className="text-sm text-gray-400">No active project selected.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* Project info */}
      <div className="rounded-xl border border-white/[0.06] bg-surface-100 p-6">
        <h3 className="text-sm font-semibold text-gray-300">Project</h3>
        <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-600">Name</p>
            <p className="font-medium text-white">{activeProject.name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Path</p>
            <p className="truncate font-mono text-xs text-gray-400">
              {activeProject.path}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-600">Source</p>
            <span className="rounded bg-blue-500/10 px-2 py-0.5 text-xs font-medium uppercase text-blue-400">
              {activeProject.sourceProvider}
            </span>
          </div>
          <div>
            <p className="text-xs text-gray-600">Target</p>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-medium uppercase text-emerald-400">
              {activeProject.targetProvider}
            </span>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="rounded-xl border border-white/[0.06] bg-surface-100 p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-300">
          Configuration
        </h3>

        <div className="space-y-6">
          {/* Toggles */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-300">
                Auto-validate
              </p>
              <p className="text-xs text-gray-600">
                Run validation automatically after apply
              </p>
            </div>
            <button
              onClick={() =>
                setConfig((c) => ({ ...c, autoValidate: !c.autoValidate }))
              }
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors ${
                config.autoValidate
                  ? "bg-primary-600"
                  : "bg-surface-400"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  config.autoValidate
                    ? "translate-x-[22px]"
                    : "translate-x-0.5"
                } mt-0.5`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-300">Dry run</p>
              <p className="text-xs text-gray-600">
                Preview changes without modifying files
              </p>
            </div>
            <button
              onClick={() =>
                setConfig((c) => ({ ...c, dryRun: !c.dryRun }))
              }
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors ${
                config.dryRun ? "bg-primary-600" : "bg-surface-400"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  config.dryRun ? "translate-x-[22px]" : "translate-x-0.5"
                } mt-0.5`}
              />
            </button>
          </div>

          {/* Max concurrency */}
          <div>
            <label className="text-sm font-medium text-gray-300">
              Max Concurrency
            </label>
            <p className="mb-2 text-xs text-gray-600">
              Maximum parallel transformations
            </p>
            <input
              type="number"
              min={1}
              max={32}
              value={config.maxConcurrency}
              onChange={(e) =>
                setConfig((c) => ({
                  ...c,
                  maxConcurrency: parseInt(e.target.value, 10) || 1,
                }))
              }
              className="w-24 rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-2 text-sm text-gray-200 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
            />
          </div>

          {/* Exclude paths */}
          <div>
            <label className="text-sm font-medium text-gray-300">
              Exclude Paths
            </label>
            <p className="mb-2 text-xs text-gray-600">
              Glob patterns for paths to exclude from scanning
            </p>
            <div className="flex flex-wrap gap-1.5">
              {config.excludePaths.map((p, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded-full bg-white/[0.06] px-2.5 py-1 text-xs text-gray-400"
                >
                  <span className="font-mono">{p}</span>
                  <button
                    onClick={() => removeExclude(i)}
                    className="text-gray-600 hover:text-gray-300"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={newExclude}
                onChange={(e) => setNewExclude(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addExclude()}
                placeholder="e.g., node_modules/**"
                className="flex-1 rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-1.5 font-mono text-xs text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              />
              <button
                onClick={addExclude}
                className="rounded-lg border border-white/[0.08] px-2 py-1.5 text-gray-500 hover:bg-white/[0.06] hover:text-gray-300"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Include patterns */}
          <div>
            <label className="text-sm font-medium text-gray-300">
              Include Patterns
            </label>
            <p className="mb-2 text-xs text-gray-600">
              Glob patterns for files to include
            </p>
            <div className="flex flex-wrap gap-1.5">
              {config.includePatterns.map((p, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded-full bg-white/[0.06] px-2.5 py-1 text-xs text-gray-400"
                >
                  <span className="font-mono">{p}</span>
                  <button
                    onClick={() => removeInclude(i)}
                    className="text-gray-600 hover:text-gray-300"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={newInclude}
                onChange={(e) => setNewInclude(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addInclude()}
                placeholder="e.g., **/*.tf"
                className="flex-1 rounded-lg border border-white/[0.08] bg-surface-200 px-3 py-1.5 font-mono text-xs text-gray-200 placeholder:text-gray-600 focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              />
              <button
                onClick={addInclude}
                className="rounded-lg border border-white/[0.08] px-2 py-1.5 text-gray-500 hover:bg-white/[0.06] hover:text-gray-300"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3">
        {saved && (
          <span className="text-sm text-accent-green">Settings saved!</span>
        )}
        <button
          onClick={handleReset}
          className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] px-4 py-2 text-sm font-medium text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
        >
          <RotateCcw className="h-4 w-4" />
          Reset
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary-600 to-primary-500 px-4 py-2 text-sm font-medium text-white hover:shadow-lg hover:shadow-primary-500/20 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
