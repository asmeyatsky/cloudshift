"""Validate routes -- POST /api/validate, GET /api/validate/{id}."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.dtos.validation import ValidationRequest
from cloudshift.application.use_cases import ValidateTransformationUseCase
from cloudshift.presentation.api.dependencies import get_validate_use_case
from cloudshift.presentation.api.schemas import (
    JobAccepted,
    ValidateRequestBody,
    ValidateResultResponse,
)
from cloudshift.presentation.api.websocket import manager

router = APIRouter(prefix="/api/validate", tags=["validate"])

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
        _results[job_id] = {"error": str(exc)}
        await manager.broadcast({"job_id": job_id, "type": "validate", "status": "failed", "error": str(exc)})


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
