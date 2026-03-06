"""Project repository port protocol."""

from __future__ import annotations

from typing import Protocol

from cloudshift.domain.entities.project import Project


class ProjectRepositoryPort(Protocol):
    """Port for persisting and querying projects."""

    def save(self, project: Project) -> str: ...
    def get(self, project_id: str) -> Project | None: ...
    def list_all(self) -> list[Project]: ...
    def delete(self, project_id: str) -> bool: ...
    def update_status(self, project_id: str, status: str) -> None: ...
