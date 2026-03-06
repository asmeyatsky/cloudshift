"""Domain service for building a transformation plan from matched patterns."""

from __future__ import annotations

from cloudshift.domain.entities.manifest import ManifestEntry, MigrationManifest
from cloudshift.domain.entities.pattern import Pattern
from cloudshift.domain.value_objects.types import ConfidenceScore


class TransformationPlanner:
    """Creates a :class:`MigrationManifest` from a set of pattern matches."""

    def __init__(self, min_confidence: float = 0.3) -> None:
        self._min_confidence = min_confidence

    def plan(
        self,
        matches: list[tuple[Pattern, str, int, int]],
    ) -> MigrationManifest:
        """Build a manifest from *(pattern, file_path, line_start, line_end)* tuples.

        Matches whose pattern confidence falls below *min_confidence* are
        silently excluded.
        """
        manifest = MigrationManifest()
        for pattern, file_path, line_start, line_end in matches:
            if pattern.confidence.value < self._min_confidence:
                continue
            entry = ManifestEntry(
                file_path=file_path,
                pattern_id=pattern.id,
                source_construct=pattern.source_service,
                target_construct=pattern.target_service,
                confidence=pattern.confidence,
                line_start=line_start,
                line_end=line_end,
            )
            manifest.add_entry(entry)
        return manifest

    def merge(self, *manifests: MigrationManifest) -> MigrationManifest:
        """Merge multiple manifests into one, de-duplicating by file+pattern."""
        seen: set[tuple[str, str]] = set()
        merged = MigrationManifest()
        for m in manifests:
            for entry in m.entries:
                key = (entry.file_path, entry.pattern_id)
                if key not in seen:
                    seen.add(key)
                    merged.add_entry(entry)
        return merged
