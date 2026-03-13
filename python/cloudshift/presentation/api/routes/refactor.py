"""Refactor routes: POST /api/refactor/file, POST /api/refactor/selection, POST /api/refactor/project.

Refactor flow: try pattern matching first; only use LLM when no pattern matches.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

from cloudshift.domain.value_objects.types import CloudProvider, Language
from cloudshift.presentation.api.dependencies import get_container
from cloudshift.presentation.api.schemas import (
    RefactorFileRequestBody,
    RefactorProjectRequestBody,
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


def _provider_enum(provider: str) -> CloudProvider | None:
    """Map source_provider/target_provider string to CloudProvider."""
    if not provider:
        return None
    u = (provider or "").upper()
    try:
        return CloudProvider(u)
    except (KeyError, ValueError):
        return None


async def _refactor_with_patterns(
    content: str,
    file_path: str,
    source_provider: str,
    target_provider: str,
    container,
) -> str | None:
    """Try pattern-based refactor. Returns refactored content if any pattern matched, else None."""
    src = _provider_enum(source_provider)
    tgt = _provider_enum(target_provider)
    if src is None or tgt is None:
        return None
    if tgt != CloudProvider.GCP:
        return None
    store = getattr(container, "pattern_store", None)
    engine = getattr(container, "pattern_engine", None)
    if store is None or engine is None:
        return None
    lang = _infer_language(file_path)
    patterns = store.list_all(
        source_provider=src,
        target_provider=tgt,
        language=lang,
    )
    if not patterns:
        return None
    try:
        matches = await asyncio.to_thread(engine.match, content, patterns, lang)
    except Exception:
        return None
    if not matches:
        return None
    modified = content
    for pattern, _line_start, _line_end in matches:
        try:
            modified = await asyncio.to_thread(engine.apply, modified, pattern, lang)
        except Exception:
            continue
    return modified if modified != content else None


def _is_llm_configured(container) -> bool:
    """True if the container has a real LLM (Gemini or Ollama), not NullLLMAdapter."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return False
    return getattr(llm.__class__, "__name__", "") != "NullLLMAdapter"


def _llm_type(container) -> str:
    """Return the LLM adapter class name for diagnostics."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return "None"
    return getattr(llm.__class__, "__name__", "unknown")


def _refactor_instruction(source: str, target: str) -> str:
    """Build a clear migration instruction so the LLM returns GCP code, not the original."""
    base = (
        f"Refactor this {source} code to equivalent {target} (GCP) code. "
        "Preserve behavior and logic. "
        "Use GCP SDKs: for Python use google-cloud-* packages (e.g. google-cloud-storage instead of Azure Blob, google-auth for credentials). "
        "Return ONLY the refactored code in a single fenced code block (e.g. ```python ... ```), no explanation or duplicate original."
    )
    if source == "AZURE":
        base += (
            " For Azure Blob Storage use Google Cloud Storage (google-cloud-storage). "
            "For DefaultAzureCredential use Google Application Default Credentials (google.auth.default)."
        )
    return base


async def _refactor_with_llm(
    content: str,
    file_path: str,
    source_provider: str,
    target_provider: str,
    container,
) -> str:
    """Use LLM to refactor content to GCP. Returns refactored content or raises on failure."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return content
    if getattr(llm, "__class__", None) and getattr(llm.__class__, "__name__", "") == "NullLLMAdapter":
        return content
    source = (source_provider or "AWS").upper()
    target = (target_provider or "GCP").upper()
    instruction = _refactor_instruction(source, target)
    lang = _infer_language(file_path)
    refactored = await llm.transform_code(content, instruction, lang)
    out = (refactored or "").strip()
    if not out or out == content:
        raise ValueError(
            "LLM did not return refactored code (empty or unchanged). Check server logs for Gemini errors."
        )
    return out


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
    """Refactor file content to GCP: try patterns first, then LLM if no pattern matches."""
    logger.info("Refactor file: llm_type=%s", _llm_type(container))
    try:
        refactored = await _refactor_with_patterns(
            body.content,
            body.file_path,
            body.source_provider,
            body.target_provider,
            container,
        )
        if refactored is None:
            refactored = await _refactor_with_llm(
                body.content,
                body.file_path,
                body.source_provider,
                body.target_provider,
                container,
            )
            if refactored == body.content and not _is_llm_configured(container):
                llm_type = _llm_type(container)
                logger.warning("Refactor file: no pattern match and LLM not configured (llm=%s)", llm_type)
                raise HTTPException(
                    status_code=503,
                    detail=f"No pattern matched and LLM is not configured (server llm={llm_type}). Fix: GitHub repo → Settings → Secrets → Actions: set GEMINI_API_KEY, then push to main to redeploy. Or set CLOUDSHIFT_DEPLOYMENT_MODE=demo and CLOUDSHIFT_GEMINI_API_KEY on the server. Get a key at https://aistudio.google.com/apikey",
                )
            if refactored == body.content and _is_llm_configured(container):
                logger.info("Refactor file: LLM configured but no changes produced (returning 200)")
        changes = _build_changes(body.content, refactored)
        return RefactorResultResponse(
            original_file=body.file_path,
            refactored_content=refactored,
            changes=[RefactorChangeResponse(**c) for c in changes],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Refactor file failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Refactor failed: {str(e)[:500]}",
        ) from e


@router.post(
    "/selection",
    response_model=RefactorResultResponse,
    summary="Refactor a selection (VS Code)",
)
async def refactor_selection(
    body: RefactorSelectionRequestBody,
    container=Depends(get_container),
) -> RefactorResultResponse:
    """Refactor selected lines to GCP: try patterns first, then LLM if no pattern matches."""
    logger.info("Refactor selection: llm_type=%s", _llm_type(container))
    try:
        lines = body.content.splitlines()
        start = max(0, body.start_line - 1)
        end = min(len(lines), body.end_line)
        if start >= end:
            refactored_content = body.content
        else:
            selected = "\n".join(lines[start:end])
            refactored_selection = await _refactor_with_patterns(
                selected,
                body.file_path,
                body.source_provider,
                body.target_provider,
                container,
            )
            if refactored_selection is None:
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
        if refactored_content == body.content and not _is_llm_configured(container):
            llm_type = _llm_type(container)
            logger.warning("Refactor selection: no pattern match and LLM not configured (llm=%s)", llm_type)
            raise HTTPException(
                status_code=503,
                detail=f"No pattern matched and LLM is not configured (server llm={llm_type}). Fix: GitHub repo → Settings → Secrets → Actions: set GEMINI_API_KEY, then push to main to redeploy. Or set CLOUDSHIFT_DEPLOYMENT_MODE=demo and CLOUDSHIFT_GEMINI_API_KEY on the server. Get a key at https://aistudio.google.com/apikey",
            )
        if refactored_content == body.content and _is_llm_configured(container):
            logger.info("Refactor selection: LLM configured but no changes produced (returning 200)")
        changes = _build_changes(body.content, refactored_content)
        return RefactorResultResponse(
            original_file=body.file_path,
            refactored_content=refactored_content,
            changes=[RefactorChangeResponse(**c) for c in changes],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Refactor selection failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Refactor failed: {str(e)[:500]}",
        ) from e


# ---------------------------------------------------------------------------
# Project-wide streaming refactor
# ---------------------------------------------------------------------------

_SCANNABLE_EXTENSIONS = frozenset(
    {"py", "ts", "tsx", "js", "jsx", "tf", "hcl", "json", "yml", "yaml", "bicep"}
)


async def _refactor_project_stream(body: RefactorProjectRequestBody, container):
    """Async generator yielding NDJSON events for project-wide refactor."""
    # Resolve root_path from project_id or body.root_path
    root_path = body.root_path
    if not root_path:
        repo = getattr(container, "project_repository", None)
        if repo is None:
            yield json.dumps({"type": "error", "message": "No project repository configured"}) + "\n"
            return
        project = repo.get(body.project_id)
        if project is None:
            yield json.dumps({"type": "error", "message": f"Project {body.project_id} not found"}) + "\n"
            return
        root_path = str(project.root_path)

    root = Path(root_path)
    if not root.is_dir():
        yield json.dumps({"type": "error", "message": f"Directory not found: {root_path}"}) + "\n"
        return

    # Walk directory for scannable files
    walker = getattr(container, "walker", None)
    if walker is not None:
        try:
            all_files = walker.walk_directory(str(root))
        except Exception:
            all_files = [str(p) for p in root.rglob("*") if p.is_file()]
    else:
        all_files = [str(p) for p in root.rglob("*") if p.is_file()]

    scannable = [
        f for f in all_files
        if Path(f).suffix.lstrip(".").lower() in _SCANNABLE_EXTENSIONS
    ]
    total = len(scannable)

    if total == 0:
        yield json.dumps({"type": "complete", "total": 0, "changed": 0, "pattern_count": 0, "llm_count": 0, "skipped": 0, "llm_configured": _is_llm_configured(container)}) + "\n"
        return

    changed_count = 0
    pattern_count = 0
    llm_count = 0
    skipped_count = 0

    for idx, file_path in enumerate(scannable):
        rel_path = str(Path(file_path).relative_to(root)) if file_path.startswith(str(root)) else file_path

        yield json.dumps({"type": "progress", "file": rel_path, "index": idx, "total": total}) + "\n"

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.debug("Skipping unreadable file %s: %s", file_path, exc)
            skipped_count += 1
            yield json.dumps({"type": "file_result", "file": rel_path, "changed": False, "method": "skipped"}) + "\n"
            continue

        method = "skipped"
        modified = None

        # Try pattern-based refactor
        try:
            modified = await _refactor_with_patterns(
                content, file_path, body.source_provider, body.target_provider, container,
            )
            if modified is not None:
                method = "pattern"
        except Exception as exc:
            logger.debug("Pattern refactor error for %s: %s", file_path, exc)

        # LLM fallback
        if modified is None and _is_llm_configured(container):
            try:
                llm_result = await _refactor_with_llm(
                    content, file_path, body.source_provider, body.target_provider, container,
                )
                if llm_result != content:
                    modified = llm_result
                    method = "llm"
            except Exception as exc:
                logger.debug("LLM refactor error for %s: %s", file_path, exc)

        if modified is not None and modified != content:
            changed_count += 1
            if method == "pattern":
                pattern_count += 1
            elif method == "llm":
                llm_count += 1
            yield json.dumps({
                "type": "file_result",
                "file": rel_path,
                "original": content,
                "modified": modified,
                "changed": True,
                "method": method,
            }) + "\n"
        else:
            skipped_count += 1
            yield json.dumps({"type": "file_result", "file": rel_path, "changed": False, "method": "skipped"}) + "\n"

        # Yield control so the event loop stays responsive
        await asyncio.sleep(0)

    yield json.dumps({
        "type": "complete",
        "total": total,
        "changed": changed_count,
        "pattern_count": pattern_count,
        "llm_count": llm_count,
        "skipped": skipped_count,
        "llm_configured": _is_llm_configured(container),
    }) + "\n"


@router.post("/project", summary="Refactor entire project (streaming NDJSON)")
async def refactor_project(
    body: RefactorProjectRequestBody,
    container=Depends(get_container),
):
    """Stream project-wide refactor results as NDJSON. Each line is a JSON object."""
    return StreamingResponse(
        _refactor_project_stream(body, container),
        media_type="application/x-ndjson",
    )
