"""Validate routes -- POST /api/validate, GET /api/validate/{id}, POST /api/validate/file (sync for VS Code)."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.dtos.validation import ValidationRequest
from cloudshift.application.use_cases import ValidateTransformationUseCase
from cloudshift.domain.value_objects.types import Language, Severity
from cloudshift.presentation.api.dependencies import get_container, get_validate_use_case
from cloudshift.presentation.api.schemas import (
    JobAccepted,
    ValidateRequestBody,
    ValidateResultResponse,
    ValidateFileRequestBody,
    ValidateFileResultResponse,
    ValidationErrorResponse,
    ValidationWarningResponse,
)
from cloudshift.presentation.api.websocket import manager

router = APIRouter(prefix="/api/validate", tags=["validate"])


def _infer_language(file_path: str) -> Language:
    ext = (Path(file_path).suffix or "").lstrip(".").lower()
    if ext in ("py",):
        return Language.PYTHON
    if ext in ("ts", "tsx", "js", "jsx"):
        return Language.TYPESCRIPT
    if ext in ("tf", "hcl"):
        return Language.HCL
    return Language.PYTHON

_results: dict[str, Any] = {}


async def _run_validate(
    job_id: str, use_case: ValidateTransformationUseCase, dto: ValidationRequest
) -> None:
    await manager.broadcast({"job_id": job_id, "type": "validate", "status": "started"})
    try:
        result = await use_case.execute(dto)
        _results[job_id] = result.model_dump(mode="json")
        await manager.broadcast({"job_id": job_id, "type": "validate", "status": "completed"})
    except Exception as exc:
        err_msg = str(exc)
        _results[job_id] = {
            "plan_id": dto.plan_id,
            "passed": False,
            "issues": [],
            "ast_equivalent": None,
            "residual_refs_found": 0,
            "sdk_coverage": 0.0,
            "tests_passed": None,
            "error": err_msg,
        }
        await manager.broadcast({"job_id": job_id, "type": "validate", "status": "failed", "error": err_msg})


@router.post(
    "",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Validate applied transformations",
)
async def start_validate(
    body: ValidateRequestBody,
    background: BackgroundTasks,
    use_case: ValidateTransformationUseCase = Depends(get_validate_use_case),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    dto = ValidationRequest(
        plan_id=body.plan_id,
        check_ast_equivalence=body.check_ast_equivalence,
        check_residual_refs=body.check_residual_refs,
        check_sdk_surface=body.check_sdk_surface,
        run_tests=body.run_tests,
        test_command=body.test_command,
    )
    background.add_task(_run_validate, job_id, use_case, dto)
    return JobAccepted(job_id=job_id)


@router.get(
    "/{job_id}",
    response_model=ValidateResultResponse,
    responses={404: {"description": "Job not found or still running"}},
    summary="Retrieve validation results",
)
async def get_validate_result(job_id: str) -> ValidateResultResponse:
    if job_id not in _results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation not found or still in progress")
    return ValidateResultResponse(**_results[job_id])


@router.post(
    "/file",
    response_model=ValidateFileResultResponse,
    summary="Validate a single file (VS Code, sync)",
)
async def validate_file(
    body: ValidateFileRequestBody,
    container=Depends(get_container),
) -> ValidateFileResultResponse:
    """Run syntax validation on file content. Returns errors and warnings synchronously."""
    validation = getattr(container, "validation", None)
    if not validation or not hasattr(validation, "validate_syntax"):
        return ValidateFileResultResponse(
            file=body.file_path,
            valid=True,
            errors=[],
            warnings=[],
        )
    lang = _infer_language(body.file_path)
    result = validation.validate_syntax(body.content, lang)
    if asyncio.iscoroutine(result):
        report = await result
    else:
        report = await asyncio.to_thread(validation.validate_syntax, body.content, lang)
    errors = []
    warnings = []
    for i in report.issues:
        line = i.line if i.line is not None else 0
        col = getattr(i, "column", None) or 0
        item = {"line": line, "column": col, "message": i.message, "rule": i.rule or "validation"}
        if i.severity in (Severity.ERROR, Severity.CRITICAL):
            errors.append(ValidationErrorResponse(**item))
        else:
            warnings.append(ValidationWarningResponse(**item))
    return ValidateFileResultResponse(
        file=body.file_path,
        valid=report.is_valid,
        errors=errors,
        warnings=warnings,
    )
