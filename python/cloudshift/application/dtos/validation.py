"""DTOs for the validate-transformation use case."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cloudshift.domain.value_objects.types import Severity


class IssueDTO(BaseModel):
    """A single validation issue."""

    message: str
    severity: Severity
    file_path: str | None = None
    line: int | None = None
    rule: str | None = None


class ValidationRequest(BaseModel):
    """Input for validating transformations."""

    plan_id: str = Field(description="ID of the executed plan.")
    check_ast_equivalence: bool = Field(default=True, description="Run AST-level equivalence checks.")
    check_residual_refs: bool = Field(default=True, description="Scan for residual source-provider references.")
    check_sdk_surface: bool = Field(default=True, description="Verify target SDK surface coverage.")
    run_tests: bool = Field(default=False, description="Optionally invoke the project test suite.")
    test_command: str | None = Field(default=None, description="Custom test command to run.")


class ValidationResult(BaseModel):
    """Output of the validate-transformation use case."""

    plan_id: str
    passed: bool = True
    issues: list[IssueDTO] = Field(default_factory=list)
    ast_equivalent: bool | None = None
    residual_refs_found: int = 0
    sdk_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    tests_passed: bool | None = None
    error: str | None = None
