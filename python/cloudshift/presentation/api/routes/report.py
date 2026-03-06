"""Report routes -- POST /api/report, GET /api/report/{id}."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.use_cases import GenerateReportUseCase
from cloudshift.presentation.api.dependencies import get_report_use_case
from cloudshift.presentation.api.schemas import (
    JobAccepted,
    ReportRequestBody,
    ReportResponse,
)
from cloudshift.presentation.api.websocket import manager

router = APIRouter(prefix="/api/report", tags=["report"])

_results: dict[str, Any] = {}


async def _run_report(job_id: str, use_case: GenerateReportUseCase, project_id: str, plan_id: str) -> None:
    await manager.broadcast({"job_id": job_id, "type": "report", "status": "started"})
    try:
        result = await use_case.execute(project_id=project_id, plan_id=plan_id)
        _results[job_id] = result.model_dump(mode="json")
        await manager.broadcast({"job_id": job_id, "type": "report", "status": "completed"})
    except Exception as exc:
        _results[job_id] = {"error": str(exc)}
        await manager.broadcast({"job_id": job_id, "type": "report", "status": "failed", "error": str(exc)})


@router.post(
    "",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a migration report",
)
async def start_report(
    body: ReportRequestBody,
    background: BackgroundTasks,
    use_case: GenerateReportUseCase = Depends(get_report_use_case),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    background.add_task(_run_report, job_id, use_case, body.project_id, body.plan_id)
    return JobAccepted(job_id=job_id)


@router.get(
    "/{job_id}",
    response_model=ReportResponse,
    responses={404: {"description": "Report not found or still generating"}},
    summary="Retrieve a generated report",
)
async def get_report(job_id: str) -> ReportResponse:
    if job_id not in _results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or still in progress")
    return ReportResponse(**_results[job_id])
