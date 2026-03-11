"""Plan routes -- POST /api/plan, GET /api/plan/{id}."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.dtos.plan import PlanRequest
from cloudshift.application.use_cases import GeneratePlanUseCase
from cloudshift.presentation.api.dependencies import get_plan_use_case
from cloudshift.presentation.api.schemas import (
    JobAccepted,
    PlanRequestBody,
    PlanResultResponse,
)
from cloudshift.presentation.api.plan_store import register_plan
from cloudshift.presentation.api.websocket import manager

router = APIRouter(prefix="/api/plan", tags=["plan"])

_results: dict[str, Any] = {}


async def _run_plan(job_id: str, use_case: GeneratePlanUseCase, dto: PlanRequest) -> None:
    await manager.broadcast({"job_id": job_id, "type": "plan", "status": "started"})
    try:
        result = await use_case.execute(dto)
        dumped = result.model_dump(mode="json")
        _results[job_id] = dumped
        if not result.error and result.plan_id:
            register_plan(result.plan_id, dumped)
        await manager.broadcast({"job_id": job_id, "type": "plan", "status": "completed"})
    except Exception as exc:
        err_msg = str(exc)
        _results[job_id] = {
            "plan_id": "",
            "project_id": dto.project_id,
            "steps": [],
            "estimated_files_changed": 0,
            "estimated_confidence": 0.0,
            "warnings": [],
            "error": err_msg,
        }
        await manager.broadcast({"job_id": job_id, "type": "plan", "status": "failed", "error": err_msg})


@router.post(
    "",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a migration plan",
)
async def start_plan(
    body: PlanRequestBody,
    background: BackgroundTasks,
    use_case: GeneratePlanUseCase = Depends(get_plan_use_case),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    dto = PlanRequest(
        project_id=body.project_id,
        manifest_id=body.manifest_id,
        strategy=body.strategy,
        max_parallel=body.max_parallel,
    )
    background.add_task(_run_plan, job_id, use_case, dto)
    return JobAccepted(job_id=job_id)


@router.get(
    "/{job_id}",
    response_model=PlanResultResponse,
    responses={404: {"description": "Job not found or still running"}},
    summary="Retrieve plan results",
)
async def get_plan_result(job_id: str) -> PlanResultResponse:
    if job_id not in _results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or still in progress")
    return PlanResultResponse(**_results[job_id])
