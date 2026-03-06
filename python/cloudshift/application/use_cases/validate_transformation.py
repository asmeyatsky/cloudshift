"""Use case: validate that transformations are semantically correct."""

from __future__ import annotations

import asyncio
from typing import Protocol

from cloudshift.application.dtos.validation import IssueDTO, ValidationRequest, ValidationResult
from cloudshift.domain.value_objects.types import Severity


# ---------------------------------------------------------------------------
# Port protocols
# ---------------------------------------------------------------------------

class ASTValidator(Protocol):
    """Check AST-level semantic equivalence."""

    async def check_equivalence(self, original: str, modified: str, language: str) -> list[Issue]: ...


class ResidualScanner(Protocol):
    """Scan for leftover references to the source provider."""

    async def scan(self, root: str, provider: str) -> list[Issue]: ...


class SDKSurfaceChecker(Protocol):
    """Verify target SDK API surface coverage."""

    async def check_coverage(self, root: str, target_provider: str) -> tuple[float, list[Issue]]: ...


class TestRunner(Protocol):
    """Run the project's test suite."""

    async def run(self, root: str, command: str | None = None) -> tuple[bool, str]: ...


class Issue(Protocol):
    @property
    def message(self) -> str: ...
    @property
    def severity(self) -> str: ...
    @property
    def file_path(self) -> str | None: ...
    @property
    def line(self) -> int | None: ...
    @property
    def rule(self) -> str | None: ...


class TransformationStore(Protocol):
    """Retrieve metadata about a completed transformation."""

    async def get_transform_metadata(self, plan_id: str) -> TransformMeta | None: ...


class TransformMeta(Protocol):
    @property
    def root_path(self) -> str: ...
    @property
    def source_provider(self) -> str: ...
    @property
    def target_provider(self) -> str: ...
    @property
    def modified_files(self) -> list[FileChange]: ...


class FileChange(Protocol):
    @property
    def path(self) -> str: ...
    @property
    def original_content(self) -> str: ...
    @property
    def modified_content(self) -> str: ...
    @property
    def language(self) -> str: ...


class EventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------

class ValidateTransformationUseCase:
    """Run AST equivalence, residual reference checks, SDK surface coverage, and optional tests."""

    def __init__(
        self,
        ast_validator: ASTValidator,
        residual_scanner: ResidualScanner,
        sdk_checker: SDKSurfaceChecker,
        test_runner: TestRunner | None = None,
        transform_store: TransformationStore | None = None,
        event_bus: EventPublisher | None = None,
    ) -> None:
        self._ast = ast_validator
        self._residual = residual_scanner
        self._sdk = sdk_checker
        self._test_runner = test_runner
        self._store = transform_store
        self._event_bus = event_bus

    async def execute(self, request: ValidationRequest) -> ValidationResult:
        await self._emit({"type": "ValidationStarted", "plan_id": request.plan_id})

        issues: list[IssueDTO] = []
        ast_equivalent: bool | None = None
        residual_count = 0
        sdk_coverage = 0.0
        tests_passed: bool | None = None

        meta = await self._store.get_transform_metadata(request.plan_id) if self._store else None
        if meta is None:
            return ValidationResult(
                plan_id=request.plan_id,
                passed=False,
                error=f"No transformation metadata found for plan {request.plan_id!r}.",
            )

        # Run AST equivalence and residual scan in parallel.
        parallel_tasks: list[asyncio.Task[list[IssueDTO]]] = []
        if request.check_ast_equivalence:
            parallel_tasks.append(asyncio.ensure_future(self._check_ast(meta)))
        if request.check_residual_refs:
            parallel_tasks.append(asyncio.ensure_future(self._check_residuals(meta)))

        parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

        idx = 0
        if request.check_ast_equivalence:
            result = parallel_results[idx]
            idx += 1
            if isinstance(result, Exception):
                issues.append(IssueDTO(message=f"AST check error: {result}", severity=Severity.ERROR))
            else:
                ast_issues: list[IssueDTO] = result
                issues.extend(ast_issues)
                ast_equivalent = len(ast_issues) == 0

        if request.check_residual_refs:
            result = parallel_results[idx]
            idx += 1
            if isinstance(result, Exception):
                issues.append(IssueDTO(message=f"Residual scan error: {result}", severity=Severity.ERROR))
            else:
                res_issues: list[IssueDTO] = result
                issues.extend(res_issues)
                residual_count = len(res_issues)

        # SDK surface check (sequential, depends on residuals being clean).
        if request.check_sdk_surface:
            try:
                sdk_coverage, sdk_issues = await self._sdk.check_coverage(meta.root_path, meta.target_provider)
                issues.extend(self._convert_issues(sdk_issues))
            except Exception as exc:
                issues.append(IssueDTO(message=f"SDK surface check error: {exc}", severity=Severity.ERROR))

        # Optional test runner.
        if request.run_tests and self._test_runner is not None:
            try:
                tests_passed, output = await self._test_runner.run(meta.root_path, request.test_command)
                if not tests_passed:
                    issues.append(IssueDTO(message=f"Test suite failed: {output[:500]}", severity=Severity.ERROR))
            except Exception as exc:
                issues.append(IssueDTO(message=f"Test runner error: {exc}", severity=Severity.ERROR))
                tests_passed = False

        passed = all(i.severity != Severity.ERROR and i.severity != Severity.CRITICAL for i in issues)

        await self._emit({"type": "ValidationCompleted", "plan_id": request.plan_id, "passed": passed})

        return ValidationResult(
            plan_id=request.plan_id,
            passed=passed,
            issues=issues,
            ast_equivalent=ast_equivalent,
            residual_refs_found=residual_count,
            sdk_coverage=sdk_coverage,
            tests_passed=tests_passed,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _check_ast(self, meta: TransformMeta) -> list[IssueDTO]:
        all_issues: list[IssueDTO] = []
        for fc in meta.modified_files:
            raw = await self._ast.check_equivalence(fc.original_content, fc.modified_content, fc.language)
            all_issues.extend(self._convert_issues(raw))
        return all_issues

    async def _check_residuals(self, meta: TransformMeta) -> list[IssueDTO]:
        raw = await self._residual.scan(meta.root_path, meta.source_provider)
        return self._convert_issues(raw)

    @staticmethod
    def _convert_issues(raw_issues: list[Issue]) -> list[IssueDTO]:
        result: list[IssueDTO] = []
        for r in raw_issues:
            sev = r.severity if isinstance(r.severity, Severity) else Severity[r.severity.upper()]
            result.append(
                IssueDTO(
                    message=r.message,
                    severity=sev,
                    file_path=r.file_path,
                    line=r.line,
                    rule=r.rule,
                )
            )
        return result

    async def _emit(self, event: object) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)
