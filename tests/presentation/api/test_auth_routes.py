"""Tests for auth routes: POST /api/auth/login, GET /api/auth/mode."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from cloudshift.infrastructure.config.settings import Settings
from cloudshift.presentation.api.auth_utils import hash_password
from cloudshift.presentation.api.app import create_app
from cloudshift.presentation.api.dependencies import get_settings


@pytest.fixture
def users_file(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"testuser": hash_password("testpass")}))
    return path


@pytest.fixture
def app_password_mode(users_file):
    settings = Settings(
        auth_mode="password",
        users_file=users_file,
        jwt_secret="test-secret",
        jwt_ttl_seconds=3600,
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def client_password_mode(app_password_mode):
    return TestClient(app_password_mode)


class TestAuthMode:
    def test_auth_mode_returns_settings(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/auth/mode")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_mode" in data
        assert "deployment_mode" in data
        assert data["auth_mode"] in ("api_key", "searce_id", "password")
        assert data["deployment_mode"] in ("demo", "client")


class TestLogin:
    def test_login_success(self, client_password_mode):
        resp = client_password_mode.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "expires_in" in data
        assert data["expires_in"] == 3600
        assert len(data["token"]) > 0

    def test_login_invalid_password(self, client_password_mode):
        resp = client_password_mode.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.json().get("detail", "")

    def test_login_unknown_user(self, client_password_mode):
        resp = client_password_mode.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "testpass"},
        )
        assert resp.status_code == 401

    def test_login_missing_username(self, client_password_mode):
        resp = client_password_mode.post(
            "/api/auth/login",
            json={"password": "testpass"},
        )
        assert resp.status_code == 422

    def test_login_missing_password(self, client_password_mode):
        resp = client_password_mode.post(
            "/api/auth/login",
            json={"username": "testuser"},
        )
        assert resp.status_code == 422

    def test_login_rate_limited_returns_429(self, app_password_mode):
        from cloudshift.presentation.api.rate_limit import login_limiter

        login_limiter.reset()
        client = TestClient(app_password_mode)
        for _ in range(5):
            client.post("/api/auth/login", json={"username": "wrong", "password": "wrong"})
        resp = client.post("/api/auth/login", json={"username": "a", "password": "b"})
        assert resp.status_code == 429
        assert "Too many" in resp.json().get("detail", "")

    def test_login_when_auth_mode_not_password(self):
        from cloudshift.presentation.api.rate_limit import login_limiter

        login_limiter.reset()
        settings = Settings(auth_mode="api_key")
        app = create_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        client = TestClient(app)
        resp = client.post(
            "/api/auth/login",
            json={"username": "u", "password": "p"},
        )
        assert resp.status_code == 400
        assert "password" in resp.json().get("detail", "").lower()


class TestVerifyAuthIntegration:
    """Test that protected routes respect auth_mode (api_key, searce_id, password)."""

    def test_api_key_required_when_set(self):
        from cloudshift.infrastructure.config.settings import Settings

        settings = Settings(api_key="secret-key", auth_mode="api_key")
        app = create_app(settings=settings)
        with TestClient(app) as client:
            resp = client.get("/api/config")
            assert resp.status_code == 401
            resp2 = client.get("/api/config", headers={"X-API-Key": "secret-key"})
            assert resp2.status_code == 200

    def test_searce_id_accepts_header(self):
        from cloudshift.infrastructure.config.settings import Settings

        settings = Settings(auth_mode="searce_id")
        app = create_app(settings=settings)
        with TestClient(app) as client:
            resp = client.get("/api/config")
            assert resp.status_code == 401
            resp2 = client.get("/api/config", headers={"X-Searce-ID": "demo-token"})
            assert resp2.status_code == 200

    def test_password_accepts_bearer_jwt(self, users_file):
        from cloudshift.presentation.api.auth_utils import sign_jwt

        settings = Settings(
            auth_mode="password",
            users_file=users_file,
            jwt_secret="test-secret",
            jwt_ttl_seconds=3600,
        )
        app = create_app(settings=settings)
        with TestClient(app) as client:
            resp = client.get("/api/config")
            assert resp.status_code == 401
            token = sign_jwt({"sub": "testuser"}, "test-secret", 3600)
            resp2 = client.get("/api/config", headers={"Authorization": f"Bearer {token}"})
            assert resp2.status_code == 200
