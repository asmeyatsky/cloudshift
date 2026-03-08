"""DTOs for the apply-transformation use case."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiffResult(BaseModel):
    """A unified diff produced for one file."""

    file_path: str
    original_hash: str
    modified_hash: str
    hunks: list[HunkDTO] = Field(default_factory=list)


class HunkDTO(BaseModel):
    """Single hunk within a diff."""

    start_line: int
    end_line: int
    original_text: str
    modified_text: str
    context: str = ""


# Rebuild DiffResult now that HunkDTO is defined.
DiffResult.model_rebuild()


class TransformRequest(BaseModel):
    """Input for applying transformations."""

    plan_id: str = Field(description="ID of the migration plan to execute.")
    step_ids: list[str] = Field(default_factory=list, description="Specific steps to apply; empty means all.")
    dry_run: bool = Field(default=False, description="If True, generate diffs without writing files.")
    backup: bool = Field(default=True, description="Create backups of modified files.")
    check_git_clean: bool = Field(default=True, description="Ensure git repository is clean before applying.")


class TransformResult(BaseModel):
    """Output of the apply-transformation use case."""

    plan_id: str
    applied_steps: list[str] = Field(default_factory=list)
    diffs: list[DiffResult] = Field(default_factory=list)
    files_modified: int = 0
    success: bool = True
    errors: list[str] = Field(default_factory=list)
