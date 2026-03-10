"""Auth routes: login (password mode) and auth info for UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel, ConfigDict

from cloudshift.presentation.api.auth_utils import (
    load_users,
    sign_jwt,
    verify_password,
)
from cloudshift.presentation.api.dependencies import get_settings
from cloudshift.presentation.api.rate_limit import login_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    username: str = ""
    password: str = ""


@router.post("/login", summary="Login (client mode: username/password)")
async def login(
    request: Request,
    body: LoginBody,
    settings=Depends(get_settings),
) -> dict:
    """Issue a JWT for valid username/password when auth_mode=password. Rate limited (30/min per IP)."""
    client_ip = request.client.host if request.client else "unknown"
    if not login_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a minute.",
        )
    if settings.auth_mode != "password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login only available when auth_mode is password",
        )
    username = body.username or getattr(body, "name", "")
    password = body.password
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="username and password required",
        )
    users = load_users(settings.users_file)
    stored = users.get(username)
    if not stored or not verify_password(password, stored):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = sign_jwt(
        {"sub": username},
        settings.jwt_secret,
        settings.jwt_ttl_seconds,
    )
    return {"token": token, "expires_in": settings.jwt_ttl_seconds}


@router.get("/mode", summary="Auth and deployment mode (for UI)")
async def auth_mode(settings=Depends(get_settings)) -> dict:
    """Return auth_mode and deployment_mode so the UI can show login vs API key."""
    return {
        "auth_mode": settings.auth_mode,
        "deployment_mode": settings.deployment_mode,
    }
