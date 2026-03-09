"""Scan routes -- POST /api/scan, GET /api/scan/{id}."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.dtos.scan import ScanRequest
from cloudshift.application.use_cases import ScanProjectUseCase
from cloudshift.domain.value_objects.types import CloudProvider, Language
from cloudshift.presentation.api.dependencies import get_scan_use_case
from cloudshift.presentation.api.schemas import (
    JobAccepted,
    ScanRequestBody,
    ScanResultResponse,
    ScanFileRequestBody,
    FileScanResultResponse,
    PatternMatchResponse,
)
from cloudshift.presentation.api.websocket import manager
from cloudshift.presentation.api.dependencies import get_container
from cloudshift.domain.value_objects.types import Language

router = APIRouter(prefix="/api/scan", tags=["scan"])

# In-memory result store (swap for Redis / DB in production).
_results: dict[str, Any] = {}


async def _run_scan(job_id: str, use_case: ScanProjectUseCase, dto: ScanRequest) -> None:
    await manager.broadcast({"job_id": job_id, "type": "scan", "status": "started"})
    try:
        result = await use_case.execute(dto)
        _results[job_id] = result.model_dump(mode="json")
        await manager.broadcast({"job_id": job_id, "type": "scan", "status": "completed"})
    except Exception as exc:
        _results[job_id] = {"error": str(exc)}
        await manager.broadcast({"job_id": job_id, "type": "scan", "status": "failed", "error": str(exc)})


@router.post(
    "/file",
    response_model=FileScanResultResponse,
    summary="Scan a single file for patterns (VS Code)",
)
async def scan_file(
    body: ScanFileRequestBody,
    container: Any = Depends(get_container),
) -> FileScanResultResponse:
    parser = container.parser
    engine = container.pattern_engine

    # 1. Detect language
    lang_val = await parser.detect_language(body.file_path, body.content)
    if not lang_val:
        return FileScanResultResponse(file=body.file_path, patterns=[])
    
    # 2. Parse AST
    # The adapter expects Language enum
    ast = await parser.parse_source(body.content, lang_val, body.file_path)

    # 3. Match patterns
    transforms = await engine.match_patterns(ast)

    # 4. Map to response
    patterns = []
    for t in transforms:
        patterns.append(
            PatternMatchResponse(
                line=t.line_start,
                end_line=t.line_end,
                column=0,  # TODO: precise column from AST
                end_column=0,
                pattern_id=t.pattern_id,
                pattern_name=t.pattern_name,
                severity="warning", # TODO: map from pattern metadata
                message=f"Detected {t.pattern_name}", # TODO: better message
                source_provider="AWS", # TODO: from pattern
                target_provider="GCP", # TODO: from pattern
            )
        )
    
    return FileScanResultResponse(file=body.file_path, patterns=patterns)


@router.post(
    "",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a project scan",
)
async def start_scan(
    body: ScanRequestBody,
    background: BackgroundTasks,
    use_case: ScanProjectUseCase = Depends(get_scan_use_case),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    dto = ScanRequest(
        root_path=body.root_path,
        source_provider=CloudProvider[body.source_provider.value],
        target_provider=CloudProvider[body.target_provider.value],
        languages=[Language[l.value] for l in body.languages],
        exclude_patterns=body.exclude_patterns,
    )
    background.add_task(_run_scan, job_id, use_case, dto)
    return JobAccepted(job_id=job_id)


@router.get(
    "/{job_id}",
    response_model=ScanResultResponse,
    responses={404: {"description": "Job not found or still running"}},
    summary="Retrieve scan results",
)
async def get_scan_result(job_id: str) -> ScanResultResponse:
    if job_id not in _results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found or still in progress")
    return ScanResultResponse(**_results[job_id])
