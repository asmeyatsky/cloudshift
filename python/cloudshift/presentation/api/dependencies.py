"""FastAPI dependency-injection helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Request


def get_container(request: Request) -> Any:
    """Retrieve the DI container stored on ``app.state`` during lifespan."""
    return request.app.state.container


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


def get_validate_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.validate_transformation import ValidateTransformationUseCase

    return ValidateTransformationUseCase(
        validation=container.validation,
        parser=container.parser,
        fs=container.file_system,
    )


def get_patterns_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.manage_patterns import ManagePatternsUseCase

    return ManagePatternsUseCase(
        pattern_store=container.pattern_store,
    )


def get_report_use_case(container: Any = Depends(get_container)):
    from cloudshift.application.use_cases.generate_report import GenerateReportUseCase

    return GenerateReportUseCase()
