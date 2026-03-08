"""Pattern routes -- GET /api/patterns, GET /api/patterns/{id}, POST /api/patterns/search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from cloudshift.application.dtos.pattern import PatternCatalogTestResponse
from cloudshift.presentation.api.dependencies import get_patterns_use_case

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("", summary="List all available migration patterns")
async def list_patterns(use_case=Depends(get_patterns_use_case)):
    patterns = await use_case.list_patterns()
    return [p.model_dump() if hasattr(p, 'model_dump') else p for p in patterns]


@router.post(
    "/test",
    response_model=PatternCatalogTestResponse,
    summary="Run self-tests for all patterns",
)
async def test_patterns(use_case=Depends(get_patterns_use_case)):
    """Run built-in examples for all patterns and return results."""
    return await use_case.test_patterns()


@router.get("/{pattern_id}", summary="Get a single pattern by ID")
async def get_pattern(pattern_id: str, use_case=Depends(get_patterns_use_case)):
    pattern = await use_case.get_pattern(pattern_id)
    if pattern is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pattern not found")
    return pattern


@router.post("/search", summary="Search patterns with filters")
async def search_patterns(body: dict, use_case=Depends(get_patterns_use_case)):
    query = body.get("query", "")
    results = await use_case.search_patterns(query=query)
    return {"patterns": [p.model_dump() if hasattr(p, 'model_dump') else p for p in results], "total": len(results)}
