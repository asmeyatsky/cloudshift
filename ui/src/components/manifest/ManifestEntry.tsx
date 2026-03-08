import { Eye, ArrowRight } from "lucide-react";
import type { ManifestEntry as ManifestEntryType, EntryStatus } from "../../types";

const STATUS_STYLES: Record<EntryStatus, string> = {
  pending: "bg-gray-500/10 text-gray-400",
  scanned: "bg-blue-500/10 text-blue-400",
  planned: "bg-amber-500/10 text-amber-400",
  applied: "bg-emerald-500/10 text-emerald-400",
  validated: "bg-green-500/10 text-green-400",
  skipped: "bg-gray-500/10 text-gray-600",
};

interface Props {
  entry: ManifestEntryType;
  onSelect: () => void;
}

export default function ManifestEntryRow({ entry, onSelect }: Props) {
  return (
    <tr className="group transition-colors hover:bg-white/[0.02]">
      <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-gray-400">
        {entry.filePath}
      </td>
      <td className="px-4 py-3">
        <span className="inline-flex items-center gap-1 text-xs text-gray-400">
          {entry.resourceType}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[entry.status]}`}
        >
          {entry.status}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-gray-600">
        {new Date(entry.updatedAt).toLocaleDateString()}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={onSelect}
            className="rounded p-1 text-gray-600 hover:bg-white/[0.06] hover:text-gray-300"
            title="View details"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={onSelect}
            className="rounded p-1 text-gray-600 hover:bg-white/[0.06] hover:text-gray-300"
            title="View transformations"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}
