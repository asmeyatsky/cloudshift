"""Validation report entity."""

from __future__ import annotations

from dataclasses import dataclass, field

from cloudshift.domain.value_objects.types import Severity, ValidationIssue


@dataclass(slots=True)
class ValidationReport:
    """Result of validating a set of transformations."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(
            i.severity in (Severity.ERROR, Severity.CRITICAL) for i in self.issues
        )

    @property
    def error_count(self) -> int:
        return sum(
            1 for i in self.issues
            if i.severity in (Severity.ERROR, Severity.CRITICAL)
        )

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity is Severity.WARNING)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.issues),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "info": sum(1 for i in self.issues if i.severity is Severity.INFO),
        }

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
