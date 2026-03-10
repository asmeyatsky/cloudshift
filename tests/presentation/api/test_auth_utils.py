"""Tests for auth_utils: password hashing, user file, JWT sign/verify."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cloudshift.presentation.api.auth_utils import (
    hash_password,
    load_users,
    sign_jwt,
    verify_jwt,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password_returns_verifiable_hash(self):
        h = hash_password("secret")
        assert isinstance(h, str)
        assert len(h) >= 32
        assert verify_password("secret", h) is True

    def test_hash_password_different_inputs(self):
        assert hash_password("a") != hash_password("b")

    def test_verify_password_match(self):
        h = hash_password("mypass")
        assert verify_password("mypass", h) is True

    def test_verify_password_mismatch(self):
        h = hash_password("mypass")
        assert verify_password("wrong", h) is False


class TestLoadUsers:
    def test_load_users_none_path(self):
        assert load_users(None) == {}

    def test_load_users_missing_file(self, tmp_path):
        assert load_users(tmp_path / "nonexistent.json") == {}

    def test_load_users_valid_file(self, tmp_path):
        path = tmp_path / "users.json"
        path.write_text(json.dumps({"alice": "hash1", "bob": "hash2"}))
        assert load_users(path) == {"alice": "hash1", "bob": "hash2"}

    def test_load_users_invalid_json(self, tmp_path):
        path = tmp_path / "users.json"
        path.write_text("not json")
        assert load_users(path) == {}


class TestJWT:
    def test_sign_jwt_returns_three_parts(self):
        token = sign_jwt({"sub": "user1"}, "secret", 3600)
        parts = token.split(".")
        assert len(parts) == 3
        assert all(len(p) > 0 for p in parts)

    def test_verify_jwt_valid(self):
        token = sign_jwt({"sub": "alice"}, "mysecret", 3600)
        payload = verify_jwt(token, "mysecret")
        assert payload is not None
        assert payload.get("sub") == "alice"
        assert "iat" in payload
        assert "exp" in payload

    def test_verify_jwt_wrong_secret_returns_none(self):
        token = sign_jwt({"sub": "alice"}, "secret1", 3600)
        assert verify_jwt(token, "secret2") is None

    def test_verify_jwt_tampered_returns_none(self):
        token = sign_jwt({"sub": "alice"}, "secret", 3600)
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.xxxx"
        assert verify_jwt(tampered, "secret") is None

    def test_verify_jwt_expired_returns_none(self):
        token = sign_jwt({"sub": "alice"}, "secret", ttl_seconds=-1)
        payload = verify_jwt(token, "secret")
        assert payload is None

    def test_verify_jwt_invalid_format_returns_none(self):
        assert verify_jwt("", "secret") is None
        assert verify_jwt("one.two", "secret") is None
        assert verify_jwt("a.b.c.d", "secret") is None
