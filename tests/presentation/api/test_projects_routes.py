"""Tests for project routes: POST /api/projects/from-snippet, POST /api/projects/from-git."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cloudshift.presentation.api.app import create_app
from cloudshift.presentation.api.dependencies import verify_auth
from cloudshift.presentation.api.routes import projects as projects_router


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


class TestFromGit:
    def test_from_git_rejects_non_https(self, client):
        resp = client.post(
            "/api/projects/from-git",
            json={
                "repo_url": "git@github.com:foo/bar.git",
                "branch": "main",
                "name": "bar",
                "source_provider": "AWS",
                "target_provider": "GCP",
            },
        )
        assert resp.status_code == 400
        assert "HTTPS" in resp.json().get("detail", "")

    def test_from_git_clones_and_returns(self, client, tmp_path):
        base = tmp_path / "git_import"
        base.mkdir()
        with patch.object(projects_router, "GIT_IMPORT_BASE", base), patch(
            "cloudshift.presentation.api.routes.projects.subprocess.run"
        ) as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0})()
            resp = client.post(
                "/api/projects/from-git",
                json={
                    "repo_url": "https://github.com/example/repo.git",
                    "branch": "main",
                    "name": "my-repo",
                    "source_provider": "AWS",
                    "target_provider": "GCP",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-repo"
        assert "project_id" in data
        assert "root_path" in data
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "clone" in call_args
        assert "main" in call_args
        assert "https://github.com/example/repo.git" in call_args

    def test_from_git_normalizes_github_tree_url(self, client, tmp_path):
        """Pasting a GitHub browser URL (e.g. .../tree/main/python/) should clone repo root."""
        base = tmp_path / "git_import"
        base.mkdir()
        with patch.object(projects_router, "GIT_IMPORT_BASE", base), patch(
            "cloudshift.presentation.api.routes.projects.subprocess.run"
        ) as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0})()
            resp = client.post(
                "/api/projects/from-git",
                json={
                    "repo_url": "https://github.com/aws-samples/aws-cdk-examples/tree/main/python/",
                    "branch": "main",
                    "name": "cdk-python",
                    "source_provider": "AWS",
                    "target_provider": "GCP",
                },
            )
        assert resp.status_code == 200
        call_args = mock_run.call_args[0][0]
        # Clone URL must be repo root, not .../tree/main/python/
        assert "https://github.com/aws-samples/aws-cdk-examples.git" in call_args
        assert "/tree/" not in " ".join(call_args)

    def test_from_git_explicit_subpath_uses_subfolder_as_root(self, client, tmp_path):
        """When subpath is provided and exists after clone, root_path is the subfolder."""
        base = tmp_path / "git_import"
        base.mkdir()

        def mock_clone(*args, **kwargs):
            # Simulate clone: create project dir and subfolder so route finds it
            project_dir = base / "cdk-python"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "python").mkdir(exist_ok=True)
            (project_dir / "python" / "app.py").write_text("# code")

        with patch.object(projects_router, "GIT_IMPORT_BASE", base), patch(
            "cloudshift.presentation.api.routes.projects.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = mock_clone
            resp = client.post(
                "/api/projects/from-git",
                json={
                    "repo_url": "https://github.com/aws-samples/aws-cdk-examples.git",
                    "branch": "main",
                    "name": "cdk-python",
                    "subpath": "python",
                    "source_provider": "AWS",
                    "target_provider": "GCP",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["root_path"] == str(base / "cdk-python" / "python")
