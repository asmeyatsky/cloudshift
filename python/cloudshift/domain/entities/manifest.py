"""Migration manifest entities."""

from __future__ import annotations

from dataclasses import dataclass, field

from cloudshift.domain.value_objects.types import ConfidenceScore, TransformationStatus


@dataclass(slots=True)
class ManifestEntry:
    """A single entry in a migration manifest."""

    file_path: str
    pattern_id: str
    source_construct: str
    target_construct: str
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.0))
    status: TransformationStatus = TransformationStatus.PENDING
    line_start: int | None = None
    line_end: int | None = None


@dataclass(slots=True)
class MigrationManifest:
    """Aggregates all planned transformations for a migration run."""

    entries: list[ManifestEntry] = field(default_factory=list)

    @property
    def overall_confidence(self) -> ConfidenceScore:
        if not self.entries:
            return ConfidenceScore(0.0)
        avg = sum(e.confidence.value for e in self.entries) / len(self.entries)
        return ConfidenceScore(avg)

    @property
    def total_files(self) -> int:
        return len({e.file_path for e in self.entries})

    @property
    def total_constructs(self) -> int:
        return len(self.entries)

    def add_entry(self, entry: ManifestEntry) -> None:
        self.entries.append(entry)
