"""ValidationAgent: 6-check validation pipeline with parallel execution where possible.

Checks:
    1. AST equivalence      (parallel with #2)
    2. Residual ref scan    (parallel with #1)
    3. SDK surface coverage (sequential)
    4. Optional test runner  (sequential)
    5. Report generation     (sequential, final)
    6. Summary verdict       (always)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

from cloudshift.application.dtos.validation import IssueDTO, ValidationResult
from cloudshift.domain.value_objects.types import Severity


# ---------------------------------------------------------------------------
# Port protocols
# ---------------------------------------------------------------------------

class ASTValidator(Protocol):
    async def check_equivalence(self, original: str, modified: str, language: str) -> list[Any]: ...


class ResidualScanner(Protocol):
    async def scan(self, root: str, provider: str) -> list[Any]: ...


class SDKSurfaceChecker(Protocol):
    async def check_coverage(self, root: str, target_provider: str) -> tuple[float, list[Any]]: ...


class TestRunner(Protocol):
    async def run(self, root: str, command: str | None = None) -> tuple[bool, str]: ...


class ReportGenerator(Protocol):
    async def execute(self, project_id: str) -> Any: ...


class EventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class FileChange:
    path: str
    original_content: str
    modified_content: str
    language: str


@dataclass
class ValidationContext:
    """Input context for the validation agent."""

    plan_id: str
    project_id: str
    root_path: str
    source_provider: str
    target_provider: str
    modified_files: list[FileChange] = field(default_factory=list)
    test_command: str | None = None
    run_tests: bool = False


@dataclass
class ValidationVerdict:
    """Final output of the validation agent."""

    passed: bool
    issues: list[IssueDTO] = field(default_factory=list)
    ast_equivalent: bool | None = None
    residual_refs_found: int = 0
    sdk_coverage: float = 0.0
    tests_passed: bool | None = None
    report: Any = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ValidationAgent:
    """Coordinate 6 validation checks, running AST equivalence and residual scan in parallel."""

    def __init__(
        self,
        ast_validator: ASTValidator,
        residual_scanner: ResidualScanner,
        sdk_checker: SDKSurfaceChecker,
        test_runner: TestRunner | None = None,
        report_generator: ReportGenerator | None = None,
        event_bus: EventPublisher | None = None,
    ) -> None:
        self._ast = ast_validator
        self._residual = residual_scanner
        self._sdk = sdk_checker
        self._test_runner = test_runner
        self._report_gen = report_generator
        self._event_bus = event_bus

    async def run(self, ctx: ValidationContext) -> ValidationVerdict:
        """Execute the full 6-check validation pipeline."""
        await self._emit({"type": "ValidationAgentStarted", "plan_id": ctx.plan_id})

        issues: list[IssueDTO] = []
        ast_equivalent: bool | None = None
        residual_count = 0
        sdk_coverage = 0.0
        tests_passed: bool | None = None
        report: Any = None

        # ---- Checks 1 & 2: AST equivalence + residual scan (parallel) ----
        ast_task = asyncio.create_task(self._check_ast(ctx))
        residual_task = asyncio.create_task(self._check_residuals(ctx))
        ast_result, residual_result = await asyncio.gather(ast_task, residual_task, return_exceptions=True)

        if isinstance(ast_result, Exception):
            issues.append(IssueDTO(message=f"AST check error: {ast_result}", severity=Severity.ERROR))
        else:
            ast_issues: list[IssueDTO] = ast_result
            issues.extend(ast_issues)
            ast_equivalent = len(ast_issues) == 0

        if isinstance(residual_result, Exception):
            issues.append(IssueDTO(message=f"Residual scan error: {residual_result}", severity=Severity.ERROR))
        else:
            residual_issues: list[IssueDTO] = residual_result
            issues.extend(residual_issues)
            residual_count = len(residual_issues)

        # ---- Check 3: SDK surface coverage ----
        try:
            sdk_coverage, sdk_raw = await self._sdk.check_coverage(ctx.root_path, ctx.target_provider)
            for raw in sdk_raw:
                issues.append(self._to_issue(raw))
        except Exception as exc:
            issues.append(IssueDTO(message=f"SDK surface check error: {exc}", severity=Severity.ERROR))

        # ---- Check 4: optional test runner ----
        if ctx.run_tests and self._test_runner is not None:
            try:
                tests_passed, output = await self._test_runner.run(ctx.root_path, ctx.test_command)
                if not tests_passed:
                    issues.append(
                        IssueDTO(message=f"Test suite failed: {output[:500]}", severity=Severity.ERROR)
                    )
            except Exception as exc:
                issues.append(IssueDTO(message=f"Test runner error: {exc}", severity=Severity.ERROR))
                tests_passed = False

        # ---- Check 5: report generation ----
        if self._report_gen is not None:
            try:
                report = await self._report_gen.execute(ctx.project_id)
            except Exception as exc:
                issues.append(IssueDTO(message=f"Report generation error: {exc}", severity=Severity.WARNING))

        # ---- Check 6: summary verdict ----
        passed = all(
            i.severity not in (Severity.ERROR, Severity.CRITICAL)
            for i in issues
        )

        await self._emit({
            "type": "ValidationAgentCompleted",
            "plan_id": ctx.plan_id,
            "passed": passed,
            "issue_count": len(issues),
        })

        return ValidationVerdict(
            passed=passed,
            issues=issues,
            ast_equivalent=ast_equivalent,
            residual_refs_found=residual_count,
            sdk_coverage=sdk_coverage,
            tests_passed=tests_passed,
            report=report,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _check_ast(self, ctx: ValidationContext) -> list[IssueDTO]:
        result: list[IssueDTO] = []
        for fc in ctx.modified_files:
            raw_issues = await self._ast.check_equivalence(fc.original_content, fc.modified_content, fc.language)
            for raw in raw_issues:
                result.append(self._to_issue(raw))
        return result

    async def _check_residuals(self, ctx: ValidationContext) -> list[IssueDTO]:
        raw_issues = await self._residual.scan(ctx.root_path, ctx.source_provider)
        return [self._to_issue(r) for r in raw_issues]

    @staticmethod
    def _to_issue(raw: Any) -> IssueDTO:
        """Convert a raw issue object (duck-typed) into an IssueDTO."""
        severity = raw.severity if isinstance(raw.severity, Severity) else Severity[str(raw.severity).upper()]
        return IssueDTO(
            message=getattr(raw, "message", str(raw)),
            severity=severity,
            file_path=getattr(raw, "file_path", None),
            line=getattr(raw, "line", None),
            rule=getattr(raw, "rule", None),
        )

    async def _emit(self, event: object) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)
