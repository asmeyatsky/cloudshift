import { useState, useMemo } from "react";
import { Search, Tag, Blocks } from "lucide-react";
import { usePatternsStore } from "../../store";
import type { Pattern } from "../../types";

interface Props {
  onSelect: (pattern: Pattern) => void;
}

export default function PatternBrowser({ onSelect }: Props) {
  const patterns = usePatternsStore((s) => s.patterns);
  const filter = usePatternsStore((s) => s.filter);
  const setFilter = usePatternsStore((s) => s.setFilter);

  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const categories = useMemo(
    () => [...new Set(patterns.map((p) => p.category))].sort(),
    [patterns],
  );

  const filtered = useMemo(() => {
    let result = [...patterns];
    if (filter.category) {
      result = result.filter((p) => p.category === filter.category);
    }
    if (filter.provider) {
      result = result.filter(
        (p) =>
          p.sourceProvider === filter.provider ||
          p.targetProvider === filter.provider,
      );
    }
    if (filter.search) {
      const q = filter.search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    return result;
  }, [patterns, filter]);

  const grouped = useMemo(() => {
    const map = new Map<string, Pattern[]>();
    for (const p of filtered) {
      const list = map.get(p.category) ?? [];
      list.push(p);
      map.set(p.category, list);
    }
    return map;
  }, [filtered]);

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search patterns..."
            value={filter.search}
            onChange={(e) => setFilter({ search: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <select
          value={filter.category}
          onChange={(e) => setFilter({ category: e.target.value })}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={filter.provider}
          onChange={(e) => setFilter({ provider: e.target.value })}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">All Providers</option>
          <option value="aws">AWS</option>
          <option value="azure">Azure</option>
          <option value="gcp">GCP</option>
        </select>
      </div>

      {/* Grouped pattern list */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16 text-gray-400">
          <Blocks className="mb-3 h-10 w-10" />
          <p className="text-sm">No patterns found.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {[...grouped.entries()].map(([category, items]) => (
            <div
              key={category}
              className="overflow-hidden rounded-xl border border-gray-200 bg-white"
            >
              <button
                onClick={() =>
                  setExpandedCategory(
                    expandedCategory === category ? null : category,
                  )
                }
                className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <span className="flex items-center gap-2">
                  <Blocks className="h-4 w-4 text-gray-400" />
                  {category}
                </span>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                  {items.length}
                </span>
              </button>

              {(expandedCategory === category || !filter.category) && (
                <div className="divide-y divide-gray-100 border-t border-gray-100">
                  {items.map((pattern) => (
                    <button
                      key={pattern.id}
                      onClick={() => onSelect(pattern)}
                      className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-800">
                          {pattern.name}
                        </p>
                        <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
                          {pattern.description}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-blue-700">
                            {pattern.sourceProvider}
                          </span>
                          <span className="text-xs text-gray-400">-&gt;</span>
                          <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-emerald-700">
                            {pattern.targetProvider}
                          </span>
                          {pattern.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="inline-flex items-center gap-0.5 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500"
                            >
                              <Tag className="h-2.5 w-2.5" />
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400">
        {filtered.length} pattern{filtered.length !== 1 ? "s" : ""} found
      </p>
    </div>
  );
}
