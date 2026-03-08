"""DTO for pattern management."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cloudshift.domain.value_objects.types import CloudProvider, Language


class PatternDTO(BaseModel):
    """Portable representation of a migration pattern."""

    pattern_id: str
    name: str
    description: str = ""
    source_provider: CloudProvider
    target_provider: CloudProvider
    language: Language
    source_snippet: str = ""
    target_snippet: str = ""
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    version: str = "1.0.0"


class PatternTestResult(BaseModel):
    """Result of a self-test for a single pattern."""

    pattern_id: str
    success: bool
    error: str | None = None
    input: str | None = None
    expected: str | None = None
    actual: str | None = None


class PatternCatalogTestResponse(BaseModel):
    """Aggregated results of testing all patterns in the catalog."""

    total_patterns: int
    passed: int
    failed: int
    results: list[PatternTestResult] = Field(default_factory=list)
