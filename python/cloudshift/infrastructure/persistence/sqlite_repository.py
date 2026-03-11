"""SQLite project repository implementing ProjectRepositoryPort."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

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

_CREATE_SCAN_MANIFESTS_TABLE = """
CREATE TABLE IF NOT EXISTS scan_manifests (
    id          TEXT PRIMARY KEY,
    root_path   TEXT NOT NULL,
    source_prov TEXT NOT NULL,
    target_prov TEXT NOT NULL,
    entries_json TEXT NOT NULL DEFAULT '[]'
);
"""

_CREATE_TRANSFORM_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS transform_metadata (
    plan_id     TEXT PRIMARY KEY,
    root_path   TEXT NOT NULL,
    source_prov TEXT NOT NULL,
    target_prov TEXT NOT NULL,
    modified_files_json TEXT NOT NULL DEFAULT '[]'
);
"""

_CREATE_JOB_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS job_results (
    job_id      TEXT NOT NULL,
    kind        TEXT NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (job_id, kind)
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
        self._conn.execute(_CREATE_SCAN_MANIFESTS_TABLE)
        self._conn.execute(_CREATE_TRANSFORM_METADATA_TABLE)
        self._conn.execute(_CREATE_JOB_RESULTS_TABLE)
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

    def save_scan_manifest(self, manifest_id: str, root_path: str, source_provider: str, target_provider: str, files: list[dict]) -> None:
        """Store scan result for plan use case (manifest_id = project_id from UI)."""
        entries_json = json.dumps([{"path": f.get("path"), "services_detected": f.get("services_detected", [])} for f in files])
        self._conn.execute(
            "INSERT OR REPLACE INTO scan_manifests (id, root_path, source_prov, target_prov, entries_json) VALUES (?, ?, ?, ?, ?)",
            (manifest_id, root_path, source_provider, target_provider, entries_json),
        )
        self._conn.commit()

    def _get_manifest_sync(self, manifest_id: str) -> SimpleNamespace | None:
        row = self._conn.execute(
            "SELECT id, root_path, source_prov, target_prov, entries_json FROM scan_manifests WHERE id = ?",
            (manifest_id,),
        ).fetchone()
        if row is None:
            return None
        entries = []
        for e in json.loads(row["entries_json"]):
            entries.append(SimpleNamespace(file_path=e.get("path", ""), services=e.get("services_detected", [])))
        return SimpleNamespace(
            root_path=row["root_path"],
            source_provider=row["source_prov"],
            target_provider=row["target_prov"],
            entries=entries,
        )

    async def get_manifest(self, manifest_id: str) -> SimpleNamespace | None:
        """Return manifest for plan use case. Run in caller thread (SQLite is thread-local)."""
        return self._get_manifest_sync(manifest_id)

    def save_transform_metadata(
        self,
        plan_id: str,
        root_path: str,
        source_provider: str,
        target_provider: str,
        modified_files: list[dict],
    ) -> None:
        """Persist transform metadata for validate use case. Call from same thread as connection."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO transform_metadata (plan_id, root_path, source_prov, target_prov, modified_files_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (plan_id, root_path, source_provider, target_provider, json.dumps(modified_files)),
        )
        self._conn.commit()

    def _get_transform_metadata_sync(self, plan_id: str) -> SimpleNamespace | None:
        row = self._conn.execute(
            "SELECT plan_id, root_path, source_prov, target_prov, modified_files_json FROM transform_metadata WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is None:
            return None
        files = []
        for f in json.loads(row["modified_files_json"]):
            files.append(
                SimpleNamespace(
                    path=f.get("path", ""),
                    original_content=f.get("original_content", ""),
                    modified_content=f.get("modified_content", ""),
                    language=f.get("language", "python"),
                )
            )
        return SimpleNamespace(
            root_path=row["root_path"],
            source_provider=row["source_prov"],
            target_provider=row["target_prov"],
            modified_files=files,
        )

    async def get_transform_metadata(self, plan_id: str) -> SimpleNamespace | None:
        """Return transform metadata for validate use case. Run in caller thread (SQLite is thread-local)."""
        return self._get_transform_metadata_sync(plan_id)

    def save_job_result(self, kind: str, job_id: str, result: dict) -> None:
        """Persist job result so GET can find it on another instance (e.g. Cloud Run)."""
        self._conn.execute(
            "INSERT OR REPLACE INTO job_results (job_id, kind, result_json) VALUES (?, ?, ?)",
            (job_id, kind, json.dumps(result)),
        )
        self._conn.commit()

    def get_job_result(self, kind: str, job_id: str) -> dict | None:
        """Return persisted job result or None."""
        row = self._conn.execute(
            "SELECT result_json FROM job_results WHERE job_id = ? AND kind = ?",
            (job_id, kind),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["result_json"])

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
