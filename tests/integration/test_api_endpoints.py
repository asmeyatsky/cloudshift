"""Integration tests for FastAPI endpoints."""
import pytest


@pytest.fixture
def api_client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient
    from cloudshift.presentation.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client


def test_health_check(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_scan_endpoint(api_client, tmp_path):
    (tmp_path / "app.py").write_text("import boto3\ns3 = boto3.client('s3')")

    response = api_client.post("/api/scan", json={
        "root_path": str(tmp_path),
        "source_provider": "AWS",
        "target_provider": "GCP",
    })
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_patterns_list(api_client):
    response = api_client.get("/api/patterns")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_config_get(api_client):
    response = api_client.get("/api/config")
    assert response.status_code == 200
