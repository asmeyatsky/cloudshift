"""DTO for audit / migration reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from cloudshift.domain.value_objects.types import CloudProvider


class FileSummary(BaseModel):
    """Per-file summary in the report."""

    path: str
    services_migrated: list[str] = Field(default_factory=list)
    issues: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ReportDTO(BaseModel):
    """Full migration audit report."""

    report_id: str
    project_id: str
    source_provider: CloudProvider
    target_provider: CloudProvider
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_files: int = 0
    files_changed: int = 0
    patterns_applied: int = 0
    validation_passed: bool = True
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    file_summaries: list[FileSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: str = ""
