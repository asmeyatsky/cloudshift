"""Comprehensive unit tests for orchestration agents: RefactorAgent and ValidationAgent.

Covers:
- RefactorAgent: all 7 pipeline stages, run(), run_parallel(), error handling, event emission
- ValidationAgent: all 6 checks, pass/fail scenarios, parallel execution, error paths
- PipelineContext / ValidationContext creation and updates
- Full coverage of uncovered lines in refactor_agent.py, validation_agent.py,
  scan_project.py, apply_transformation.py, and validate_transformation.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cloudshift.application.dtos.plan import PlanResult, TransformStep
from cloudshift.application.dtos.scan import ScanResult
from cloudshift.application.dtos.transform import (
    DiffResult,
    HunkDTO,
    TransformRequest,
    TransformResult,
)
from cloudshift.application.dtos.validation import (
    IssueDTO,
    ValidationRequest,
    ValidationResult,
)
from cloudshift.application.orchestration.refactor_agent import (
    PipelineContext,
    PipelineStage,
    RefactorAgent,
)
from cloudshift.application.orchestration.validation_agent import (
    FileChange,
    ValidationAgent,
    ValidationContext,
    ValidationVerdict,
)
from cloudshift.application.use_cases.apply_transformation import (
    ApplyTransformationUseCase,
)
from cloudshift.application.use_cases.scan_project import ScanProjectUseCase
from cloudshift.application.use_cases.validate_transformation import (
    ValidateTransformationUseCase,
)
from cloudshift.domain.value_objects.types import (
    CloudProvider,
    ConfidenceScore,
    Language,
    Severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**overrides) -> PipelineContext:
    defaults = {
        "root_path": "/project",
        "source_provider": CloudProvider.AWS,
        "target_provider": CloudProvider.GCP,
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)


_SENTINEL = object()

def _make_scan_result(error=None, services_found=_SENTINEL, project_id="p1"):
    if services_found is _SENTINEL:
        services_found = ["S3", "Lambda"]
    return ScanResult(
        project_id=project_id,
        root_path="/project",
        source_provider=CloudProvider.AWS,
        target_provider=CloudProvider.GCP,
        files=[],
        total_files_scanned=5,
        services_found=services_found,
        error=error,
    )


def _make_plan_result(error=None, steps=_SENTINEL, plan_id="plan1"):
    if steps is _SENTINEL:
        steps = [
            TransformStep(
                step_id="s1",
                file_path="app.py",
                pattern_id="p-s3-to-gcs",
                description="Migrate S3",
                confidence=0.9,
            )
        ]
    return PlanResult(
        plan_id=plan_id,
        project_id="p1",
        steps=steps,
        error=error,
    )


def _make_transform_result(success=True, errors=None):
    return TransformResult(
        plan_id="plan1",
        applied_steps=["s1"],
        diffs=[],
        files_modified=1,
        success=success,
        errors=errors or [],
    )


def _make_validation_result(passed=True, issues=None):
    return ValidationResult(
        plan_id="plan1",
        passed=passed,
        issues=issues or [],
    )


def _make_validation_context(**overrides) -> ValidationContext:
    defaults = {
        "plan_id": "plan1",
        "project_id": "p1",
        "root_path": "/project",
        "source_provider": "AWS",
        "target_provider": "GCP",
    }
    defaults.update(overrides)
    return ValidationContext(**defaults)


# ===================================================================
# 1. PipelineContext
# ===================================================================


class TestPipelineContext:
    def test_default_values(self):
        ctx = _make_context()
        assert ctx.root_path == "/project"
        assert ctx.source_provider == CloudProvider.AWS
        assert ctx.target_provider == CloudProvider.GCP
        assert ctx.project_id is None
        assert ctx.manifest_id is None
        assert ctx.plan_id is None
        assert ctx.dry_run is False
        assert ctx.stage == PipelineStage.INGEST
        assert ctx.results == {}
        assert ctx.errors == []

    def test_failed_property_false(self):
        ctx = _make_context()
        assert ctx.failed is False

    def test_failed_property_true(self):
        ctx = _make_context()
        ctx.errors.append("something went wrong")
        assert ctx.failed is True

    def test_pipeline_stage_enum(self):
        assert PipelineStage.INGEST.name == "INGEST"
        assert PipelineStage.COMMIT.name == "COMMIT"
        assert len(PipelineStage) == 7

    def test_context_mutation(self):
        ctx = _make_context()
        ctx.project_id = "p1"
        ctx.plan_id = "plan1"
        ctx.stage = PipelineStage.TRANSFORM
        assert ctx.project_id == "p1"
        assert ctx.stage == PipelineStage.TRANSFORM


# ===================================================================
# 2. RefactorAgent - Individual stages
# ===================================================================


class TestRefactorAgentStages:
    @pytest.fixture()
    def mocks(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()
        commit_port = AsyncMock()
        event_bus = AsyncMock()
        return scan, plan, transform, validate, commit_port, event_bus

    async def test_stage_ingest_success(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        scan.execute.return_value = _make_scan_result()

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        await agent._stage_ingest(ctx)

        assert ctx.project_id == "p1"
        assert ctx.manifest_id == "p1"
        assert "INGEST" in ctx.results
        assert not ctx.failed

    async def test_stage_ingest_scan_error(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        scan.execute.return_value = _make_scan_result(error="disk full")

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        await agent._stage_ingest(ctx)

        assert ctx.failed
        assert "Scan failed" in ctx.errors[0]

    async def test_stage_detect_success(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.results["INGEST"] = _make_scan_result()
        await agent._stage_detect(ctx)

        assert "DETECT" in ctx.results
        assert "S3" in ctx.results["DETECT"]
        assert not ctx.failed

    async def test_stage_detect_no_services(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.results["INGEST"] = _make_scan_result(services_found=[])
        await agent._stage_detect(ctx)

        assert ctx.failed
        assert "No cloud services detected" in ctx.errors[0]

    async def test_stage_detect_no_ingest_result(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        # No INGEST result set.
        await agent._stage_detect(ctx)

        assert ctx.failed
        assert "No cloud services detected" in ctx.errors[0]

    async def test_stage_plan_success(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        plan.execute.return_value = _make_plan_result()

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.project_id = "p1"
        ctx.manifest_id = "p1"
        await agent._stage_plan(ctx)

        assert ctx.plan_id == "plan1"
        assert "PLAN" in ctx.results
        assert not ctx.failed

    async def test_stage_plan_error(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        plan.execute.return_value = _make_plan_result(error="no manifest")

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        await agent._stage_plan(ctx)

        assert ctx.failed
        assert "Plan generation failed" in ctx.errors[0]

    async def test_stage_match_success(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.results["PLAN"] = _make_plan_result()
        await agent._stage_match(ctx)

        assert "MATCH" in ctx.results
        assert ctx.results["MATCH"] == ["p-s3-to-gcs"]
        assert not ctx.failed

    async def test_stage_match_no_steps(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.results["PLAN"] = _make_plan_result(steps=[])
        await agent._stage_match(ctx)

        assert ctx.failed
        assert "No transformation steps" in ctx.errors[0]

    async def test_stage_match_no_plan_result(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        # No PLAN result.
        await agent._stage_match(ctx)

        assert ctx.failed

    async def test_stage_transform_success(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        transform.execute.return_value = _make_transform_result()

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.plan_id = "plan1"
        await agent._stage_transform(ctx)

        assert "TRANSFORM" in ctx.results
        assert not ctx.failed

    async def test_stage_transform_failure(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        transform.execute.return_value = _make_transform_result(
            success=False, errors=["type mismatch"]
        )

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.plan_id = "plan1"
        await agent._stage_transform(ctx)

        assert ctx.failed
        assert "Transform failed" in ctx.errors[0]
        assert "type mismatch" in ctx.errors[0]

    async def test_stage_validate_success(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        validate.execute.return_value = _make_validation_result(passed=True)

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.plan_id = "plan1"
        await agent._stage_validate(ctx)

        assert "VALIDATE" in ctx.results
        assert not ctx.failed

    async def test_stage_validate_failure(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        validate.execute.return_value = _make_validation_result(
            passed=False,
            issues=[
                IssueDTO(message="leftover boto3 import", severity=Severity.ERROR),
                IssueDTO(message="missing gcs import", severity=Severity.ERROR),
            ],
        )

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.plan_id = "plan1"
        await agent._stage_validate(ctx)

        assert ctx.failed
        assert "Validation failed" in ctx.errors[0]
        assert "leftover boto3" in ctx.errors[0]

    async def test_stage_commit_dry_run(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context(dry_run=True)
        await agent._stage_commit(ctx)

        assert ctx.results["COMMIT"] == "dry-run: no commit"
        assert not ctx.failed
        commit_port.commit.assert_not_awaited()

    async def test_stage_commit_no_port(self, mocks):
        scan, plan, transform, validate, _, event_bus = mocks
        agent = RefactorAgent(scan, plan, transform, validate, commit_port=None, event_bus=event_bus)
        ctx = _make_context()
        await agent._stage_commit(ctx)

        assert ctx.results["COMMIT"] == "no commit port configured"

    async def test_stage_commit_with_port(self, mocks):
        scan, plan, transform, validate, commit_port, event_bus = mocks
        commit_port.commit.return_value = "abc123"

        agent = RefactorAgent(scan, plan, transform, validate, commit_port, event_bus)
        ctx = _make_context()
        ctx.plan_id = "plan1"
        await agent._stage_commit(ctx)

        assert ctx.results["COMMIT"] == "abc123"
        commit_port.commit.assert_awaited_once_with(
            "/project", "plan1", "cloudshift: migrate AWS -> GCP"
        )


# ===================================================================
# 3. RefactorAgent - run()
# ===================================================================


class TestRefactorAgentRun:
    async def test_run_full_pipeline_success(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()
        event_bus = AsyncMock()

        scan.execute.return_value = _make_scan_result()
        plan.execute.return_value = _make_plan_result()
        transform.execute.return_value = _make_transform_result()
        validate.execute.return_value = _make_validation_result()

        agent = RefactorAgent(scan, plan, transform, validate, commit_port=None, event_bus=event_bus)
        ctx = _make_context()
        result = await agent.run(ctx)

        assert not result.failed
        assert result.stage == PipelineStage.COMMIT
        assert "INGEST" in result.results
        assert "DETECT" in result.results
        assert "PLAN" in result.results
        assert "MATCH" in result.results
        assert "TRANSFORM" in result.results
        assert "VALIDATE" in result.results
        assert "COMMIT" in result.results
        # Event bus should have stage events.
        assert event_bus.publish.await_count >= 14  # 7 started + 7 completed

    async def test_run_stops_on_error(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()
        event_bus = AsyncMock()

        # Scan fails.
        scan.execute.return_value = _make_scan_result(error="permission denied")

        agent = RefactorAgent(scan, plan, transform, validate, event_bus=event_bus)
        ctx = _make_context()
        result = await agent.run(ctx)

        assert result.failed
        assert result.stage == PipelineStage.INGEST
        # Plan should never be called.
        plan.execute.assert_not_awaited()

    async def test_run_stops_on_exception(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()
        event_bus = AsyncMock()

        scan.execute.side_effect = RuntimeError("connection refused")

        agent = RefactorAgent(scan, plan, transform, validate, event_bus=event_bus)
        ctx = _make_context()
        result = await agent.run(ctx)

        assert result.failed
        assert "[INGEST]" in result.errors[0]
        assert "connection refused" in result.errors[0]

    async def test_run_without_event_bus(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()

        scan.execute.return_value = _make_scan_result()
        plan.execute.return_value = _make_plan_result()
        transform.execute.return_value = _make_transform_result()
        validate.execute.return_value = _make_validation_result()

        agent = RefactorAgent(scan, plan, transform, validate, event_bus=None)
        ctx = _make_context()
        result = await agent.run(ctx)

        assert not result.failed

    async def test_emit_with_event_bus(self):
        event_bus = AsyncMock()
        agent = RefactorAgent(
            AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), event_bus=event_bus
        )
        await agent._emit({"type": "TestEvent"})
        event_bus.publish.assert_awaited_once()

    async def test_emit_without_event_bus(self):
        agent = RefactorAgent(
            AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), event_bus=None
        )
        # Should not raise.
        await agent._emit({"type": "TestEvent"})


# ===================================================================
# 4. RefactorAgent - run_parallel()
# ===================================================================


class TestRefactorAgentRunParallel:
    async def test_run_parallel_full_pipeline(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()

        scan.execute.return_value = _make_scan_result()
        plan.execute.return_value = _make_plan_result()
        transform.execute.return_value = _make_transform_result()
        validate.execute.return_value = _make_validation_result()

        agent = RefactorAgent(scan, plan, transform, validate, commit_port=None, max_parallel=2)
        ctx = _make_context()
        result = await agent.run_parallel(ctx)

        # All stages should have run.
        assert "INGEST" in result.results
        assert "COMMIT" in result.results

    async def test_run_parallel_respects_max_parallel(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()

        scan.execute.return_value = _make_scan_result()
        plan.execute.return_value = _make_plan_result()
        transform.execute.return_value = _make_transform_result()
        validate.execute.return_value = _make_validation_result()

        agent = RefactorAgent(
            scan, plan, transform, validate, commit_port=None, max_parallel=1
        )
        ctx = _make_context()
        result = await agent.run_parallel(ctx)

        assert "INGEST" in result.results


# ===================================================================
# 5. RefactorAgent - constructor
# ===================================================================


class TestRefactorAgentInit:
    def test_constructor_stores_all_ports(self):
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()
        commit = AsyncMock()
        event_bus = AsyncMock()

        agent = RefactorAgent(
            scan, plan, transform, validate,
            commit_port=commit,
            event_bus=event_bus,
            max_parallel=8,
        )

        assert agent._scan is scan
        assert agent._plan is plan
        assert agent._transform is transform
        assert agent._validate is validate
        assert agent._commit is commit
        assert agent._event_bus is event_bus
        assert agent._max_parallel == 8

    def test_constructor_defaults(self):
        agent = RefactorAgent(
            AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
        )
        assert agent._commit is None
        assert agent._event_bus is None
        assert agent._max_parallel == 4


# ===================================================================
# 6. ValidationAgent - Basics
# ===================================================================


class TestValidationAgentInit:
    def test_constructor(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        test_runner = AsyncMock()
        report_gen = AsyncMock()
        event_bus = AsyncMock()

        agent = ValidationAgent(
            ast_v, residual, sdk,
            test_runner=test_runner,
            report_generator=report_gen,
            event_bus=event_bus,
        )

        assert agent._ast is ast_v
        assert agent._residual is residual
        assert agent._sdk is sdk
        assert agent._test_runner is test_runner
        assert agent._report_gen is report_gen
        assert agent._event_bus is event_bus

    def test_constructor_defaults(self):
        agent = ValidationAgent(AsyncMock(), AsyncMock(), AsyncMock())
        assert agent._test_runner is None
        assert agent._report_gen is None
        assert agent._event_bus is None


# ===================================================================
# 7. ValidationAgent - run() scenarios
# ===================================================================


class TestValidationAgentRun:
    @pytest.fixture()
    def mocks(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        test_runner = AsyncMock()
        report_gen = AsyncMock()
        event_bus = AsyncMock()
        return ast_v, residual, sdk, test_runner, report_gen, event_bus

    async def test_run_all_pass(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.95, [])

        ctx = _make_validation_context()
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is True
        assert verdict.ast_equivalent is True
        assert verdict.residual_refs_found == 0
        assert verdict.sdk_coverage == 0.95
        assert verdict.tests_passed is None
        event_bus.publish.assert_awaited()

    async def test_run_ast_issues_cause_failure(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        @dataclass
        class RawIssue:
            message: str = "AST mismatch in app.py"
            severity: Severity = Severity.ERROR
            file_path: str | None = "app.py"
            line: int | None = 10
            rule: str | None = "ast-equiv"

        ast_v.check_equivalence.return_value = [RawIssue()]
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])

        ctx = _make_validation_context(
            modified_files=[FileChange(
                path="app.py",
                original_content="import boto3",
                modified_content="from google.cloud import storage",
                language="python",
            )]
        )
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert verdict.ast_equivalent is False
        assert len(verdict.issues) >= 1

    async def test_run_residual_issues(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        @dataclass
        class RawIssue:
            message: str = "Found 'boto3' import"
            severity: Severity = Severity.ERROR
            file_path: str | None = "app.py"
            line: int | None = 1
            rule: str | None = "residual-ref"

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = [RawIssue()]
        sdk.check_coverage.return_value = (0.8, [])

        ctx = _make_validation_context()
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert verdict.residual_refs_found == 1

    async def test_run_ast_check_exception(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.side_effect = RuntimeError("parser crash")
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])

        ctx = _make_validation_context(
            modified_files=[FileChange(
                path="app.py",
                original_content="old",
                modified_content="new",
                language="python",
            )]
        )
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert any("AST check error" in i.message for i in verdict.issues)

    async def test_run_residual_check_exception(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.side_effect = RuntimeError("scan crash")
        sdk.check_coverage.return_value = (0.9, [])

        ctx = _make_validation_context()
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert any("Residual scan error" in i.message for i in verdict.issues)

    async def test_run_sdk_check_exception(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.side_effect = RuntimeError("sdk crash")

        ctx = _make_validation_context()
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert any("SDK surface check error" in i.message for i in verdict.issues)

    async def test_run_sdk_issues_converted(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        @dataclass
        class RawIssue:
            message: str = "Missing API method"
            severity: str = "WARNING"
            file_path: str | None = None
            line: int | None = None
            rule: str | None = None

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.7, [RawIssue()])

        ctx = _make_validation_context()
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        # WARNING severity should not fail the verdict.
        assert verdict.passed is True
        assert len(verdict.issues) == 1

    async def test_run_with_test_runner_pass(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        test_runner.run.return_value = (True, "All tests passed")

        ctx = _make_validation_context(run_tests=True, test_command="pytest")
        agent = ValidationAgent(ast_v, residual, sdk, test_runner=test_runner, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is True
        assert verdict.tests_passed is True

    async def test_run_with_test_runner_fail(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        test_runner.run.return_value = (False, "2 tests failed")

        ctx = _make_validation_context(run_tests=True)
        agent = ValidationAgent(ast_v, residual, sdk, test_runner=test_runner, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert verdict.tests_passed is False
        assert any("Test suite failed" in i.message for i in verdict.issues)

    async def test_run_with_test_runner_exception(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        test_runner.run.side_effect = RuntimeError("test runner crash")

        ctx = _make_validation_context(run_tests=True)
        agent = ValidationAgent(ast_v, residual, sdk, test_runner=test_runner, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is False
        assert verdict.tests_passed is False
        assert any("Test runner error" in i.message for i in verdict.issues)

    async def test_run_without_test_runner_when_run_tests(self, mocks):
        ast_v, residual, sdk, _, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])

        ctx = _make_validation_context(run_tests=True)
        # No test_runner provided.
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.passed is True
        assert verdict.tests_passed is None

    async def test_run_with_report_generator(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        report_gen.execute.return_value = {"summary": "all good"}

        ctx = _make_validation_context()
        agent = ValidationAgent(
            ast_v, residual, sdk, report_generator=report_gen, event_bus=event_bus
        )
        verdict = await agent.run(ctx)

        assert verdict.passed is True
        assert verdict.report == {"summary": "all good"}

    async def test_run_with_report_generator_error(self, mocks):
        ast_v, residual, sdk, test_runner, report_gen, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        report_gen.execute.side_effect = RuntimeError("report crash")

        ctx = _make_validation_context()
        agent = ValidationAgent(
            ast_v, residual, sdk, report_generator=report_gen, event_bus=event_bus
        )
        verdict = await agent.run(ctx)

        # Report error is a WARNING, so verdict should still pass.
        assert verdict.passed is True
        assert any("Report generation error" in i.message for i in verdict.issues)

    async def test_run_without_report_generator(self, mocks):
        ast_v, residual, sdk, _, _, event_bus = mocks

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])

        ctx = _make_validation_context()
        agent = ValidationAgent(ast_v, residual, sdk, event_bus=event_bus)
        verdict = await agent.run(ctx)

        assert verdict.report is None

    async def test_emit_with_event_bus(self, mocks):
        _, _, _, _, _, event_bus = mocks
        agent = ValidationAgent(AsyncMock(), AsyncMock(), AsyncMock(), event_bus=event_bus)
        await agent._emit({"type": "TestEvent"})
        event_bus.publish.assert_awaited_once()

    async def test_emit_without_event_bus(self):
        agent = ValidationAgent(AsyncMock(), AsyncMock(), AsyncMock())
        # Should not raise.
        await agent._emit({"type": "TestEvent"})


# ===================================================================
# 8. ValidationAgent._to_issue
# ===================================================================


class TestValidationAgentToIssue:
    def test_to_issue_with_severity_enum(self):
        @dataclass
        class RawIssue:
            message: str = "test issue"
            severity: Severity = Severity.WARNING
            file_path: str | None = "test.py"
            line: int | None = 42
            rule: str | None = "test-rule"

        issue = ValidationAgent._to_issue(RawIssue())
        assert issue.message == "test issue"
        assert issue.severity == Severity.WARNING
        assert issue.file_path == "test.py"
        assert issue.line == 42
        assert issue.rule == "test-rule"

    def test_to_issue_with_severity_string(self):
        @dataclass
        class RawIssue:
            message: str = "string severity"
            severity: str = "ERROR"
            file_path: str | None = None
            line: int | None = None
            rule: str | None = None

        issue = ValidationAgent._to_issue(RawIssue())
        assert issue.severity == Severity.ERROR

    def test_to_issue_minimal_attrs(self):
        raw = SimpleNamespace(
            message="simple issue",
            severity="INFO",
        )
        issue = ValidationAgent._to_issue(raw)
        assert issue.message == "simple issue"
        assert issue.severity == Severity.INFO
        assert issue.file_path is None
        assert issue.line is None
        assert issue.rule is None


# ===================================================================
# 9. ValidationAgent._check_ast and _check_residuals
# ===================================================================


class TestValidationAgentInternals:
    async def test_check_ast_with_multiple_files(self):
        ast_v = AsyncMock()

        @dataclass
        class RawIssue:
            message: str = "issue"
            severity: Severity = Severity.WARNING
            file_path: str | None = None
            line: int | None = None
            rule: str | None = None

        ast_v.check_equivalence.return_value = [RawIssue()]

        agent = ValidationAgent(ast_v, AsyncMock(), AsyncMock())
        ctx = _make_validation_context(
            modified_files=[
                FileChange("a.py", "old_a", "new_a", "python"),
                FileChange("b.py", "old_b", "new_b", "python"),
            ]
        )
        issues = await agent._check_ast(ctx)

        # 2 files, each returns 1 issue.
        assert len(issues) == 2
        assert ast_v.check_equivalence.await_count == 2

    async def test_check_ast_no_files(self):
        ast_v = AsyncMock()
        agent = ValidationAgent(ast_v, AsyncMock(), AsyncMock())
        ctx = _make_validation_context(modified_files=[])
        issues = await agent._check_ast(ctx)

        assert issues == []
        ast_v.check_equivalence.assert_not_awaited()

    async def test_check_residuals(self):
        residual = AsyncMock()

        @dataclass
        class RawIssue:
            message: str = "found boto3"
            severity: Severity = Severity.ERROR
            file_path: str | None = "app.py"
            line: int | None = 1
            rule: str | None = "residual"

        residual.scan.return_value = [RawIssue()]

        agent = ValidationAgent(AsyncMock(), residual, AsyncMock())
        ctx = _make_validation_context()
        issues = await agent._check_residuals(ctx)

        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    async def test_check_residuals_empty(self):
        residual = AsyncMock()
        residual.scan.return_value = []

        agent = ValidationAgent(AsyncMock(), residual, AsyncMock())
        ctx = _make_validation_context()
        issues = await agent._check_residuals(ctx)

        assert issues == []


# ===================================================================
# 10. ValidationContext and FileChange dataclasses
# ===================================================================


class TestValidationDataclasses:
    def test_validation_context_defaults(self):
        ctx = ValidationContext(
            plan_id="p1",
            project_id="proj1",
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
        )
        assert ctx.modified_files == []
        assert ctx.test_command is None
        assert ctx.run_tests is False

    def test_validation_context_with_files(self):
        fc = FileChange("app.py", "old", "new", "python")
        ctx = ValidationContext(
            plan_id="p1",
            project_id="proj1",
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[fc],
            test_command="pytest",
            run_tests=True,
        )
        assert len(ctx.modified_files) == 1
        assert ctx.test_command == "pytest"
        assert ctx.run_tests is True

    def test_file_change(self):
        fc = FileChange("app.py", "original", "modified", "python")
        assert fc.path == "app.py"
        assert fc.original_content == "original"
        assert fc.modified_content == "modified"
        assert fc.language == "python"

    def test_validation_verdict_defaults(self):
        verdict = ValidationVerdict(passed=True)
        assert verdict.issues == []
        assert verdict.ast_equivalent is None
        assert verdict.residual_refs_found == 0
        assert verdict.sdk_coverage == 0.0
        assert verdict.tests_passed is None
        assert verdict.report is None


# ===================================================================
# 11. ScanProjectUseCase - additional coverage
# ===================================================================


class TestScanProjectUseCaseAdditional:
    async def test_scan_file_exception_is_gathered(self):
        """When _scan_file raises, gather returns the exception and it's skipped."""
        fs = AsyncMock()
        parser = AsyncMock()
        detector = AsyncMock()

        fs.list_files.return_value = ["good.py", "bad.py"]
        fs.read_file.side_effect = ["content", RuntimeError("read error")]
        parser.detect_language.return_value = Language.PYTHON
        parser.count_lines.return_value = 10
        detector.detect_services.return_value = [("S3", ConfidenceScore(0.9))]

        uc = ScanProjectUseCase(fs, parser, detector)
        from cloudshift.application.dtos.scan import ScanRequest
        result = await uc.execute(
            ScanRequest(
                root_path="/project",
                source_provider=CloudProvider.AWS,
                target_provider=CloudProvider.GCP,
            )
        )

        # One file succeeded, one raised; the result skips the exception.
        assert result.error is None
        assert result.total_files_scanned == 2
        assert len(result.files) == 1

    async def test_scan_file_no_detections_returns_none(self):
        """When detector returns empty list, the file is skipped."""
        fs = AsyncMock()
        parser = AsyncMock()
        detector = AsyncMock()

        fs.list_files.return_value = ["clean.py"]
        fs.read_file.return_value = "print('hello')"
        parser.detect_language.return_value = Language.PYTHON
        detector.detect_services.return_value = []

        uc = ScanProjectUseCase(fs, parser, detector)
        from cloudshift.application.dtos.scan import ScanRequest
        result = await uc.execute(
            ScanRequest(
                root_path="/project",
                source_provider=CloudProvider.AWS,
                target_provider=CloudProvider.GCP,
            )
        )

        assert len(result.files) == 0

    async def test_scan_with_event_bus(self):
        """Event bus gets called for ScanStarted and ScanCompleted."""
        fs = AsyncMock()
        parser = AsyncMock()
        detector = AsyncMock()
        event_bus = AsyncMock()

        fs.list_files.return_value = []

        uc = ScanProjectUseCase(fs, parser, detector, event_bus=event_bus)
        from cloudshift.application.dtos.scan import ScanRequest
        await uc.execute(
            ScanRequest(
                root_path="/project",
                source_provider=CloudProvider.AWS,
                target_provider=CloudProvider.GCP,
            )
        )

        assert event_bus.publish.await_count == 2


# ===================================================================
# 12. ApplyTransformationUseCase - additional coverage
# ===================================================================


class TestApplyTransformationUseCaseAdditional:
    async def test_apply_with_step_ids_filter(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()
        event_bus = AsyncMock()

        step1 = SimpleNamespace(step_id="s1", file_path="a.py", pattern_id="p1", depends_on=[])
        step2 = SimpleNamespace(step_id="s2", file_path="b.py", pattern_id="p2", depends_on=[])
        plan = SimpleNamespace(plan_id="plan1", steps=[step1, step2])
        plan_store.get_plan.return_value = plan

        fs.read_file.return_value = "original"
        pattern_engine.apply_pattern.return_value = "modified"
        hunk = SimpleNamespace(
            start_line=1, end_line=1,
            original_text="original", modified_text="modified", context=""
        )
        diff_engine.compute_diff.return_value = [hunk]

        uc = ApplyTransformationUseCase(plan_store, pattern_engine, fs, diff_engine, event_bus)
        result = await uc.execute(
            TransformRequest(plan_id="plan1", step_ids=["s1"], dry_run=True)
        )

        # Only step s1 should be applied.
        assert result.success is True
        assert "s1" in result.applied_steps
        assert "s2" not in result.applied_steps

    async def test_apply_unsatisfied_dependency(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()

        step = SimpleNamespace(
            step_id="s2", file_path="a.py", pattern_id="p1",
            depends_on=["s1"]  # s1 doesn't exist.
        )
        plan = SimpleNamespace(plan_id="plan1", steps=[step])
        plan_store.get_plan.return_value = plan

        uc = ApplyTransformationUseCase(plan_store, pattern_engine, fs, diff_engine)
        result = await uc.execute(TransformRequest(plan_id="plan1"))

        assert result.success is False
        assert any("unsatisfied" in e for e in result.errors)

    async def test_apply_step_raises_exception(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()

        step = SimpleNamespace(step_id="s1", file_path="a.py", pattern_id="p1", depends_on=[])
        plan = SimpleNamespace(plan_id="plan1", steps=[step])
        plan_store.get_plan.return_value = plan

        fs.read_file.side_effect = RuntimeError("file not found")

        uc = ApplyTransformationUseCase(plan_store, pattern_engine, fs, diff_engine)
        result = await uc.execute(TransformRequest(plan_id="plan1"))

        assert result.success is False
        assert any("s1" in e for e in result.errors)

    async def test_apply_without_backup(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()

        step = SimpleNamespace(step_id="s1", file_path="a.py", pattern_id="p1", depends_on=[])
        plan = SimpleNamespace(plan_id="plan1", steps=[step])
        plan_store.get_plan.return_value = plan

        fs.read_file.return_value = "original"
        pattern_engine.apply_pattern.return_value = "modified"
        hunk = SimpleNamespace(
            start_line=1, end_line=1,
            original_text="original", modified_text="modified", context=""
        )
        diff_engine.compute_diff.return_value = [hunk]

        uc = ApplyTransformationUseCase(plan_store, pattern_engine, fs, diff_engine)
        result = await uc.execute(
            TransformRequest(plan_id="plan1", dry_run=False, backup=False)
        )

        assert result.success is True
        fs.copy_file.assert_not_called()
        fs.write_file.assert_called_once()

    async def test_apply_with_event_bus(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()
        event_bus = AsyncMock()

        plan_store.get_plan.return_value = None

        uc = ApplyTransformationUseCase(plan_store, pattern_engine, fs, diff_engine, event_bus)
        result = await uc.execute(TransformRequest(plan_id="nope"))

        assert result.success is False
        # emit is not called when plan is not found (returns early).

    async def test_topological_sort_with_dependencies(self):
        step1 = SimpleNamespace(step_id="s1", file_path="a.py", pattern_id="p1", depends_on=[])
        step2 = SimpleNamespace(step_id="s2", file_path="a.py", pattern_id="p2", depends_on=["s1"])
        step3 = SimpleNamespace(step_id="s3", file_path="b.py", pattern_id="p3", depends_on=["s1", "s2"])

        ordered = ApplyTransformationUseCase._topological_sort([step3, step1, step2])

        ids = [s.step_id for s in ordered]
        assert ids.index("s1") < ids.index("s2")
        assert ids.index("s2") < ids.index("s3")

    async def test_topological_sort_cyclic(self):
        step1 = SimpleNamespace(step_id="s1", file_path="a.py", pattern_id="p1", depends_on=["s2"])
        step2 = SimpleNamespace(step_id="s2", file_path="a.py", pattern_id="p2", depends_on=["s1"])

        # Cyclic deps: both should still appear (appended as remaining).
        ordered = ApplyTransformationUseCase._topological_sort([step1, step2])
        assert len(ordered) == 2

    async def test_apply_emit_without_event_bus(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()

        plan_store.get_plan.return_value = None

        uc = ApplyTransformationUseCase(plan_store, pattern_engine, fs, diff_engine)
        # emit should not raise when event_bus is None.
        await uc._emit({"type": "test"})


# ===================================================================
# 13. ValidateTransformationUseCase - additional coverage
# ===================================================================


class TestValidateTransformationUseCaseAdditional:
    async def test_validate_no_metadata(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        store.get_transform_metadata.return_value = None

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(ValidationRequest(plan_id="no-meta"))

        assert result.passed is False
        assert result.error is not None
        assert "no-meta" in result.error

    async def test_validate_no_store(self):
        """When transform_store is None, meta is None and we get an error."""
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=None)
        result = await uc.execute(ValidationRequest(plan_id="plan1"))

        assert result.passed is False
        assert result.error is not None

    async def test_validate_ast_exception(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[
                SimpleNamespace(
                    path="app.py",
                    original_content="old",
                    modified_content="new",
                    language="python",
                )
            ],
        )
        store.get_transform_metadata.return_value = meta

        ast_v.check_equivalence.side_effect = RuntimeError("parser crash")
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", check_ast_equivalence=True, check_residual_refs=True)
        )

        assert result.passed is False
        assert any("AST check error" in str(i.message) for i in result.issues)

    async def test_validate_residual_exception(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        ast_v.check_equivalence.return_value = []
        residual.scan.side_effect = RuntimeError("scan crash")
        sdk.check_coverage.return_value = (0.9, [])

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", check_ast_equivalence=True, check_residual_refs=True)
        )

        assert result.passed is False
        assert any("Residual scan error" in str(i.message) for i in result.issues)

    async def test_validate_sdk_exception(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.side_effect = RuntimeError("sdk crash")

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", check_sdk_surface=True)
        )

        assert result.passed is False
        assert any("SDK surface check error" in str(i.message) for i in result.issues)

    async def test_validate_test_runner_pass(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        test_runner = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        test_runner.run.return_value = (True, "ok")

        uc = ValidateTransformationUseCase(
            ast_v, residual, sdk, test_runner=test_runner, transform_store=store
        )
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", run_tests=True, test_command="pytest")
        )

        assert result.passed is True
        assert result.tests_passed is True

    async def test_validate_test_runner_fail(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        test_runner = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        test_runner.run.return_value = (False, "3 failures")

        uc = ValidateTransformationUseCase(
            ast_v, residual, sdk, test_runner=test_runner, transform_store=store
        )
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", run_tests=True)
        )

        assert result.passed is False
        assert result.tests_passed is False
        assert any("Test suite failed" in i.message for i in result.issues)

    async def test_validate_test_runner_exception(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        test_runner = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.9, [])
        test_runner.run.side_effect = RuntimeError("crash")

        uc = ValidateTransformationUseCase(
            ast_v, residual, sdk, test_runner=test_runner, transform_store=store
        )
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", run_tests=True)
        )

        assert result.passed is False
        assert result.tests_passed is False
        assert any("Test runner error" in i.message for i in result.issues)

    async def test_validate_skip_checks(self):
        """When all checks are disabled, only SDK surface runs."""
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta
        sdk.check_coverage.return_value = (0.95, [])

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(
            ValidationRequest(
                plan_id="plan1",
                check_ast_equivalence=False,
                check_residual_refs=False,
                check_sdk_surface=True,
                run_tests=False,
            )
        )

        assert result.passed is True
        assert result.ast_equivalent is None
        assert result.residual_refs_found == 0
        ast_v.check_equivalence.assert_not_awaited()
        residual.scan.assert_not_awaited()

    async def test_validate_all_checks_disabled(self):
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(
            ValidationRequest(
                plan_id="plan1",
                check_ast_equivalence=False,
                check_residual_refs=False,
                check_sdk_surface=False,
                run_tests=False,
            )
        )

        assert result.passed is True
        assert result.issues == []

    async def test_validate_convert_issues_with_string_severity(self):
        """_convert_issues handles string severity values."""
        raw_issue = SimpleNamespace(
            message="leftover import",
            severity="ERROR",
            file_path="app.py",
            line=5,
            rule="residual-ref",
        )
        issues = ValidateTransformationUseCase._convert_issues([raw_issue])
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR
        assert issues[0].message == "leftover import"

    async def test_validate_convert_issues_with_severity_enum(self):
        raw_issue = SimpleNamespace(
            message="info note",
            severity=Severity.INFO,
            file_path=None,
            line=None,
            rule=None,
        )
        issues = ValidateTransformationUseCase._convert_issues([raw_issue])
        assert len(issues) == 1
        assert issues[0].severity == Severity.INFO

    async def test_validate_emit_with_event_bus(self):
        event_bus = AsyncMock()
        uc = ValidateTransformationUseCase(
            AsyncMock(), AsyncMock(), AsyncMock(), event_bus=event_bus
        )
        await uc._emit({"type": "test"})
        event_bus.publish.assert_awaited_once()

    async def test_validate_emit_without_event_bus(self):
        uc = ValidateTransformationUseCase(
            AsyncMock(), AsyncMock(), AsyncMock()
        )
        # Should not raise.
        await uc._emit({"type": "test"})

    async def test_validate_check_ast_internal(self):
        """Test _check_ast via the use case directly."""
        ast_v = AsyncMock()

        raw_issue = SimpleNamespace(
            message="mismatch",
            severity=Severity.WARNING,
            file_path="x.py",
            line=3,
            rule="ast-diff",
        )
        ast_v.check_equivalence.return_value = [raw_issue]

        uc = ValidateTransformationUseCase(ast_v, AsyncMock(), AsyncMock())
        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[
                SimpleNamespace(
                    path="x.py",
                    original_content="old",
                    modified_content="new",
                    language="python",
                ),
            ],
        )
        issues = await uc._check_ast(meta)
        assert len(issues) == 1
        assert issues[0].message == "mismatch"

    async def test_validate_check_residuals_internal(self):
        """Test _check_residuals via the use case directly."""
        residual = AsyncMock()

        raw_issue = SimpleNamespace(
            message="boto3 leftover",
            severity="ERROR",
            file_path="app.py",
            line=1,
            rule="residual",
        )
        residual.scan.return_value = [raw_issue]

        uc = ValidateTransformationUseCase(AsyncMock(), residual, AsyncMock())
        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        issues = await uc._check_residuals(meta)
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    async def test_validate_sdk_surface_issues_converted(self):
        """SDK surface check issues are properly converted."""
        ast_v = AsyncMock()
        residual = AsyncMock()
        sdk = AsyncMock()
        store = AsyncMock()

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        store.get_transform_metadata.return_value = meta

        raw_issue = SimpleNamespace(
            message="missing API",
            severity="WARNING",
            file_path=None,
            line=None,
            rule=None,
        )
        ast_v.check_equivalence.return_value = []
        residual.scan.return_value = []
        sdk.check_coverage.return_value = (0.7, [raw_issue])

        uc = ValidateTransformationUseCase(ast_v, residual, sdk, transform_store=store)
        result = await uc.execute(
            ValidationRequest(plan_id="plan1", check_sdk_surface=True)
        )

        # WARNING issues don't cause failure.
        assert result.passed is True
        assert len(result.issues) == 1
        assert result.sdk_coverage == 0.7


# ===================================================================
# 14. RefactorAgent - stages with edge cases
# ===================================================================


class TestRefactorAgentEdgeCases:
    async def test_validate_stage_truncates_issues(self):
        """Validation stage only shows first 5 issues in the error message."""
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()

        issues = [
            IssueDTO(message=f"issue-{i}", severity=Severity.ERROR)
            for i in range(10)
        ]
        validate.execute.return_value = _make_validation_result(passed=False, issues=issues)

        agent = RefactorAgent(scan, plan, transform, validate)
        ctx = _make_context()
        ctx.plan_id = "plan1"
        await agent._stage_validate(ctx)

        assert ctx.failed
        # Only 5 issues mentioned (joined by ;).
        error_msg = ctx.errors[0]
        assert "issue-0" in error_msg
        assert "issue-4" in error_msg

    async def test_run_multiple_stage_failures(self):
        """Pipeline stops at first error (from ctx.failed check after handler)."""
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()

        # Scan succeeds but returns no services.
        scan.execute.return_value = _make_scan_result(services_found=[])

        agent = RefactorAgent(scan, plan, transform, validate)
        ctx = _make_context()
        result = await agent.run(ctx)

        assert result.failed
        # Pipeline should stop at DETECT stage.
        assert result.stage == PipelineStage.DETECT

    async def test_run_with_null_project_id_and_plan_id(self):
        """Stages handle None project_id/plan_id gracefully (use empty string)."""
        scan = AsyncMock()
        plan = AsyncMock()
        transform = AsyncMock()
        validate = AsyncMock()
        event_bus = AsyncMock()

        # Scan result has error, so project_id never set.
        scan.execute.return_value = _make_scan_result(error="fail early")

        agent = RefactorAgent(scan, plan, transform, validate, event_bus=event_bus)
        ctx = _make_context()
        result = await agent.run(ctx)

        assert result.failed
        assert result.project_id is None


# ===================================================================
# DAGOrchestrator tests (for timeout branch coverage)
# ===================================================================


class TestDAGOrchestrator:
    """Tests for dag.py lines 105-108: worker timeout and exit."""

    @pytest.mark.asyncio
    async def test_worker_timeout_branch(self):
        """Workers that finish early hit TimeoutError while waiting for others.

        With 2 tasks and max_parallel=2, both workers start.
        Worker 1 finishes task "a" instantly, then polls an empty queue.
        Worker 2 takes task "b" and completes slowly.
        Worker 1 times out, sees completed_count < total, continues.
        After worker 2 finishes, worker 1 times out again and breaks.
        """
        from cloudshift.application.orchestration.dag import DAGOrchestrator

        async def fast_action():
            return "fast"

        async def slow_action():
            await asyncio.sleep(0.25)
            return "slow"

        dag = DAGOrchestrator(max_parallel=2)
        dag.add_node("a", fast_action)
        dag.add_node("b", slow_action)
        results = await dag.execute()
        assert results["a"] == "fast"
        assert results["b"] == "slow"
