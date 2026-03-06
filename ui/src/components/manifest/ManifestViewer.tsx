import { useState, useMemo } from "react";
import { Search, Filter, ChevronUp, ChevronDown } from "lucide-react";
import { useManifestStore } from "../../store";
import ManifestEntryRow from "./ManifestEntry";
import type { ManifestEntry as ManifestEntryType } from "../../types";

type SortKey = "filePath" | "resourceType" | "status" | "updatedAt";
type SortDir = "asc" | "desc";

const STATUS_OPTIONS = [
  "",
  "pending",
  "scanned",
  "planned",
  "applied",
  "validated",
  "skipped",
];

export default function ManifestViewer() {
  const entries = useManifestStore((s) => s.entries);
  const filter = useManifestStore((s) => s.filter);
  const setFilter = useManifestStore((s) => s.setFilter);
  const setSelectedEntry = useManifestStore((s) => s.setSelectedEntry);

  const [sortKey, setSortKey] = useState<SortKey>("filePath");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col)
      return <ChevronUp className="h-3 w-3 text-gray-300" />;
    return sortDir === "asc" ? (
      <ChevronUp className="h-3 w-3 text-primary-600" />
    ) : (
      <ChevronDown className="h-3 w-3 text-primary-600" />
    );
  };

  const filtered = useMemo(() => {
    let result = [...entries];

    if (filter.status) {
      result = result.filter((e) => e.status === filter.status);
    }
    if (filter.resourceType) {
      result = result.filter((e) =>
        e.resourceType
          .toLowerCase()
          .includes(filter.resourceType.toLowerCase()),
      );
    }
    if (filter.search) {
      const q = filter.search.toLowerCase();
      result = result.filter(
        (e) =>
          e.filePath.toLowerCase().includes(q) ||
          e.resourceType.toLowerCase().includes(q),
      );
    }

    result.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [entries, filter, sortKey, sortDir]);

  const resourceTypes = useMemo(
    () => [...new Set(entries.map((e) => e.resourceType))].sort(),
    [entries],
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search files or resource types..."
            value={filter.search}
            onChange={(e) => setFilter({ search: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={filter.status}
            onChange={(e) => setFilter({ status: e.target.value })}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s || "All Statuses"}
              </option>
            ))}
          </select>
          <select
            value={filter.resourceType}
            onChange={(e) => setFilter({ resourceType: e.target.value })}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">All Types</option>
            {resourceTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {(
                [
                  ["filePath", "File Path"],
                  ["resourceType", "Resource Type"],
                  ["status", "Status"],
                  ["updatedAt", "Updated"],
                ] as const
              ).map(([key, label]) => (
                <th
                  key={key}
                  className="cursor-pointer px-4 py-3 hover:text-gray-700"
                  onClick={() => toggleSort(key)}
                >
                  <span className="flex items-center gap-1">
                    {label}
                    <SortIcon col={key} />
                  </span>
                </th>
              ))}
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-gray-400"
                >
                  No manifest entries found.
                </td>
              </tr>
            ) : (
              filtered.map((entry: ManifestEntryType) => (
                <ManifestEntryRow
                  key={entry.id}
                  entry={entry}
                  onSelect={() => setSelectedEntry(entry)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400">
        Showing {filtered.length} of {entries.length} entries
      </p>
    </div>
  );
}
