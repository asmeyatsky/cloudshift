"""Pydantic request/response models for the REST API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Shared enums (mirror domain but kept API-local for decoupling)
# ---------------------------------------------------------------------------

class CloudProviderParam(str, Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"


class LanguageParam(str, Enum):
    PYTHON = "PYTHON"
    TYPESCRIPT = "TYPESCRIPT"
    HCL = "HCL"
    CLOUDFORMATION = "CLOUDFORMATION"


class SeverityParam(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Generic wrappers
# ---------------------------------------------------------------------------

class JobAccepted(BaseModel):
    """Returned when a background job is queued."""

    job_id: str
    status: str = "accepted"


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

class ScanRequestBody(BaseModel):
    root_path: str = Field(description="Absolute path to the project root.")
    source_provider: CloudProviderParam
    target_provider: CloudProviderParam
    languages: list[LanguageParam] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def uppercase_enums(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ('source_provider', 'target_provider'):
                if field in data and isinstance(data[field], str):
                    data[field] = data[field].upper()
            if 'languages' in data and isinstance(data['languages'], list):
                data['languages'] = [l.upper() if isinstance(l, str) else l for l in data['languages']]
        return data


class FileEntryResponse(BaseModel):
    path: str
    language: str | None = None
    services_detected: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    line_count: int = 0


class ScanFileRequestBody(BaseModel):
    file_path: str = Field(alias="filePath")
    content: str

    model_config = {"populate_by_name": True}


class ScanResultResponse(BaseModel):
    project_id: str
    root_path: str
    source_provider: str
    target_provider: str
    files: list[FileEntryResponse] = Field(default_factory=list)
    total_files_scanned: int = 0
    services_found: list[str] = Field(default_factory=list)
    error: str | None = None


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return "".join(p.capitalize() if i > 0 else p for i, p in enumerate(parts))


class PatternMatchResponse(BaseModel):
    line: int
    end_line: int
    column: int
    end_column: int
    pattern_id: str
    pattern_name: str
    severity: str
    message: str
    source_provider: str
    target_provider: str

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=_to_camel,
    )


class FileScanResultResponse(BaseModel):
    file: str
    patterns: list[PatternMatchResponse] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

class PlanRequestBody(BaseModel):
    project_id: str
    manifest_id: str
    strategy: str = Field(default="conservative")
    max_parallel: int = Field(default=4, ge=1)


class TransformStepResponse(BaseModel):
    step_id: str
    file_path: str
    pattern_id: str
    description: str
    confidence: float = 0.0
    depends_on: list[str] = Field(default_factory=list)


class PlanResultResponse(BaseModel):
    plan_id: str
    project_id: str
    steps: list[TransformStepResponse] = Field(default_factory=list)
    estimated_files_changed: int = 0
    estimated_confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Apply (transform)
# ---------------------------------------------------------------------------

class ApplyRequestBody(BaseModel):
    plan_id: str
    step_ids: list[str] = Field(default_factory=list)
    dry_run: bool = False
    backup: bool = True


class HunkResponse(BaseModel):
    start_line: int
    end_line: int
    original_text: str
    modified_text: str
    context: str = ""


class DiffResponse(BaseModel):
    file_path: str
    original_hash: str
    modified_hash: str
    hunks: list[HunkResponse] = Field(default_factory=list)


class ApplyResultResponse(BaseModel):
    plan_id: str
    applied_steps: list[str] = Field(default_factory=list)
    diffs: list[DiffResponse] = Field(default_factory=list)
    files_modified: int = 0
    success: bool = True
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

class ValidateRequestBody(BaseModel):
    plan_id: str
    check_ast_equivalence: bool = True
    check_residual_refs: bool = True
    check_sdk_surface: bool = True
    run_tests: bool = False
    test_command: str | None = None


class IssueResponse(BaseModel):
    message: str
    severity: SeverityParam
    file_path: str | None = None
    line: int | None = None
    rule: str | None = None


class ValidateResultResponse(BaseModel):
    plan_id: str
    passed: bool = True
    issues: list[IssueResponse] = Field(default_factory=list)
    ast_equivalent: bool | None = None
    residual_refs_found: int = 0
    sdk_coverage: float = 0.0
    tests_passed: bool | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

class PatternResponse(BaseModel):
    pattern_id: str
    name: str
    description: str = ""
    source_provider: str
    target_provider: str
    language: str
    source_snippet: str = ""
    target_snippet: str = ""
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    version: str = "1.0.0"


class PatternSearchBody(BaseModel):
    query: str = ""
    source_provider: CloudProviderParam | None = None
    target_provider: CloudProviderParam | None = None
    language: LanguageParam | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)


class PatternSearchResponse(BaseModel):
    patterns: list[PatternResponse] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class ReportRequestBody(BaseModel):
    project_id: str
    plan_id: str


class FileSummaryResponse(BaseModel):
    path: str
    services_migrated: list[str] = Field(default_factory=list)
    issues: int = 0
    confidence: float = 0.0


class ReportResponse(BaseModel):
    report_id: str
    project_id: str
    source_provider: str
    target_provider: str
    generated_at: datetime
    total_files: int = 0
    files_changed: int = 0
    patterns_applied: int = 0
    validation_passed: bool = True
    overall_confidence: float = 0.0
    file_summaries: list[FileSummaryResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class ConfigResponse(BaseModel):
    """Current application configuration (safe subset)."""

    source_provider: CloudProviderParam | None = None
    target_provider: CloudProviderParam | None = None
    default_strategy: str = "conservative"
    max_parallel: int = 4
    backup_enabled: bool = True
    extra: dict[str, object] = Field(default_factory=dict)


class ConfigUpdateBody(BaseModel):
    source_provider: CloudProviderParam | None = None
    target_provider: CloudProviderParam | None = None
    default_strategy: str | None = None
    max_parallel: int | None = Field(default=None, ge=1)
    backup_enabled: bool | None = None
    extra: dict[str, object] | None = None
