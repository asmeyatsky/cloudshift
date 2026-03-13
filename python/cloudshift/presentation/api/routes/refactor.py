"""Refactor routes for VS Code extension: POST /api/refactor/file, POST /api/refactor/selection."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from cloudshift.domain.value_objects.types import Language
from cloudshift.presentation.api.dependencies import get_container
from cloudshift.presentation.api.schemas import (
    RefactorFileRequestBody,
    RefactorResultResponse,
    RefactorSelectionRequestBody,
    RefactorChangeResponse,
)

router = APIRouter(prefix="/api/refactor", tags=["refactor"])


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


def _is_llm_configured(container) -> bool:
    """True if the container has a real LLM (Gemini or Ollama), not NullLLMAdapter."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return False
    return getattr(llm.__class__, "__name__", "") != "NullLLMAdapter"


async def _refactor_with_llm(
    content: str,
    file_path: str,
    source_provider: str,
    target_provider: str,
    container,
) -> str:
    """Use LLM to refactor content to GCP. Returns refactored content or original if no LLM."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return content
    if getattr(llm, "__class__", None) and getattr(llm.__class__, "__name__", "") == "NullLLMAdapter":
        return content
    source = (source_provider or "AWS").upper()
    target = (target_provider or "GCP").upper()
    instruction = (
        f"Refactor this {source} code to equivalent {target} (GCP) code. "
        "Preserve behavior and logic. Use GCP SDKs (e.g. google-cloud-* for Python). "
        "Return only the refactored code in a single fenced code block, no explanation."
    )
    lang = _infer_language(file_path)
    try:
        refactored = await llm.transform_code(content, instruction, lang)
        return (refactored or "").strip() or content
    except Exception:
        return content


def _build_changes(original: str, refactored: str) -> list[dict]:
    """Build a list of RefactorChangeResponse-compatible dicts from line diff."""
    orig_lines = original.splitlines()
    ref_lines = refactored.splitlines()
    changes = []
    if original != refactored and (orig_lines or ref_lines):
        if len(orig_lines) <= 1 and len(ref_lines) <= 1:
            changes.append({
                "line": 1,
                "original": original,
                "replacement": refactored,
                "description": "Refactored to GCP",
            })
        else:
            for i, (o, r) in enumerate(zip(orig_lines, ref_lines)):
                if o != r:
                    changes.append({
                        "line": i + 1,
                        "original": o,
                        "replacement": r,
                        "description": "Refactored to GCP",
                    })
            for i in range(len(orig_lines), len(ref_lines)):
                changes.append({
                    "line": i + 1,
                    "original": "",
                    "replacement": ref_lines[i],
                    "description": "Added (GCP)",
                })
            for i in range(len(ref_lines), len(orig_lines)):
                changes.append({
                    "line": i + 1,
                    "original": orig_lines[i],
                    "replacement": "",
                    "description": "Removed",
                })
    return changes


@router.post(
    "/file",
    response_model=RefactorResultResponse,
    summary="Refactor a full file (VS Code)",
)
async def refactor_file(
    body: RefactorFileRequestBody,
    container=Depends(get_container),
) -> RefactorResultResponse:
    """Refactor file content to GCP using LLM or pattern engine. Synchronous for editor use."""
    if not _is_llm_configured(container):
        raise HTTPException(
            status_code=503,
            detail="Refactoring requires an LLM. Set CLOUDSHIFT_DEPLOYMENT_MODE=demo and CLOUDSHIFT_GEMINI_API_KEY on the server. Get a key at https://aistudio.google.com/apikey",
        )
    refactored = await _refactor_with_llm(
        body.content,
        body.file_path,
        body.source_provider,
        body.target_provider,
        container,
    )
    changes = _build_changes(body.content, refactored)
    return RefactorResultResponse(
        original_file=body.file_path,
        refactored_content=refactored,
        changes=[RefactorChangeResponse(**c) for c in changes],
    )


@router.post(
    "/selection",
    response_model=RefactorResultResponse,
    summary="Refactor a selection (VS Code)",
)
async def refactor_selection(
    body: RefactorSelectionRequestBody,
    container=Depends(get_container),
) -> RefactorResultResponse:
    """Refactor selected lines to GCP; returns full file content with selection replaced."""
    if not _is_llm_configured(container):
        raise HTTPException(
            status_code=503,
            detail="Refactoring requires an LLM. Set CLOUDSHIFT_DEPLOYMENT_MODE=demo and CLOUDSHIFT_GEMINI_API_KEY on the server. Get a key at https://aistudio.google.com/apikey",
        )
    lines = body.content.splitlines()
    start = max(0, body.start_line - 1)
    end = min(len(lines), body.end_line)
    if start >= end:
        refactored_content = body.content
    else:
        selected = "\n".join(lines[start:end])
        refactored_selection = await _refactor_with_llm(
            selected,
            body.file_path,
            body.source_provider,
            body.target_provider,
            container,
        )
        parts = []
        if start > 0:
            parts.append("\n".join(lines[:start]))
        parts.append(refactored_selection)
        if end < len(lines):
            parts.append("\n".join(lines[end:]))
        refactored_content = "\n".join(parts)
    changes = _build_changes(body.content, refactored_content)
    return RefactorResultResponse(
        original_file=body.file_path,
        refactored_content=refactored_content,
        changes=[RefactorChangeResponse(**c) for c in changes],
    )
