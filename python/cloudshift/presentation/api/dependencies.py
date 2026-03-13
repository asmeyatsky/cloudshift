"""FastAPI dependency-injection helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from cloudshift.infrastructure.config.settings import AuthMode
from cloudshift.presentation.api.auth_utils import load_users, verify_jwt


def get_container(request: Request) -> Any:
    """Retrieve the DI container stored on ``app.state`` during lifespan."""
    return request.app.state.container


def get_settings(request: Request) -> Any:
    """Retrieve settings from app state."""
    return request.app.state.settings


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


def _get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


async def verify_api_key(
    request: Request,
    api_key: str = Security(_api_key_header),
):
    """Verify the X-API-Key header against the configured static key (auth_mode=api_key)."""
    settings = get_settings(request)
    if not settings.api_key:
        return  # Auth disabled
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )


async def verify_auth(request: Request):
    """Single auth dependency: dispatches by settings.auth_mode."""
    settings = get_settings(request)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server not ready (settings not loaded). Retry shortly.",
        )
    mode: AuthMode = getattr(settings, "auth_mode", "api_key") or "api_key"

    # Allow API key from query (e.g. WebSocket upgrade; browser cannot set headers on WS)
    def _get_api_key(req: Request) -> str:
        h = (req.headers.get("X-API-Key") or "").strip()
        if h:
            return h
        q = getattr(req, "query_params", None)
        if q is not None:
            return (q.get("api_key") or "").strip()
        return ""

    if mode == "api_key":
        api_key = _get_api_key(request)
        if not getattr(settings, "api_key", None):
            return
        if api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key",
            )
        return

    if mode == "searce_id":
        # Demo: accept IAP JWT (browser behind IAP), X-Searce-ID, Bearer, or API key (VS Code/scripts)
        iap_jwt = request.headers.get("X-Goog-IAP-JWT-Assertion")
        searce_id = request.headers.get("X-Searce-ID")
        token = _get_bearer_token(request)
        api_key = _get_api_key(request)
        if iap_jwt or searce_id or token:
            return
        if getattr(settings, "api_key", None) and api_key == settings.api_key:
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="IAP / X-Searce-ID / Bearer or valid X-API-Key required",
        )

    if mode == "password":
        token = _get_bearer_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization Bearer token required",
            )
        payload = verify_jwt(token, settings.jwt_secret)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return


def get_scan_use_case(container: Any = Depends(get_container)):
    from pathlib import Path

    from cloudshift.application.use_cases.scan_project import ScanProjectUseCase
    from cloudshift.infrastructure.config.dependency_injection import GIT_IMPORT_BASE
    from cloudshift.presentation.api.scan_adapters import (
        AsyncScanDetector,
        AsyncScanFs,
        AsyncScanParser,
    )

    settings = getattr(container, "_settings", None)
    allowed = list(getattr(settings, "allowed_scan_paths", [Path(".")])) if settings else [Path(".")]
    if GIT_IMPORT_BASE not in allowed:
        allowed.append(GIT_IMPORT_BASE)

    return ScanProjectUseCase(
        fs=AsyncScanFs(container.walker),
        parser=AsyncScanParser(container.parser),
        detector=AsyncScanDetector(container.detector),
        allowed_paths=allowed,
    )


def get_plan_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.generate_plan import GeneratePlanUseCase
    from cloudshift.presentation.api.plan_adapters import PlanPatternEngineAdapter

    return GeneratePlanUseCase(
        pattern_engine=PlanPatternEngineAdapter(
            pattern_store=container.pattern_store,
            walker=container.walker,
            pattern_engine=container.pattern_engine,
        ),
        manifest_store=container.project_repository,
    )


def get_apply_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.apply_transformation import ApplyTransformationUseCase
    from cloudshift.presentation.api.apply_adapters import AsyncApplyFs, AsyncDiffEngineAdapter
    from cloudshift.presentation.api.plan_adapters import PlanStoreAdapter

    return ApplyTransformationUseCase(
        plan_store=PlanStoreAdapter(),
        pattern_engine=container.pattern_engine,
        fs=AsyncApplyFs(container.file_system),
        diff_engine=AsyncDiffEngineAdapter(container.diff),
        git=container.git_safety,
        imports=container.import_organizer,
    )


def get_validate_use_case(container: Any = Depends(get_container), settings: Any = Depends(get_settings)):
    from cloudshift.application.use_cases.validate_transformation import ValidateTransformationUseCase

    # Use the container's resolver to ensure consistent wiring with CLI
    # but override with current request-scope settings if needed (though settings are global here)
    # Since container.resolve creates a new instance each time, this is safe.
    from cloudshift.infrastructure.config.dependency_injection import Container
    
    # We can cast container to Container for type checking if needed, but it's Any here.
    # The container in app.state is already configured with settings.
    # So we can just delegate to container.resolve if it supports the class.
    
    # However, container.resolve returns a factory lambda in the current implementation,
    # wait, no, it calls factory() at the end: `return factory()`.
    # So we can just use container.resolve(ValidateTransformationUseCase).
    
    return container.resolve(ValidateTransformationUseCase)


def get_patterns_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.manage_patterns import ManagePatternsUseCase

    return ManagePatternsUseCase(
        pattern_store=container.pattern_store,
    )


def get_report_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.generate_report import GenerateReportUseCase

    return GenerateReportUseCase()
