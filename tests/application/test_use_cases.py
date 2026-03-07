"""Unit tests for the CloudShift application layer.

Covers:
- Each use case with mocked dependencies
- DTO creation and serialization
- DAG orchestrator with simple task graphs
- Event dispatcher publish/subscribe
- Edge cases (empty results, not-found scenarios)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from cloudshift.application.dtos.pattern import PatternDTO
from cloudshift.application.dtos.plan import PlanRequest, PlanResult, TransformStep
from cloudshift.application.dtos.report import FileSummary, ReportDTO
from cloudshift.application.dtos.scan import FileEntry, ScanRequest, ScanResult
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
from cloudshift.application.orchestration.dag import (
    DAGExecutionError,
    DAGOrchestrator,
    NodeStatus,
)
from cloudshift.application.services.event_dispatcher import EventDispatcher
from cloudshift.application.use_cases.apply_transformation import (
    ApplyTransformationUseCase,
)
from cloudshift.application.use_cases.generate_plan import GeneratePlanUseCase
from cloudshift.application.use_cases.generate_report import GenerateReportUseCase
from cloudshift.application.use_cases.manage_patterns import ManagePatternsUseCase
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


def _make_scan_request(**overrides) -> ScanRequest:
    defaults = {
        "root_path": "/project",
        "source_provider": CloudProvider.AWS,
        "target_provider": CloudProvider.GCP,
    }
    defaults.update(overrides)
    return ScanRequest(**defaults)


# ===================================================================
# 1. ScanProjectUseCase
# ===================================================================


class TestScanProjectUseCase:
    """Tests for scanning a project directory."""

    @pytest.fixture()
    def mocks(self):
        fs = AsyncMock()
        parser = AsyncMock()
        detector = AsyncMock()
        event_bus = AsyncMock()
        return fs, parser, detector, event_bus

    @pytest.mark.asyncio
    async def test_scan_discovers_files_and_services(self, mocks):
        fs, parser, detector, event_bus = mocks

        fs.list_files.return_value = ["app.py", "infra.py"]
        fs.read_file.side_effect = ["import boto3", "import s3"]
        parser.detect_language.return_value = Language.PYTHON
        parser.count_lines.return_value = 10
        detector.detect_services.return_value = [
            ("S3", ConfidenceScore(0.95)),
        ]

        uc = ScanProjectUseCase(fs, parser, detector, event_bus)
        result = await uc.execute(_make_scan_request())

        assert result.error is None
        assert result.total_files_scanned == 2
        assert len(result.files) == 2
        assert "S3" in result.services_found

    @pytest.mark.asyncio
    async def test_scan_returns_error_when_listing_fails(self, mocks):
        fs, parser, detector, event_bus = mocks
        fs.list_files.side_effect = OSError("permission denied")

        uc = ScanProjectUseCase(fs, parser, detector, event_bus)
        result = await uc.execute(_make_scan_request())

        assert result.error is not None
        assert "permission denied" in result.error

    @pytest.mark.asyncio
    async def test_scan_skips_unrecognised_language(self, mocks):
        fs, parser, detector, event_bus = mocks
        fs.list_files.return_value = ["readme.txt"]
        fs.read_file.return_value = "hello"
        parser.detect_language.return_value = None

        uc = ScanProjectUseCase(fs, parser, detector, event_bus)
        result = await uc.execute(_make_scan_request())

        assert len(result.files) == 0
        assert result.total_files_scanned == 1

    @pytest.mark.asyncio
    async def test_scan_filters_by_language(self, mocks):
        fs, parser, detector, event_bus = mocks
        fs.list_files.return_value = ["app.py"]
        fs.read_file.return_value = "import boto3"
        parser.detect_language.return_value = Language.PYTHON
        detector.detect_services.return_value = [("S3", ConfidenceScore(0.9))]
        parser.count_lines.return_value = 5

        # Request only HCL -- Python file should be filtered out.
        uc = ScanProjectUseCase(fs, parser, detector, event_bus)
        result = await uc.execute(
            _make_scan_request(languages=[Language.HCL])
        )

        assert len(result.files) == 0

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self, mocks):
        fs, parser, detector, event_bus = mocks
        fs.list_files.return_value = []

        uc = ScanProjectUseCase(fs, parser, detector, event_bus)
        result = await uc.execute(_make_scan_request())

        assert result.error is None
        assert result.total_files_scanned == 0
        assert len(result.files) == 0
        assert result.services_found == []

    @pytest.mark.asyncio
    async def test_scan_without_event_bus(self, mocks):
        """Event bus is optional; the use case must not crash when it is None."""
        fs, parser, detector, _ = mocks
        fs.list_files.return_value = []

        uc = ScanProjectUseCase(fs, parser, detector, event_bus=None)
        result = await uc.execute(_make_scan_request())

        assert result.error is None


# ===================================================================
# 2. GeneratePlanUseCase
# ===================================================================


class TestGeneratePlanUseCase:
    """Tests for generating a transformation plan."""

    @pytest.fixture()
    def mocks(self):
        pattern_engine = AsyncMock()
        manifest_store = AsyncMock()
        event_bus = AsyncMock()
        return pattern_engine, manifest_store, event_bus

    @pytest.mark.asyncio
    async def test_plan_manifest_not_found(self, mocks):
        pe, ms, eb = mocks
        ms.get_manifest.return_value = None

        uc = GeneratePlanUseCase(pe, ms, eb)
        result = await uc.execute(
            PlanRequest(project_id="p1", manifest_id="missing")
        )

        assert result.error is not None
        assert "missing" in result.error

    @pytest.mark.asyncio
    async def test_plan_generates_steps_from_manifest(self, mocks):
        pe, ms, eb = mocks

        entry = SimpleNamespace(file_path="app.py", services=["S3"])
        manifest = SimpleNamespace(
            source_provider="AWS", target_provider="GCP", entries=[entry]
        )
        ms.get_manifest.return_value = manifest

        match = SimpleNamespace(
            pattern_id="p-s3-to-gcs",
            description="S3 -> GCS migration",
            confidence=ConfidenceScore(0.9),
        )
        pe.match_patterns.return_value = [match]

        uc = GeneratePlanUseCase(pe, ms, eb)
        result = await uc.execute(
            PlanRequest(project_id="p1", manifest_id="m1", strategy="balanced")
        )

        assert result.error is None
        assert len(result.steps) == 1
        assert result.steps[0].pattern_id == "p-s3-to-gcs"
        assert result.estimated_files_changed == 1

    @pytest.mark.asyncio
    async def test_plan_conservative_filters_low_confidence(self, mocks):
        pe, ms, eb = mocks

        entry = SimpleNamespace(file_path="app.py", services=["S3"])
        manifest = SimpleNamespace(
            source_provider="AWS", target_provider="GCP", entries=[entry]
        )
        ms.get_manifest.return_value = manifest

        match = SimpleNamespace(
            pattern_id="p-low",
            description="Low-confidence match",
            confidence=ConfidenceScore(0.3),
        )
        pe.match_patterns.return_value = [match]

        uc = GeneratePlanUseCase(pe, ms, eb)
        result = await uc.execute(
            PlanRequest(project_id="p1", manifest_id="m1", strategy="conservative")
        )

        # Conservative threshold is 0.8; confidence 0.3 should be dropped.
        assert len(result.steps) == 0
        assert any("dropped" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_plan_no_patterns_warns(self, mocks):
        pe, ms, eb = mocks

        entry = SimpleNamespace(file_path="app.py", services=["DynamoDB"])
        manifest = SimpleNamespace(
            source_provider="AWS", target_provider="GCP", entries=[entry]
        )
        ms.get_manifest.return_value = manifest
        pe.match_patterns.return_value = []

        uc = GeneratePlanUseCase(pe, ms, eb)
        result = await uc.execute(
            PlanRequest(project_id="p1", manifest_id="m1")
        )

        assert any("No patterns matched" in w for w in result.warnings)


# ===================================================================
# 3. ApplyTransformationUseCase
# ===================================================================


class TestApplyTransformationUseCase:
    """Tests for applying pattern-based transformations."""

    @pytest.fixture()
    def mocks(self):
        plan_store = AsyncMock()
        pattern_engine = AsyncMock()
        fs = AsyncMock()
        diff_engine = AsyncMock()
        event_bus = AsyncMock()
        return plan_store, pattern_engine, fs, diff_engine, event_bus

    @pytest.mark.asyncio
    async def test_plan_not_found(self, mocks):
        ps, pe, fs, de, eb = mocks
        ps.get_plan.return_value = None

        uc = ApplyTransformationUseCase(ps, pe, fs, de, eb)
        result = await uc.execute(TransformRequest(plan_id="nope"))

        assert result.success is False
        assert any("not found" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_apply_dry_run_does_not_write(self, mocks):
        ps, pe, fs, de, eb = mocks

        step = SimpleNamespace(
            step_id="s1", file_path="app.py", pattern_id="p1", depends_on=[]
        )
        plan = SimpleNamespace(plan_id="plan1", steps=[step])
        ps.get_plan.return_value = plan

        fs.read_file.return_value = "original code"
        pe.apply_pattern.return_value = "modified code"

        hunk = SimpleNamespace(
            start_line=1,
            end_line=3,
            original_text="original code",
            modified_text="modified code",
            context="",
        )
        de.compute_diff.return_value = [hunk]

        uc = ApplyTransformationUseCase(ps, pe, fs, de, eb)
        result = await uc.execute(
            TransformRequest(plan_id="plan1", dry_run=True, backup=False)
        )

        assert result.success is True
        assert len(result.diffs) == 1
        fs.write_file.assert_not_called()
        fs.copy_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_with_backup(self, mocks):
        ps, pe, fs, de, eb = mocks

        step = SimpleNamespace(
            step_id="s1", file_path="app.py", pattern_id="p1", depends_on=[]
        )
        plan = SimpleNamespace(plan_id="plan1", steps=[step])
        ps.get_plan.return_value = plan

        fs.read_file.return_value = "original"
        pe.apply_pattern.return_value = "modified"

        hunk = SimpleNamespace(
            start_line=1,
            end_line=1,
            original_text="original",
            modified_text="modified",
            context="",
        )
        de.compute_diff.return_value = [hunk]

        uc = ApplyTransformationUseCase(ps, pe, fs, de, eb)
        result = await uc.execute(
            TransformRequest(plan_id="plan1", dry_run=False, backup=True)
        )

        assert result.success is True
        fs.copy_file.assert_called_once_with("app.py", "app.py.bak")
        fs.write_file.assert_called_once_with("app.py", "modified")

    @pytest.mark.asyncio
    async def test_apply_no_change_produces_no_diff(self, mocks):
        ps, pe, fs, de, eb = mocks

        step = SimpleNamespace(
            step_id="s1", file_path="app.py", pattern_id="p1", depends_on=[]
        )
        plan = SimpleNamespace(plan_id="plan1", steps=[step])
        ps.get_plan.return_value = plan

        fs.read_file.return_value = "unchanged"
        pe.apply_pattern.return_value = "unchanged"  # Same content.

        uc = ApplyTransformationUseCase(ps, pe, fs, de, eb)
        result = await uc.execute(TransformRequest(plan_id="plan1"))

        assert result.success is True
        assert len(result.diffs) == 0


# ===================================================================
# 4. ValidateTransformationUseCase
# ===================================================================


class TestValidateTransformationUseCase:
    """Tests for the validation use case."""

    @pytest.fixture()
    def mocks(self):
        ast_validator = AsyncMock()
        residual_scanner = AsyncMock()
        sdk_checker = AsyncMock()
        test_runner = AsyncMock()
        transform_store = AsyncMock()
        event_bus = AsyncMock()
        return ast_validator, residual_scanner, sdk_checker, test_runner, transform_store, event_bus

    @pytest.mark.asyncio
    async def test_validation_no_metadata(self, mocks):
        ast_v, rs, sdk, tr, ts, eb = mocks
        ts.get_transform_metadata.return_value = None

        uc = ValidateTransformationUseCase(ast_v, rs, sdk, tr, ts, eb)
        result = await uc.execute(ValidationRequest(plan_id="no-meta"))

        assert result.passed is False
        assert result.error is not None
        assert "no-meta" in result.error

    @pytest.mark.asyncio
    async def test_validation_passes_clean(self, mocks):
        ast_v, rs, sdk, tr, ts, eb = mocks

        file_change = SimpleNamespace(
            path="app.py",
            original_content="import boto3",
            modified_content="from google.cloud import storage",
            language="python",
        )
        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[file_change],
        )
        ts.get_transform_metadata.return_value = meta
        ast_v.check_equivalence.return_value = []
        rs.scan.return_value = []
        sdk.check_coverage.return_value = (0.95, [])

        uc = ValidateTransformationUseCase(ast_v, rs, sdk, tr, ts, eb)
        result = await uc.execute(
            ValidationRequest(
                plan_id="plan1",
                check_ast_equivalence=True,
                check_residual_refs=True,
                check_sdk_surface=True,
                run_tests=False,
            )
        )

        assert result.passed is True
        assert result.ast_equivalent is True
        assert result.residual_refs_found == 0

    @pytest.mark.asyncio
    async def test_validation_fails_on_residual_refs(self, mocks):
        ast_v, rs, sdk, tr, ts, eb = mocks

        meta = SimpleNamespace(
            root_path="/project",
            source_provider="AWS",
            target_provider="GCP",
            modified_files=[],
        )
        ts.get_transform_metadata.return_value = meta
        ast_v.check_equivalence.return_value = []

        residual_issue = SimpleNamespace(
            message="Found 'boto3' import",
            severity=Severity.ERROR,
            file_path="app.py",
            line=1,
            rule="residual-import",
        )
        rs.scan.return_value = [residual_issue]
        sdk.check_coverage.return_value = (0.8, [])

        uc = ValidateTransformationUseCase(ast_v, rs, sdk, tr, ts, eb)
        result = await uc.execute(
            ValidationRequest(
                plan_id="plan1",
                check_ast_equivalence=True,
                check_residual_refs=True,
                check_sdk_surface=True,
            )
        )

        assert result.passed is False
        assert result.residual_refs_found == 1


# ===================================================================
# 5. ManagePatternsUseCase
# ===================================================================


class TestManagePatternsUseCase:
    """Tests for pattern CRUD operations."""

    @pytest.fixture()
    def store(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_list_patterns(self, store):
        store.list_all.return_value = [
            {
                "id": "p1",
                "name": "S3->GCS",
                "description": "Migrate S3 to GCS",
                "source_provider": CloudProvider.AWS,
                "target_provider": CloudProvider.GCP,
                "language": Language.PYTHON,
            }
        ]

        uc = ManagePatternsUseCase(store)
        result = await uc.list_patterns()

        assert len(result) == 1
        assert result[0].pattern_id == "p1"
        assert result[0].name == "S3->GCS"

    @pytest.mark.asyncio
    async def test_get_pattern_not_found(self, store):
        store.get_by_id.return_value = None

        uc = ManagePatternsUseCase(store)
        result = await uc.get_pattern("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_add_pattern(self, store):
        store.add.return_value = "new-id"

        dto = PatternDTO(
            pattern_id="",
            name="Lambda->CloudFunc",
            description="Migrate Lambda to Cloud Functions",
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
            language=Language.PYTHON,
        )

        uc = ManagePatternsUseCase(store)
        result = await uc.add_pattern(dto)

        assert result == "new-id"
        store.add.assert_called_once_with(dto)

    @pytest.mark.asyncio
    async def test_delete_pattern(self, store):
        store.delete.return_value = True

        uc = ManagePatternsUseCase(store)
        result = await uc.delete_pattern("p1")

        assert result is True

    @pytest.mark.asyncio
    async def test_search_patterns_with_query(self, store):
        store.list_all.return_value = [
            {
                "id": "p1",
                "name": "S3->GCS",
                "description": "Migrate S3",
                "source_provider": CloudProvider.AWS,
                "target_provider": CloudProvider.GCP,
                "language": Language.PYTHON,
            },
            {
                "id": "p2",
                "name": "DynamoDB->Firestore",
                "description": "Migrate DynamoDB",
                "source_provider": CloudProvider.AWS,
                "target_provider": CloudProvider.GCP,
                "language": Language.PYTHON,
            },
        ]

        uc = ManagePatternsUseCase(store)
        result = await uc.search_patterns(query="dynamo")

        assert len(result) == 1
        assert result[0].pattern_id == "p2"

    @pytest.mark.asyncio
    async def test_search_patterns_empty_query_returns_all(self, store):
        store.list_all.return_value = [
            {
                "id": f"p{i}",
                "name": f"Pattern {i}",
                "description": "",
                "source_provider": CloudProvider.AWS,
                "target_provider": CloudProvider.GCP,
                "language": Language.PYTHON,
            }
            for i in range(3)
        ]

        uc = ManagePatternsUseCase(store)
        result = await uc.search_patterns(query="", top_k=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_call_with_async_store_method(self):
        """Cover line 34: awaiting an async method on the store."""
        store = AsyncMock()
        store.list_all.return_value = []
        uc = ManagePatternsUseCase(store)
        result = await uc.list_patterns()
        assert result == []

    @pytest.mark.asyncio
    async def test_search_patterns_with_object_patterns(self):
        """Cover line 59: getattr branch for non-dict patterns."""
        obj = SimpleNamespace(
            id="p1", pattern_id="p1", name="S3->GCS",
            description="Migrate S3", source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP, language=Language.PYTHON,
            source_snippet="", target_snippet="", tags=[], confidence=0.9,
            base_confidence=0.9, version="1.0",
        )
        store = MagicMock()
        store.list_all.return_value = [obj]
        uc = ManagePatternsUseCase(store)
        result = await uc.search_patterns(query="s3")
        assert len(result) == 1
        assert result[0].name == "S3->GCS"


# ===================================================================
# 6. GenerateReportUseCase
# ===================================================================


class TestGenerateReportUseCase:
    """Tests for audit report generation."""

    @pytest.fixture()
    def stores(self):
        project_store = AsyncMock()
        scan_store = AsyncMock()
        transform_store = AsyncMock()
        validation_store = AsyncMock()
        return project_store, scan_store, transform_store, validation_store

    @pytest.mark.asyncio
    async def test_report_project_not_found(self, stores):
        ps, ss, ts, vs = stores
        ps.get_project.return_value = None

        uc = GenerateReportUseCase(ps, ss, ts, vs)
        result = await uc.execute("unknown")

        assert "not found" in result.notes

    @pytest.mark.asyncio
    async def test_report_full_pipeline(self, stores):
        ps, ss, ts, vs = stores

        project = SimpleNamespace(
            project_id="p1",
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
        )
        ps.get_project.return_value = project

        scan_entry = SimpleNamespace(path="app.py", services=["S3"], confidence=0.9)
        scan_summary = SimpleNamespace(total_files=5, entries=[scan_entry])
        ss.get_scan_summary.return_value = scan_summary

        transform_summary = SimpleNamespace(
            files_modified=1, patterns_applied=1, modified_paths=["app.py"]
        )
        ts.get_transform_summary.return_value = transform_summary

        validation_summary = SimpleNamespace(
            passed=True, issue_count=0, warnings=[]
        )
        vs.get_validation_summary.return_value = validation_summary

        uc = GenerateReportUseCase(ps, ss, ts, vs)
        result = await uc.execute("p1")

        assert result.total_files == 5
        assert result.files_changed == 1
        assert result.validation_passed is True
        assert result.overall_confidence == 0.9
        assert len(result.file_summaries) == 1
        assert result.file_summaries[0].services_migrated == ["S3"]


# ===================================================================
# 7. DTO creation and serialization
# ===================================================================


class TestDTOs:
    """Tests for DTO construction and round-trip serialization."""

    def test_scan_request_defaults(self):
        req = ScanRequest(
            root_path="/src",
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
        )
        assert req.languages == []
        assert req.exclude_patterns == []

    def test_file_entry_serialization(self):
        entry = FileEntry(
            path="app.py",
            language=Language.PYTHON,
            services_detected=["S3", "Lambda"],
            confidence=0.85,
            line_count=120,
        )
        data = entry.model_dump()
        assert data["path"] == "app.py"
        assert data["confidence"] == 0.85
        round_trip = FileEntry.model_validate(data)
        assert round_trip == entry

    def test_scan_result_serialization(self):
        result = ScanResult(
            project_id="abc123",
            root_path="/project",
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
            files=[],
            total_files_scanned=0,
            services_found=[],
        )
        data = result.model_dump()
        assert data["project_id"] == "abc123"

    def test_pattern_dto_confidence_clamped(self):
        """PatternDTO confidence must be between 0 and 1."""
        with pytest.raises(Exception):
            PatternDTO(
                pattern_id="x",
                name="bad",
                source_provider=CloudProvider.AWS,
                target_provider=CloudProvider.GCP,
                language=Language.PYTHON,
                confidence=1.5,
            )

    def test_transform_step_dto(self):
        step = TransformStep(
            step_id="s1",
            file_path="main.py",
            pattern_id="p1",
            description="Migrate S3 calls",
            confidence=0.88,
            depends_on=["s0"],
        )
        assert step.depends_on == ["s0"]
        data = step.model_dump()
        assert data["step_id"] == "s1"

    def test_issue_dto(self):
        issue = IssueDTO(
            message="Found residual reference",
            severity=Severity.WARNING,
            file_path="app.py",
            line=42,
            rule="residual-ref",
        )
        assert issue.severity == Severity.WARNING
        data = issue.model_dump()
        assert data["line"] == 42

    def test_report_dto_defaults(self):
        report = ReportDTO(
            report_id="r1",
            project_id="p1",
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
        )
        assert report.total_files == 0
        assert report.validation_passed is True
        assert report.warnings == []


# ===================================================================
# 8. DAG Orchestrator
# ===================================================================


class TestDAGOrchestrator:
    """Tests for the DAG-based workflow orchestrator."""

    @pytest.mark.asyncio
    async def test_simple_linear_dag(self):
        results = []

        async def step_a():
            results.append("A")
            return "result_a"

        async def step_b(deps):
            results.append("B")
            return deps["A"]

        dag = DAGOrchestrator(max_parallel=2)
        dag.add_node("A", step_a)
        dag.add_node("B", step_b, depends_on=["A"])

        output = await dag.execute()

        assert output["A"] == "result_a"
        assert output["B"] == "result_a"
        # A must run before B.
        assert results.index("A") < results.index("B")

    @pytest.mark.asyncio
    async def test_parallel_independent_nodes(self):
        order = []

        async def node(name):
            order.append(name)
            return name

        dag = DAGOrchestrator(max_parallel=4)
        dag.add_node("X", lambda: node("X"))
        dag.add_node("Y", lambda: node("Y"))
        dag.add_node("Z", lambda: node("Z"))

        output = await dag.execute()

        assert set(output.keys()) == {"X", "Y", "Z"}

    @pytest.mark.asyncio
    async def test_dag_cycle_detection(self):
        dag = DAGOrchestrator()
        dag.add_node("A", AsyncMock(), depends_on=["B"])
        dag.add_node("B", AsyncMock(), depends_on=["A"])

        with pytest.raises(DAGExecutionError, match="[Cc]ycle"):
            await dag.execute()

    @pytest.mark.asyncio
    async def test_dag_duplicate_node_raises(self):
        dag = DAGOrchestrator()
        dag.add_node("A", AsyncMock())

        with pytest.raises(ValueError, match="Duplicate"):
            dag.add_node("A", AsyncMock())

    @pytest.mark.asyncio
    async def test_dag_failed_node_skips_dependents(self):
        async def fail_action():
            raise RuntimeError("boom")

        async def after_fail(deps):
            return "should not run"

        dag = DAGOrchestrator(max_parallel=2)
        dag.add_node("fail", fail_action)
        dag.add_node("after", after_fail, depends_on=["fail"])

        output = await dag.execute()

        # "fail" failed, "after" should be skipped; neither in completed results.
        assert "fail" not in output
        assert "after" not in output
        assert dag.nodes["fail"].status == NodeStatus.FAILED
        assert dag.nodes["after"].status == NodeStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_dag_reset(self):
        dag = DAGOrchestrator()
        dag.add_node("A", AsyncMock(return_value=1))

        await dag.execute()
        assert dag.nodes["A"].status == NodeStatus.COMPLETED

        dag.reset()
        assert dag.nodes["A"].status == NodeStatus.PENDING
        assert dag.nodes["A"].result is None

    @pytest.mark.asyncio
    async def test_dag_diamond_graph(self):
        """Diamond: A -> B, A -> C, B -> D, C -> D."""
        order = []

        async def make(name, _deps=None):
            order.append(name)
            return name

        dag = DAGOrchestrator(max_parallel=4)
        dag.add_node("A", lambda: make("A"))
        dag.add_node("B", lambda deps: make("B", deps), depends_on=["A"])
        dag.add_node("C", lambda deps: make("C", deps), depends_on=["A"])
        dag.add_node("D", lambda deps: make("D", deps), depends_on=["B", "C"])

        output = await dag.execute()

        assert set(output.keys()) == {"A", "B", "C", "D"}
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")


# ===================================================================
# 9. EventDispatcher
# ===================================================================


class TestEventDispatcher:
    """Tests for the in-memory event bus."""

    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self):
        dispatcher = EventDispatcher()
        received = []

        async def handler(event):
            received.append(event)

        dispatcher.subscribe("ScanStarted", handler)
        await dispatcher.publish({"type": "ScanStarted", "project_id": "p1"})

        assert len(received) == 1
        assert received[0]["project_id"] == "p1"

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self):
        dispatcher = EventDispatcher()
        # Should not raise.
        await dispatcher.publish({"type": "Unknown"})

    @pytest.mark.asyncio
    async def test_subscribe_all(self):
        dispatcher = EventDispatcher()
        received = []

        async def global_handler(event):
            received.append(event)

        dispatcher.subscribe_all(global_handler)
        await dispatcher.publish({"type": "A"})
        await dispatcher.publish({"type": "B"})

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        dispatcher = EventDispatcher()
        received = []

        async def handler(event):
            received.append(event)

        dispatcher.subscribe("E", handler)
        dispatcher.unsubscribe("E", handler)
        await dispatcher.publish({"type": "E"})

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        dispatcher = EventDispatcher()
        received = []

        def sync_handler(event):
            received.append(event)

        dispatcher.subscribe("Evt", sync_handler)
        await dispatcher.publish({"type": "Evt", "data": 42})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handler_count(self):
        dispatcher = EventDispatcher()
        dispatcher.subscribe("A", AsyncMock())
        dispatcher.subscribe("A", AsyncMock())
        dispatcher.subscribe("B", AsyncMock())
        dispatcher.subscribe_all(AsyncMock())

        assert dispatcher.handler_count == 4

    @pytest.mark.asyncio
    async def test_clear_handlers(self):
        dispatcher = EventDispatcher()
        dispatcher.subscribe("A", AsyncMock())
        dispatcher.subscribe_all(AsyncMock())

        dispatcher.clear()
        assert dispatcher.handler_count == 0

    @pytest.mark.asyncio
    async def test_event_type_resolved_from_object_class(self):
        """When event is not a dict, type is resolved from the class name."""
        dispatcher = EventDispatcher()
        received = []

        @dataclass
        class ScanStarted:
            project_id: str

        async def handler(event):
            received.append(event)

        dispatcher.subscribe("ScanStarted", handler)
        await dispatcher.publish(ScanStarted(project_id="p1"))

        assert len(received) == 1
        assert received[0].project_id == "p1"

    def test_publish_sync(self):
        dispatcher = EventDispatcher()
        received = []

        def handler(event):
            received.append(event)

        dispatcher.subscribe("Evt", handler)
        dispatcher.publish_sync({"type": "Evt", "val": 1})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_sync_handler_exception_during_publish(self):
        """Cover line 76-77: sync handler raises during async publish."""
        dispatcher = EventDispatcher()

        def bad_handler(event):
            raise ValueError("boom")

        dispatcher.subscribe("Evt", bad_handler)
        # Should not raise — error is logged
        await dispatcher.publish({"type": "Evt"})

    @pytest.mark.asyncio
    async def test_async_handler_exception_during_publish(self):
        """Cover line 83: async handler raises, caught by gather."""
        dispatcher = EventDispatcher()

        async def bad_handler(event):
            raise RuntimeError("async boom")

        dispatcher.subscribe("Evt", bad_handler)
        # Should not raise — error is logged
        await dispatcher.publish({"type": "Evt"})

    def test_publish_sync_with_async_handler(self):
        """Cover lines 94-96: async handler skipped during sync publish."""
        dispatcher = EventDispatcher()

        async def async_handler(event):
            pass  # pragma: no cover

        dispatcher.subscribe("Evt", async_handler)
        # Should not raise — async handler is skipped with a warning
        dispatcher.publish_sync({"type": "Evt"})

    def test_publish_sync_handler_exception(self):
        """Cover lines 97-98: handler raises during sync publish."""
        dispatcher = EventDispatcher()

        def bad_handler(event):
            raise ValueError("sync boom")

        dispatcher.subscribe("Evt", bad_handler)
        # Should not raise — error is logged
        dispatcher.publish_sync({"type": "Evt"})
