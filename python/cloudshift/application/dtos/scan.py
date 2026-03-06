"""DTOs for the scan-project use case."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cloudshift.domain.value_objects.types import CloudProvider, Language


class ScanRequest(BaseModel):
    """Input for scanning a project directory."""

    root_path: str = Field(description="Absolute path to the project root.")
    source_provider: CloudProvider = Field(description="Cloud provider currently in use.")
    target_provider: CloudProvider = Field(description="Cloud provider to migrate towards.")
    languages: list[Language] = Field(default_factory=list, description="Languages to scan; empty means auto-detect.")
    exclude_patterns: list[str] = Field(default_factory=list, description="Glob patterns to exclude from scanning.")

    model_config = {"use_enum_values": False}


class FileEntry(BaseModel):
    """A single file discovered during scanning."""

    path: str
    language: Language | None = None
    services_detected: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    line_count: int = 0


class ScanResult(BaseModel):
    """Output of the scan-project use case."""

    project_id: str
    root_path: str
    source_provider: CloudProvider
    target_provider: CloudProvider
    files: list[FileEntry] = Field(default_factory=list)
    total_files_scanned: int = 0
    services_found: list[str] = Field(default_factory=list)
    error: str | None = None
