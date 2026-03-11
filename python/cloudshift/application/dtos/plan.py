"""DTOs for the generate-plan use case."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransformStep(BaseModel):
    """A single planned transformation step."""

    step_id: str
    file_path: str
    pattern_id: str
    description: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    depends_on: list[str] = Field(default_factory=list)


class StepsByPattern(BaseModel):
    """Steps grouped by pattern for approve-by-pattern UX (one approval per pattern, not per file)."""

    pattern_id: str
    description: str
    count: int
    step_ids: list[str] = Field(default_factory=list)
    file_paths_sample: list[str] = Field(default_factory=list, description="Sample paths for display (e.g. first 5)")


class PlanRequest(BaseModel):
    """Input for generating a migration plan."""

    project_id: str = Field(description="ID of the previously scanned project.")
    manifest_id: str = Field(description="ID of the scan manifest to plan against.")
    strategy: str = Field(default="conservative", description="Migration strategy: conservative | balanced | aggressive.")
    max_parallel: int = Field(default=4, ge=1, description="Maximum parallel transformation steps.")


class PlanResult(BaseModel):
    """Output of the generate-plan use case."""

    plan_id: str
    project_id: str
    steps: list[TransformStep] = Field(default_factory=list)
    steps_by_pattern: list[StepsByPattern] = Field(
        default_factory=list,
        description="Steps grouped by pattern_id for approve-by-pattern (approve once, apply to all similar).",
    )
    estimated_files_changed: int = 0
    estimated_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
