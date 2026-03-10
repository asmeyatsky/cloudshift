"""Tests for project routes: POST /api/projects/from-snippet."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cloudshift.presentation.api.app import create_app
from cloudshift.presentation.api.dependencies import verify_auth


@pytest.fixture
def app_with_auth_override(tmp_path):
    from cloudshift.infrastructure.config.settings import Settings

    settings = Settings(data_dir=tmp_path)
    app = create_app(settings=settings)
    app.dependency_overrides[verify_auth] = lambda: None
    return app


@pytest.fixture
def client(app_with_auth_override):
    return TestClient(app_with_auth_override)


class TestFromSnippet:
    def test_from_snippet_creates_file_and_returns_path(self, client, tmp_path):
        resp = client.post(
            "/api/projects/from-snippet",
            json={
                "name": "my-snippet",
                "content": "import boto3\nprint('hello')",
                "language": "PYTHON",
                "source_provider": "AWS",
                "target_provider": "GCP",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "project_id" in data
        assert "root_path" in data
        assert data["name"] == "my-snippet"
        assert len(data["project_id"]) == 12

        root = Path(data["root_path"])
        assert root.exists()
        assert root.is_dir()
        main_py = root / "main.py"
        assert main_py.exists()
        assert main_py.read_text() == "import boto3\nprint('hello')"

    def test_from_snippet_custom_filename(self, client, tmp_path):
        resp = client.post(
            "/api/projects/from-snippet",
            json={
                "name": "ts-snippet",
                "content": "const x = 1;",
                "language": "TYPESCRIPT",
                "source_provider": "AZURE",
                "target_provider": "GCP",
                "filename": "index.ts",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        root = Path(data["root_path"])
        assert (root / "index.ts").exists()
        assert (root / "index.ts").read_text() == "const x = 1;"

    def test_from_snippet_default_filename_typescript(self, client, tmp_path):
        resp = client.post(
            "/api/projects/from-snippet",
            json={
                "name": "ts",
                "content": "x",
                "language": "TYPESCRIPT",
                "source_provider": "AWS",
                "target_provider": "GCP",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        root = Path(data["root_path"])
        assert (root / "main.ts").exists()

    def test_from_snippet_unknown_language_defaults_to_txt(self, client, tmp_path):
        resp = client.post(
            "/api/projects/from-snippet",
            json={
                "name": "other",
                "content": "content",
                "language": "UNKNOWN",
                "source_provider": "AWS",
                "target_provider": "GCP",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        root = Path(data["root_path"])
        assert (root / "main.txt").exists()

    def test_from_snippet_path_traversal_filename_sanitized(self, client, tmp_path):
        """Security: filename like ../../../etc/passwd is basename-sanitized and kept under project dir."""
        resp = client.post(
            "/api/projects/from-snippet",
            json={
                "name": "safe",
                "content": "x = 1",
                "language": "PYTHON",
                "source_provider": "AWS",
                "target_provider": "GCP",
                "filename": "../../../etc/passwd",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        root = Path(data["root_path"])
        # Should write to project_dir with a safe name (passwd has no allowed extension -> main.py)
        assert root.exists()
        assert (root / "main.py").exists()
        assert (root / "main.py").read_text() == "x = 1"
