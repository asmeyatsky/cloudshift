"""Manifest route for VS Code: GET /api/manifest."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from cloudshift.presentation.api.dependencies import get_container
from cloudshift.presentation.api.schemas import ManifestEntryResponse

router = APIRouter(prefix="/api/manifest", tags=["manifest"])


@router.get(
    "",
    response_model=list[ManifestEntryResponse],
    summary="Get manifest entries (VS Code)",
)
async def get_manifest(
    project_id: str | None = Query(default=None, description="Project ID from a prior scan; if omitted, returns []"),
    container=Depends(get_container),
) -> list[ManifestEntryResponse]:
    """Return manifest entries for a project. Requires project_id from a completed scan."""
    if not project_id:
        return []
    repo = getattr(container, "project_repository", None)
    if not repo:
        return []
    manifest = await repo.get_manifest(project_id)
    if not manifest or not getattr(manifest, "entries", None):
        return []
    return [
        ManifestEntryResponse(
            file=getattr(entry, "file_path", "") or getattr(entry, "path", ""),
            patterns=[],  # Scan manifest does not store per-file pattern matches
            status="pending",
        )
        for entry in manifest.entries
    ]
