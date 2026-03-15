"""Scan routes -- POST /api/scan, GET /api/scan/{id}, POST /api/scan/estimate."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
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
    ScanEstimateRequestBody,
    ScanEstimateResponse,
    ScanFileRequestBody,
    FileScanResultResponse,
    PatternMatchResponse,
)
from cloudshift.presentation.api.websocket import manager
from cloudshift.presentation.api.dependencies import get_container
from cloudshift.domain.value_objects.types import Language

router = APIRouter(prefix="/api/scan", tags=["scan"])

# Extensions that the scan/plan pipeline processes (same as scan use case).
SCANNABLE_EXTENSIONS = frozenset(
    {"py", "ts", "tsx", "js", "jsx", "tf", "hcl", "json", "yml", "yaml", "bicep"}
)

# In-memory result store (swap for Redis / DB in production).
_results: dict[str, Any] = {}


async def _run_scan(
    job_id: str,
    use_case: ScanProjectUseCase,
    dto: ScanRequest,
    project_id: str | None,
    container: Any,
) -> None:
    await manager.broadcast({"job_id": job_id, "type": "scan", "status": "started"})
    try:
        result = await use_case.execute(dto)
        dumped = result.model_dump(mode="json")
        _results[job_id] = dumped
        if project_id and not result.error:
            repo = container.project_repository
            # Call sync DB write in same thread (SQLite connection is thread-local).
            repo.save_scan_manifest(
                project_id,
                result.root_path,
                result.source_provider.name if hasattr(result.source_provider, "name") else str(result.source_provider),
                result.target_provider.name if hasattr(result.target_provider, "name") else str(result.target_provider),
                dumped.get("files", []),
            )
        await manager.broadcast({"job_id": job_id, "type": "scan", "status": "completed"})
    except Exception as exc:
        err_msg = str(exc)
        _results[job_id] = {
            "project_id": "",
            "root_path": dto.root_path,
            "source_provider": dto.source_provider.name,
            "target_provider": dto.target_provider.name,
            "files": [],
            "total_files_scanned": 0,
            "services_found": [],
            "error": err_msg,
        }
        await manager.broadcast({"job_id": job_id, "type": "scan", "status": "failed", "error": err_msg})


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
    "/estimate",
    response_model=ScanEstimateResponse,
    summary="Estimate repo size before running pipeline",
)
async def estimate_repo_size(
    body: ScanEstimateRequestBody,
    container: Any = Depends(get_container),
) -> ScanEstimateResponse:
    """Return file counts and estimated plan time. Path must be under allowed_scan_paths."""
    from cloudshift.infrastructure.config.dependency_injection import GIT_IMPORT_BASE

    raw_path = body.root_path
    # Resolve __demo__/ prefix to the demos/ directory
    if raw_path and raw_path.startswith("__demo__/"):
        demo_rel = raw_path[len("__demo__/"):]
        project_root = Path(__file__).resolve().parents[5]
        raw_path = str(project_root / "demos" / demo_rel)

    try:
        root = Path(raw_path).resolve()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {e}") from e

    settings = getattr(container, "_settings", None)
    allowed = list(getattr(settings, "allowed_scan_paths", [Path(".")])) if settings else [Path(".")]
    if GIT_IMPORT_BASE not in allowed:
        allowed.append(GIT_IMPORT_BASE)
    # Also allow the demos/ directory for __demo__ paths
    demos_dir = Path(__file__).resolve().parents[5] / "demos"
    if demos_dir not in allowed:
        allowed.append(demos_dir)
    allowed_resolved = [p.resolve() for p in allowed]
    if not any(root == p or p in root.parents for p in allowed_resolved):
        raise HTTPException(
            status_code=403,
            detail="Path not under allowed_scan_paths",
        )

    if not root.exists():
        hint = ""
        if "/tmp/cloudshift" in str(root):
            hint = " The cloned repo may be on another server instance. Use Re-import from Git to clone again on this instance."
        raise HTTPException(
            status_code=400,
            detail=(
                f"Path does not exist on the server: {root}. "
                "If you imported from Git, use the path returned by the import."
                + hint
                + " For local/demo projects, ensure the path exists where the backend is running."
            ),
        )
    if not root.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {root}. Scan and estimate require a directory.",
        )

    try:
        paths = await asyncio.to_thread(
            container.walker.list_files, root, None
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not walk path: {e}") from e

    total = len(paths)
    by_ext: dict[str, int] = {}
    for p in paths:
        ext = (p.suffix or "").lstrip(".").lower()
        if ext:
            by_ext[ext] = by_ext.get(ext, 0) + 1
    scannable = sum(by_ext.get(ext, 0) for ext in SCANNABLE_EXTENSIONS)

    # Rough: ~2 sec per scannable file for plan (read + pattern match).
    estimated_plan_minutes = max(0.5, scannable * 2.0 / 60.0)
    if scannable > 500:
        message = "Very large repo. Plan may take 15–30+ minutes. Consider running on a smaller subtree."
    elif scannable > 200:
        message = "Large repo. Plan may take 10–20 minutes."
    elif scannable > 50:
        message = "Moderate size. Plan may take a few minutes."
    else:
        message = "Small repo. Plan should complete quickly."

    return ScanEstimateResponse(
        total_files=total,
        scannable_files=scannable,
        by_extension=by_ext,
        estimated_plan_minutes=round(estimated_plan_minutes, 1),
        message=message,
    )


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
    container: Any = Depends(get_container),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    dto = ScanRequest(
        root_path=body.root_path,
        source_provider=CloudProvider[body.source_provider.value],
        target_provider=CloudProvider[body.target_provider.value],
        languages=[Language[l.value] for l in body.languages],
        exclude_patterns=body.exclude_patterns,
    )
    background.add_task(_run_scan, job_id, use_case, dto, body.project_id, container)
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
