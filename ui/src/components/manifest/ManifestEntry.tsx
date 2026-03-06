import { Eye, ArrowRight } from "lucide-react";
import type { ManifestEntry as ManifestEntryType, EntryStatus } from "../../types";

const STATUS_STYLES: Record<EntryStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  scanned: "bg-blue-100 text-blue-700",
  planned: "bg-amber-100 text-amber-700",
  applied: "bg-emerald-100 text-emerald-700",
  validated: "bg-green-100 text-green-700",
  skipped: "bg-gray-100 text-gray-500",
};

interface Props {
  entry: ManifestEntryType;
  onSelect: () => void;
}

export default function ManifestEntryRow({ entry, onSelect }: Props) {
  return (
    <tr className="group transition-colors hover:bg-gray-50">
      <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-gray-700">
        {entry.filePath}
      </td>
      <td className="px-4 py-3">
        <span className="inline-flex items-center gap-1 text-xs text-gray-600">
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
      <td className="px-4 py-3 text-xs text-gray-500">
        {new Date(entry.updatedAt).toLocaleDateString()}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={onSelect}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            title="View details"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={onSelect}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            title="View transformations"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}
