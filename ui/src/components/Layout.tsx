import { useState } from "react";
import { Outlet, NavLink } from "react-router";
import {
  LayoutDashboard,
  FileText,
  GitCompare,
  ShieldCheck,
  Blocks,
  Settings,
  FileBarChart,
  Zap,
  Brain,
  Wifi,
  WifiOff,
  ChevronDown,
  Plus,
  Check,
  ArrowRight,
  LogOut,
} from "lucide-react";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  useProjectStore,
  useOperationStore,
  useManifestStore,
  useValidationStore,
} from "../store";
import { useAuthStore } from "../store/authStore";
import ImportProjectModal from "./ImportProjectModal";

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Pipeline" },
  { to: "/manifest", icon: FileText, label: "Manifest" },
  { to: "/diff", icon: GitCompare, label: "Diff Viewer" },
  { to: "/validation", icon: ShieldCheck, label: "Validation" },
  { to: "/patterns", icon: Blocks, label: "Patterns" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/report", icon: FileBarChart, label: "Report" },
] as const;

export default function Layout() {
  const { connected } = useWebSocket();
  const progress = useOperationStore((s) => s.progress);
  const running = useOperationStore((s) => s.running);
  const projects = useProjectStore((s) => s.projects);
  const activeProject = useProjectStore((s) => s.activeProject);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const resetOps = useOperationStore((s) => s.reset);
  const setEntries = useManifestStore((s) => s.setEntries);
  const setValidationResult = useValidationStore((s) => s.setResult);

  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const deploymentMode = useAuthStore((s) => s.deploymentMode);
  const authMode = useAuthStore((s) => s.authMode);
  const logout = useAuthStore((s) => s.logout);

  const switchProject = (projectId: string) => {
    const proj = projects.find((p) => p.id === projectId);
    if (proj && proj.id !== activeProject?.id) {
      resetOps();
      setValidationResult(null);
      setEntries([]);
      setActiveProject(proj);
    }
    setProjectDropdownOpen(false);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-surface-0">
      {/* Sidebar */}
      <aside className="flex w-72 flex-col border-r border-white/[0.06] bg-surface-50">
        {/* Brand */}
        <div className="flex h-18 items-center gap-3 border-b border-white/[0.06] px-6 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-accent-purple shadow-lg shadow-primary-500/20">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-white">
              CloudShift
            </span>
            <p className="text-xs font-semibold uppercase tracking-[0.15em] text-primary-400/80">
              Agent
            </p>
          </div>
        </div>

        {/* Project Selector */}
        <div className="border-b border-white/[0.06] px-4 py-4">
          <div className="relative">
            <button
              onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
              className="flex w-full items-center justify-between rounded-xl bg-surface-200/60 px-4 py-3 text-left transition-all hover:bg-surface-200"
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-600">
                  Project
                </p>
                {activeProject ? (
                  <div className="mt-0.5 flex items-center gap-2">
                    <p className="truncate text-sm font-medium text-gray-200">
                      {activeProject.name}
                    </p>
                    <span className="font-mono text-xs uppercase text-primary-400/70">
                      {activeProject.sourceProvider}
                    </span>
                    <ArrowRight className="h-3 w-3 text-gray-700" />
                    <span className="font-mono text-xs uppercase text-accent-green/70">
                      {activeProject.targetProvider}
                    </span>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No project selected</p>
                )}
              </div>
              <ChevronDown
                className={`h-4 w-4 shrink-0 text-gray-600 transition-transform ${
                  projectDropdownOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {projectDropdownOpen && (
              <div className="absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden rounded-xl border border-white/[0.08] bg-surface-100 shadow-xl">
                <div className="max-h-52 overflow-y-auto py-1">
                  {projects.map((proj) => (
                    <button
                      key={proj.id}
                      onClick={() => switchProject(proj.id)}
                      className={`flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-white/[0.04] ${
                        proj.id === activeProject?.id
                          ? "text-primary-400"
                          : "text-gray-400"
                      }`}
                    >
                      {proj.id === activeProject?.id ? (
                        <Check className="h-4 w-4 shrink-0 text-primary-400" />
                      ) : (
                        <span className="h-4 w-4 shrink-0" />
                      )}
                      <span className="truncate font-medium">{proj.name}</span>
                      <span className="ml-auto shrink-0 font-mono text-xs uppercase text-gray-600">
                        {proj.sourceProvider} → {proj.targetProvider}
                      </span>
                    </button>
                  ))}
                </div>
                <div className="border-t border-white/[0.06]">
                  <button
                    onClick={() => {
                      setProjectDropdownOpen(false);
                      setImportOpen(true);
                    }}
                    className="flex w-full items-center gap-3 px-4 py-3 text-sm font-medium text-accent-cyan transition-colors hover:bg-white/[0.04]"
                  >
                    <Plus className="h-4 w-4" />
                    Import Project
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-5">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-primary-500/10 text-primary-400 shadow-[inset_0_0_0_1px_rgba(6,182,212,0.12)]"
                    : "text-gray-500 hover:bg-white/[0.04] hover:text-gray-300"
                }`
              }
            >
              <Icon className="h-5 w-5 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Deployment & LLM */}
        <div className="border-t border-white/[0.06] px-4 py-4">
          <div className="rounded-xl bg-surface-200/60 px-4 py-3">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-accent-purple" />
              <span className="text-xs font-semibold text-gray-400">
                {deploymentMode === "demo" ? "Demo (Gemini)" : "Client (Ollama)"}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-green opacity-40" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-green" />
              </span>
              <span className="font-mono text-xs text-gray-500">
                {deploymentMode === "demo" ? "Gemini" : "Qwen 2"}
              </span>
            </div>
          </div>

          {authMode === "searce_id" && (
            <p className="mt-3 px-1 text-xs text-gray-500">
              Signed in via IAP
            </p>
          )}
          {authMode === "password" && (
            <button
              onClick={() => logout()}
              className="mt-3 flex w-full items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium text-gray-500 hover:bg-white/[0.04] hover:text-gray-300"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          )}

          <div className="mt-3 flex items-center gap-2 px-1">
            {connected ? (
              <>
                <Wifi className="h-4 w-4 text-accent-green/60" />
                <span className="text-xs text-gray-600">Live</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-red-400/60" />
                <span className="text-xs text-gray-600">Offline</span>
              </>
            )}
          </div>
        </div>

        {/* Progress bar */}
        {running && progress && (
          <div className="border-t border-white/[0.06] px-5 py-4">
            <p className="mb-2 truncate text-xs font-semibold uppercase tracking-wider text-primary-400/80">
              {progress.operation}
            </p>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-300">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-purple transition-all duration-300"
                style={{ width: `${progress.percentage}%` }}
              />
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <p className="truncate text-xs text-gray-600">
                {progress.message}
              </p>
              <p className="font-mono text-xs text-gray-500">
                {progress.percentage}%
              </p>
            </div>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

      {/* Import modal */}
      <ImportProjectModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
      />
    </div>
  );
}
