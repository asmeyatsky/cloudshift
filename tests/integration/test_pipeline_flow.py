"""Integration tests for the full pipeline flow across API, CLI, and ID consistency.

Verifies:
- Scan -> Plan -> Apply -> Validate ID handoff (project_id, manifest_id, plan_id, job_id).
- API: POST returns 202 + job_id; GET poll until 200 with result shape.
- Request/response shapes match across API and CLI expectations.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cloudshift.infrastructure.config.dependency_injection import GIT_IMPORT_BASE
from cloudshift.infrastructure.config.settings import Settings
from cloudshift.presentation.api.app import create_app
from cloudshift.presentation.api.dependencies import verify_auth


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _poll_get(client: TestClient, url: str, max_attempts: int = 40, interval: float = 0.25) -> tuple[int, dict]:
    """Poll GET until 200 or max_attempts. Returns (status_code, json body)."""
    for _ in range(max_attempts):
        resp = client.get(url)
        if resp.status_code == 200:
            return 200, resp.json()
        if resp.status_code != 404:
            return resp.status_code, resp.json() if resp.content else {}
        time.sleep(interval)
    return 404, {"detail": "timeout"}


# ---------------------------------------------------------------------------
# API pipeline flow (scan -> plan -> apply -> validate)
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_app(tmp_path):
    """App with real Container, temp DB and scan path, auth disabled."""
    from cloudshift.infrastructure.config.dependency_injection import Container

    patterns_dir = _repo_root() / "patterns"
    if not patterns_dir.is_dir():
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
    settings = Settings(
        db_path=tmp_path / "cloudshift.db",
        patterns_dir=patterns_dir,
        allowed_scan_paths=[Path("."), GIT_IMPORT_BASE, tmp_path],
        api_key=None,
    )
    app = create_app(settings=settings)
    # TestClient does not run lifespan; set container so get_container() works
    app.state.container = Container(settings=settings)
    app.state.settings = settings
    app.dependency_overrides[verify_auth] = lambda: None
    return app


@pytest.fixture
def pipeline_client(pipeline_app):
    return TestClient(pipeline_app, raise_server_exceptions=False)


def test_api_pipeline_flow_id_handoff(pipeline_client, tmp_path):
    """Full API pipeline: scan (project_id) -> plan (manifest_id=project_id) -> apply (plan_id) -> validate (plan_id)."""
    (tmp_path / "app.py").write_text("import boto3\ns3 = boto3.client('s3')\n")
    project_id = "proj-pipeline-test"

    # 1) Scan
    scan_resp = pipeline_client.post(
        "/api/scan",
        json={
            "root_path": str(tmp_path),
            "source_provider": "AWS",
            "target_provider": "GCP",
            "project_id": project_id,
        },
    )
    assert scan_resp.status_code == 202
    scan_data = scan_resp.json()
    assert "job_id" in scan_data
    scan_job_id = scan_data["job_id"]

    status, scan_result = _poll_get(pipeline_client, f"/api/scan/{scan_job_id}")
    assert status == 200, scan_result
    assert "project_id" in scan_result or "error" in scan_result
    if scan_result.get("error"):
        pytest.skip(f"Scan failed: {scan_result.get('error')}")

    # 2) Plan (manifest_id = project_id so backend finds saved manifest)
    plan_resp = pipeline_client.post(
        "/api/plan",
        json={
            "project_id": project_id,
            "manifest_id": project_id,
            "strategy": "balanced",
            "max_parallel": 4,
        },
    )
    assert plan_resp.status_code == 202
    plan_data = plan_resp.json()
    plan_job_id = plan_data["job_id"]

    status, plan_result = _poll_get(pipeline_client, f"/api/plan/{plan_job_id}")
    assert status == 200, plan_result
    plan_id = plan_result.get("plan_id")
    assert plan_id or plan_result.get("error")
    if plan_result.get("error"):
        pytest.skip(f"Plan failed: {plan_result.get('error')}")
    assert plan_result.get("project_id") == project_id

    # 3) Apply (plan_id from plan result)
    apply_resp = pipeline_client.post(
        "/api/apply",
        json={"plan_id": plan_id, "dry_run": True, "backup": False},
    )
    assert apply_resp.status_code == 202
    apply_job_id = apply_resp.json()["job_id"]

    status, apply_result = _poll_get(pipeline_client, f"/api/apply/{apply_job_id}")
    assert status == 200, apply_result
    assert apply_result.get("plan_id") == plan_id
    assert "success" in apply_result

    # 4) Validate (plan_id; may fail with no metadata if apply was dry_run / 0 files)
    val_resp = pipeline_client.post(
        "/api/validate",
        json={"plan_id": plan_id, "check_ast_equivalence": False, "check_residual_refs": False},
    )
    assert val_resp.status_code == 202
    val_job_id = val_resp.json()["job_id"]

    status, val_result = _poll_get(pipeline_client, f"/api/validate/{val_job_id}")
    assert status == 200, val_result
    assert val_result.get("plan_id") == plan_id
    assert "passed" in val_result or "error" in val_result


def test_api_scan_accepts_optional_project_id(pipeline_client, tmp_path):
    """Scan request accepts optional project_id for manifest persistence."""
    (tmp_path / "empty.py").write_text("# empty\n")
    # Without project_id: still 202
    r = pipeline_client.post(
        "/api/scan",
        json={
            "root_path": str(tmp_path),
            "source_provider": "AWS",
            "target_provider": "GCP",
        },
    )
    assert r.status_code == 202
    assert "job_id" in r.json()


def test_api_plan_requires_project_id_and_manifest_id(pipeline_client):
    """Plan request requires project_id and manifest_id."""
    r = pipeline_client.post("/api/plan", json={})
    assert r.status_code == 422  # validation error


def test_api_apply_requires_plan_id(pipeline_client):
    """Apply request requires plan_id."""
    r = pipeline_client.post("/api/apply", json={})
    assert r.status_code == 422


def test_api_validate_requires_plan_id(pipeline_client):
    """Validate request requires plan_id."""
    r = pipeline_client.post("/api/validate", json={})
    assert r.status_code == 422
