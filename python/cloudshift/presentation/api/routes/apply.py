"""Apply routes -- POST /api/apply, GET /api/apply/{id}."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.dtos.transform import TransformRequest
from cloudshift.application.use_cases import ApplyTransformationUseCase
from cloudshift.presentation.api.dependencies import get_apply_use_case
from cloudshift.presentation.api.schemas import (
    ApplyRequestBody,
    ApplyResultResponse,
    JobAccepted,
)
from cloudshift.presentation.api.websocket import manager

router = APIRouter(prefix="/api/apply", tags=["apply"])

_results: dict[str, Any] = {}


async def _run_apply(job_id: str, use_case: ApplyTransformationUseCase, dto: TransformRequest) -> None:
    await manager.broadcast({"job_id": job_id, "type": "apply", "status": "started"})
    try:
        result = await use_case.execute(dto)
        _results[job_id] = result.model_dump(mode="json")
        await manager.broadcast({"job_id": job_id, "type": "apply", "status": "completed"})
    except Exception as exc:
        _results[job_id] = {"error": str(exc)}
        await manager.broadcast({"job_id": job_id, "type": "apply", "status": "failed", "error": str(exc)})


@router.post(
    "",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Apply transformations from a plan",
)
async def start_apply(
    body: ApplyRequestBody,
    background: BackgroundTasks,
    use_case: ApplyTransformationUseCase = Depends(get_apply_use_case),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    dto = TransformRequest(
        plan_id=body.plan_id,
        step_ids=body.step_ids,
        dry_run=body.dry_run,
        backup=body.backup,
    )
    background.add_task(_run_apply, job_id, use_case, dto)
    return JobAccepted(job_id=job_id)


@router.get(
    "/{job_id}",
    response_model=ApplyResultResponse,
    responses={404: {"description": "Job not found or still running"}},
    summary="Retrieve apply results",
)
async def get_apply_result(job_id: str) -> ApplyResultResponse:
    if job_id not in _results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Apply not found or still in progress")
    return ApplyResultResponse(**_results[job_id])
