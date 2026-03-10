"""Auth helpers: JWT (HMAC-SHA256), password hashing (bcrypt), and user file."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any

try:
    import bcrypt as _bcrypt

    _BCRYPT_AVAILABLE = True
except ImportError:
    _bcrypt = None
    _BCRYPT_AVAILABLE = False


def hash_password(password: str) -> str:
    """Hash for storage. Prefer bcrypt; fallback SHA-256 (legacy)."""
    if _BCRYPT_AVAILABLE:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("ascii")
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password. Accepts bcrypt hashes ($2b$...) or legacy SHA-256 hex."""
    if not stored_hash:
        return False
    if stored_hash.startswith("$2") and _BCRYPT_AVAILABLE:
        return _bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored_hash)


def load_users(users_file: Path | None) -> dict[str, str]:
    """Load {username: password_hash} from JSON file."""
    if not users_file or not users_file.is_file():
        return {}
    try:
        data = json.loads(users_file.read_text())
        return dict(data) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    import base64
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def sign_jwt(payload: dict[str, Any], secret: str, ttl_seconds: int) -> str:
    """Create a JWT with HS256 (HMAC-SHA256)."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload["iat"] = now
    payload["exp"] = now + ttl_seconds
    header_b = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{header_b}.{payload_b}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    sig_b = _b64url(sig)
    return f"{header_b}.{payload_b}.{sig_b}"


def verify_jwt(token: str, secret: str) -> dict[str, Any] | None:
    """Verify JWT and return payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b, payload_b, sig_b = parts
        message = f"{header_b}.{payload_b}".encode()
        expected = _b64url(hmac.new(secret.encode(), message, hashlib.sha256).digest())
        if not hmac.compare_digest(sig_b, expected):
            return None
        payload = json.loads(_b64url_decode(payload_b).decode())
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
