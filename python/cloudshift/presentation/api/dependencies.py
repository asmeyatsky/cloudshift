"""FastAPI dependency-injection helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader


def get_container(request: Request) -> Any:
    """Retrieve the DI container stored on ``app.state`` during lifespan."""
    return request.app.state.container


def get_settings(request: Request) -> Any:
    """Retrieve settings from app state."""
    return request.app.state.settings


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str = Security(_api_key_header),
):
    """Verify the X-API-Key header against the configured static key."""
    settings = get_settings(request)
    if not settings.api_key:
        return  # Auth disabled

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )


def get_scan_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.scan_project import ScanProjectUseCase

    return ScanProjectUseCase(
        fs=container.walker,
        parser=container.parser,
        detector=container.detector,
    )


def get_plan_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.generate_plan import GeneratePlanUseCase

    return GeneratePlanUseCase(
        pattern_engine=container.pattern_engine,
        diff=container.diff,
    )


def get_apply_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.apply_transformation import ApplyTransformationUseCase

    return ApplyTransformationUseCase(
        pattern_engine=container.pattern_engine,
        diff=container.diff,
        fs=container.file_system,
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
