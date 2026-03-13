"""Apply routes -- POST /api/apply, GET /api/apply/{id}."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cloudshift.application.dtos.transform import TransformRequest
from cloudshift.application.use_cases import ApplyTransformationUseCase
from cloudshift.domain.value_objects.types import Language
from cloudshift.presentation.api.dependencies import get_apply_use_case, get_container
from cloudshift.presentation.api.plan_store import get_plan
from cloudshift.presentation.api.schemas import (
    ApplyRequestBody,
    ApplyResultResponse,
    JobAccepted,
)
from cloudshift.presentation.api.websocket import manager

router = APIRouter(prefix="/api/apply", tags=["apply"])

_results: dict[str, Any] = {}


def _infer_language(file_path: str) -> Language:
    ext = (Path(file_path).suffix or "").lstrip(".").lower()
    if ext in ("py",):
        return Language.PYTHON
    if ext in ("ts", "tsx", "js", "jsx"):
        return Language.TYPESCRIPT
    if ext in ("tf", "hcl"):
        return Language.HCL
    if ext in ("yaml", "yml", "json") and "template" in file_path.lower():
        return Language.CLOUDFORMATION
    return Language.PYTHON


async def _llm_fallback_refactor(
    container: Any,
    plan: Any,
    manifest: Any,
) -> list[dict[str, Any]]:
    """When pattern apply produced 0 files, refactor each manifest file via LLM to get GCP code."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return []
    if getattr(llm, "__class__", None) and getattr(llm.__class__, "__name__", "") == "NullLLMAdapter":
        return []
    root = Path(getattr(manifest, "root_path", "") or "")
    if not root.is_dir():
        return []
    source_provider = (getattr(manifest, "source_provider", "aws") or "aws").upper()
    target_provider = (getattr(manifest, "target_provider", "gcp") or "gcp").upper()
    instruction = (
        f"Refactor this {source_provider} code to equivalent {target_provider} (GCP) code. "
        "Preserve behavior and logic. Use GCP SDKs (e.g. google-cloud-* for Python). "
        "Return only the refactored code in a single fenced code block, no explanation."
    )
    details: list[dict[str, Any]] = []
    root_resolved = root.resolve()
    for entry in getattr(manifest, "entries", []) or []:
        file_path = getattr(entry, "file_path", "") or getattr(entry, "path", "")
        if not file_path:
            continue
        path = Path(file_path).resolve() if Path(file_path).is_absolute() else (root / file_path).resolve()
        if not path.is_file():
            continue
        try:
            path = path.resolve().relative_to(root_resolved)
        except ValueError:
            continue
        try:
            content = await asyncio.to_thread((root_resolved / path).read_text, encoding="utf-8")
        except Exception:
            continue
        path_str = str(path).replace("\\", "/")
        lang = _infer_language(path_str)
        try:
            refactored = await llm.transform_code(content, instruction, lang)
        except Exception:
            refactored = content
        refactored = (refactored or "").strip() or content
        details.append({
            "path": path_str,
            "original_content": content,
            "modified_content": refactored,
            "language": lang.name.lower(),
        })
    return details


async def _run_apply(
    job_id: str,
    use_case: ApplyTransformationUseCase,
    dto: TransformRequest,
    container: Any,
) -> None:
    await manager.broadcast({"job_id": job_id, "type": "apply", "status": "started"})
    try:
        result = await use_case.execute(dto)
        result_dump = result.model_dump(mode="json")
        modified_details = result_dump.get("modified_file_details") or []
        plan = await get_plan(dto.plan_id)
        manifest = None
        if plan and getattr(plan, "project_id", None):
            manifest = await container.project_repository.get_manifest(plan.project_id)
        if result.success and len(modified_details) == 0 and manifest and getattr(manifest, "entries", None):
            fallback = await _llm_fallback_refactor(container, plan, manifest)
            if fallback:
                result_dump["modified_file_details"] = fallback
                result_dump["files_modified"] = len(fallback)
        _results[job_id] = result_dump
        if result_dump.get("modified_file_details") and manifest:
            container.project_repository.save_transform_metadata(
                dto.plan_id,
                getattr(manifest, "root_path", ""),
                getattr(manifest, "source_provider", "aws"),
                getattr(manifest, "target_provider", "gcp"),
                result_dump["modified_file_details"],
            )
        await manager.broadcast({"job_id": job_id, "type": "apply", "status": "completed"})
    except Exception as exc:
        err_msg = str(exc)
        _results[job_id] = {
            "plan_id": dto.plan_id,
            "applied_steps": [],
            "diffs": [],
            "files_modified": 0,
            "success": False,
            "errors": [err_msg],
        }
        await manager.broadcast({"job_id": job_id, "type": "apply", "status": "failed", "error": err_msg})


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
    container: Any = Depends(get_container),
) -> JobAccepted:
    job_id = uuid.uuid4().hex[:12]
    dto = TransformRequest(
        plan_id=body.plan_id,
        step_ids=body.step_ids,
        dry_run=body.dry_run,
        backup=body.backup,
    )
    background.add_task(_run_apply, job_id, use_case, dto, container)
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
