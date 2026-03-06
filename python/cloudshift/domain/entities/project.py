"""Project entity -- the root aggregate for a migration project."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cloudshift.domain.value_objects.types import CloudProvider, ProjectStatus


@dataclass(slots=True)
class Project:
    """Represents a cloud migration project."""

    name: str
    root_path: Path
    source_provider: CloudProvider
    target_provider: CloudProvider
    status: ProjectStatus = ProjectStatus.CREATED
    file_patterns: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)

    def advance_status(self, new_status: ProjectStatus) -> None:
        self.status = new_status

    def is_active(self) -> bool:
        return self.status not in (ProjectStatus.COMPLETED, ProjectStatus.FAILED)
