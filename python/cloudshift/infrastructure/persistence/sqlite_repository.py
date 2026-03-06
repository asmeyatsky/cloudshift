"""SQLite project repository implementing ProjectRepositoryPort."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from cloudshift.domain.entities.project import Project
from cloudshift.domain.value_objects.types import CloudProvider, ProjectStatus


_PROVIDER_MAP: dict[str, CloudProvider] = {
    "AWS": CloudProvider.AWS,
    "AZURE": CloudProvider.AZURE,
    "GCP": CloudProvider.GCP,
}

_STATUS_MAP: dict[str, ProjectStatus] = {s.name: s for s in ProjectStatus}

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    root_path     TEXT NOT NULL,
    source_prov   TEXT NOT NULL,
    target_prov   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'CREATED',
    file_patterns TEXT NOT NULL DEFAULT '[]',
    exclude_paths TEXT NOT NULL DEFAULT '[]',
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class SQLiteProjectRepository:
    """Implements ProjectRepositoryPort backed by a local SQLite database.

    Protocol methods:
        save(project) -> str
        get(project_id) -> Project | None
        list_all() -> list[Project]
        delete(project_id) -> bool
        update_status(project_id, status) -> None
    """

    def __init__(self, db_path: str | Path = "cloudshift.db") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def save(self, project: Project) -> str:
        project_id = uuid.uuid4().hex[:12]
        self._conn.execute(
            """
            INSERT INTO projects (id, name, root_path, source_prov, target_prov,
                                  status, file_patterns, exclude_paths)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                project.name,
                str(project.root_path),
                project.source_provider.name,
                project.target_provider.name,
                project.status.name,
                json.dumps(project.file_patterns),
                json.dumps(project.exclude_paths),
            ),
        )
        self._conn.commit()
        return project_id

    def get(self, project_id: str) -> Project | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_project(row)

    def list_all(self) -> list[Project]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC",
        ).fetchall()
        return [_row_to_project(r) for r in rows]

    def delete(self, project_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM projects WHERE id = ?", (project_id,),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def update_status(self, project_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE projects SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, project_id),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        name=row["name"],
        root_path=Path(row["root_path"]),
        source_provider=_PROVIDER_MAP.get(row["source_prov"], CloudProvider.AWS),
        target_provider=_PROVIDER_MAP.get(row["target_prov"], CloudProvider.GCP),
        status=_STATUS_MAP.get(row["status"], ProjectStatus.CREATED),
        file_patterns=json.loads(row["file_patterns"]),
        exclude_paths=json.loads(row["exclude_paths"]),
    )
