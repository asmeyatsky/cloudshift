"""Domain service for evaluating validation reports."""

from __future__ import annotations

from cloudshift.domain.entities.validation_report import ValidationReport
from cloudshift.domain.value_objects.types import ConfidenceScore, Severity


class ValidationEvaluator:
    """Evaluates validation reports and derives an overall quality score."""

    def __init__(
        self,
        *,
        max_errors: int = 0,
        max_warnings: int = 10,
    ) -> None:
        self._max_errors = max_errors
        self._max_warnings = max_warnings

    def is_acceptable(self, report: ValidationReport) -> bool:
        """Return *True* when the report meets the configured thresholds."""
        return (
            report.error_count <= self._max_errors
            and report.warning_count <= self._max_warnings
        )

    @staticmethod
    def quality_score(report: ValidationReport) -> ConfidenceScore:
        """Derive a 0-1 quality score from a validation report.

        Each error deducts 0.2 and each warning deducts 0.05, floored at 0.
        """
        penalty = report.error_count * 0.2 + report.warning_count * 0.05
        return ConfidenceScore(max(0.0, 1.0 - penalty))

    @staticmethod
    def critical_issues(report: ValidationReport) -> list[str]:
        """Return human-readable descriptions of critical/error issues."""
        return [
            issue.message
            for issue in report.issues
            if issue.severity in (Severity.ERROR, Severity.CRITICAL)
        ]
