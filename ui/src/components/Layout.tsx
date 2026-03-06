import { Outlet, NavLink } from "react-router";
import {
  LayoutDashboard,
  FileText,
  GitCompare,
  ShieldCheck,
  Blocks,
  Settings,
  FileBarChart,
  Cloud,
} from "lucide-react";
import { useWebSocket } from "../hooks/useWebSocket";
import { useOperationStore } from "../store";

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/manifest", icon: FileText, label: "Manifest" },
  { to: "/diff", icon: GitCompare, label: "Diff Viewer" },
  { to: "/validation", icon: ShieldCheck, label: "Validation" },
  { to: "/patterns", icon: Blocks, label: "Patterns" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/report", icon: FileBarChart, label: "Report" },
] as const;

export default function Layout() {
  useWebSocket();
  const progress = useOperationStore((s) => s.progress);
  const running = useOperationStore((s) => s.running);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-gray-200 bg-white">
        {/* Brand */}
        <div className="flex h-14 items-center gap-2 border-b border-gray-200 px-4">
          <Cloud className="h-6 w-6 text-primary-600" />
          <span className="text-lg font-semibold tracking-tight text-gray-900">
            CloudShift
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary-50 text-primary-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Progress bar (when an operation is running) */}
        {running && progress && (
          <div className="border-t border-gray-200 px-4 py-3">
            <p className="mb-1 truncate text-xs text-gray-500">
              {progress.message}
            </p>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full rounded-full bg-primary-600 transition-all duration-300"
                style={{ width: `${progress.percentage}%` }}
              />
            </div>
            <p className="mt-1 text-right text-[10px] text-gray-400">
              {progress.current}/{progress.total}
            </p>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
