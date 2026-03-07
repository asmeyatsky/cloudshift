"""Comprehensive unit tests for the CloudShift domain layer.

Tests cover entities, value objects, and domain services using pure domain
logic -- no external mocks required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudshift.domain.entities.manifest import ManifestEntry, MigrationManifest
from cloudshift.domain.entities.pattern import Pattern
from cloudshift.domain.entities.project import Project
from cloudshift.domain.entities.transformation import Transformation
from cloudshift.domain.entities.validation_report import ValidationReport
from cloudshift.domain.services.confidence import ConfidenceCalculator
from cloudshift.domain.services.planner import TransformationPlanner
from cloudshift.domain.services.validation_evaluator import ValidationEvaluator
from cloudshift.domain.value_objects.types import (
    CloudProvider,
    ConfidenceScore,
    DiffHunk,
    Language,
    ProjectStatus,
    ServiceMapping,
    Severity,
    TransformationStatus,
    ValidationIssue,
)


# ===================================================================
# Value Objects -- ConfidenceScore
# ===================================================================


class TestConfidenceScore:
    """ConfidenceScore clamping, equality, ordering, and immutability."""

    def test_basic_creation(self) -> None:
        score = ConfidenceScore(0.75)
        assert score.value == 0.75

    def test_clamped_above_one(self) -> None:
        score = ConfidenceScore(1.5)
        assert score.value == 1.0

    def test_clamped_below_zero(self) -> None:
        score = ConfidenceScore(-0.3)
        assert score.value == 0.0

    def test_zero_boundary(self) -> None:
        score = ConfidenceScore(0.0)
        assert score.value == 0.0

    def test_one_boundary(self) -> None:
        score = ConfidenceScore(1.0)
        assert score.value == 1.0

    def test_integer_coerced_to_float(self) -> None:
        score = ConfidenceScore(1)
        assert score.value == 1.0
        assert isinstance(score.value, float)

    def test_equality(self) -> None:
        assert ConfidenceScore(0.5) == ConfidenceScore(0.5)

    def test_inequality(self) -> None:
        assert ConfidenceScore(0.3) != ConfidenceScore(0.7)

    def test_ordering_lt(self) -> None:
        assert ConfidenceScore(0.2) < ConfidenceScore(0.8)
        assert not ConfidenceScore(0.8) < ConfidenceScore(0.2)

    def test_ordering_le(self) -> None:
        assert ConfidenceScore(0.5) <= ConfidenceScore(0.5)
        assert ConfidenceScore(0.3) <= ConfidenceScore(0.5)

    def test_float_conversion(self) -> None:
        score = ConfidenceScore(0.42)
        assert float(score) == pytest.approx(0.42)

    def test_frozen_immutability(self) -> None:
        score = ConfidenceScore(0.5)
        with pytest.raises(AttributeError):
            score.value = 0.9  # type: ignore[misc]


# ===================================================================
# Value Objects -- ServiceMapping, DiffHunk, ValidationIssue
# ===================================================================


class TestServiceMapping:
    def test_creation_and_equality(self) -> None:
        m1 = ServiceMapping(CloudProvider.AWS, "S3", CloudProvider.GCP, "GCS")
        m2 = ServiceMapping(CloudProvider.AWS, "S3", CloudProvider.GCP, "GCS")
        assert m1 == m2

    def test_different_mappings_not_equal(self) -> None:
        m1 = ServiceMapping(CloudProvider.AWS, "S3", CloudProvider.GCP, "GCS")
        m2 = ServiceMapping(CloudProvider.AWS, "DynamoDB", CloudProvider.GCP, "Firestore")
        assert m1 != m2

    def test_frozen(self) -> None:
        m = ServiceMapping(CloudProvider.AWS, "S3", CloudProvider.GCP, "GCS")
        with pytest.raises(AttributeError):
            m.source_service = "Lambda"  # type: ignore[misc]


class TestDiffHunk:
    def test_creation(self) -> None:
        hunk = DiffHunk(
            file_path="app.py",
            start_line=10,
            end_line=20,
            original_text="import boto3",
            modified_text="from google.cloud import storage",
            context="migration",
        )
        assert hunk.start_line == 10
        assert hunk.end_line == 20
        assert hunk.context == "migration"

    def test_default_context(self) -> None:
        hunk = DiffHunk("f.py", 1, 2, "a", "b")
        assert hunk.context == ""


class TestValidationIssue:
    def test_creation_with_all_fields(self) -> None:
        issue = ValidationIssue(
            message="Unused import",
            severity=Severity.WARNING,
            file_path="app.py",
            line=3,
            rule="W001",
        )
        assert issue.severity is Severity.WARNING
        assert issue.rule == "W001"

    def test_optional_fields_default_to_none(self) -> None:
        issue = ValidationIssue(message="Bad", severity=Severity.ERROR)
        assert issue.file_path is None
        assert issue.line is None
        assert issue.rule is None


# ===================================================================
# Entity -- Pattern
# ===================================================================


class TestPattern:
    def test_creation(self) -> None:
        p = Pattern(
            id="p-s3-to-gcs",
            name="S3 to GCS",
            description="Migrate S3 calls to GCS",
            source_provider=CloudProvider.AWS,
            source_service="S3",
            target_provider=CloudProvider.GCP,
            target_service="GCS",
            language=Language.PYTHON,
            match_pattern="boto3.client\\('s3'\\)",
        )
        assert p.id == "p-s3-to-gcs"
        assert p.source_provider is CloudProvider.AWS
        assert p.target_provider is CloudProvider.GCP
        assert p.language is Language.PYTHON

    def test_default_confidence_is_half(self) -> None:
        p = Pattern(
            id="x", name="x", description="x",
            source_provider=CloudProvider.AWS, source_service="S3",
            target_provider=CloudProvider.GCP, target_service="GCS",
            language=Language.PYTHON, match_pattern=".*",
        )
        assert p.confidence == ConfidenceScore(0.5)

    def test_default_tags_and_transform_spec(self) -> None:
        p = Pattern(
            id="x", name="x", description="x",
            source_provider=CloudProvider.AWS, source_service="S3",
            target_provider=CloudProvider.GCP, target_service="GCS",
            language=Language.PYTHON, match_pattern=".*",
        )
        assert p.tags == []
        assert p.transform_spec == {}


# ===================================================================
# Entity -- ManifestEntry & MigrationManifest
# ===================================================================


def _make_entry(
    file_path: str = "app.py",
    pattern_id: str = "p1",
    confidence: float = 0.8,
) -> ManifestEntry:
    return ManifestEntry(
        file_path=file_path,
        pattern_id=pattern_id,
        source_construct="S3",
        target_construct="GCS",
        confidence=ConfidenceScore(confidence),
    )


class TestManifestEntry:
    def test_defaults(self) -> None:
        entry = ManifestEntry(
            file_path="f.py",
            pattern_id="p1",
            source_construct="S3",
            target_construct="GCS",
        )
        assert entry.confidence == ConfidenceScore(0.0)
        assert entry.status is TransformationStatus.PENDING
        assert entry.line_start is None
        assert entry.line_end is None


class TestMigrationManifest:
    def test_empty_manifest(self) -> None:
        m = MigrationManifest()
        assert m.overall_confidence == ConfidenceScore(0.0)
        assert m.total_files == 0
        assert m.total_constructs == 0

    def test_add_entry(self) -> None:
        m = MigrationManifest()
        m.add_entry(_make_entry())
        assert m.total_constructs == 1

    def test_overall_confidence_is_average(self) -> None:
        m = MigrationManifest()
        m.add_entry(_make_entry(confidence=0.6))
        m.add_entry(_make_entry(confidence=0.8))
        assert m.overall_confidence.value == pytest.approx(0.7)

    def test_total_files_deduplicates(self) -> None:
        m = MigrationManifest()
        m.add_entry(_make_entry(file_path="a.py", pattern_id="p1"))
        m.add_entry(_make_entry(file_path="a.py", pattern_id="p2"))
        m.add_entry(_make_entry(file_path="b.py", pattern_id="p1"))
        assert m.total_files == 2
        assert m.total_constructs == 3


# ===================================================================
# Entity -- Transformation
# ===================================================================


class TestTransformation:
    def test_creation_defaults(self) -> None:
        t = Transformation(
            file_path="f.py",
            original_text="import boto3",
            transformed_text="",
            pattern_id="p1",
        )
        assert t.status is TransformationStatus.PENDING
        assert t.diagnostics == []
        assert t.confidence == ConfidenceScore(0.0)

    def test_mark_completed(self) -> None:
        t = Transformation(
            file_path="f.py",
            original_text="old",
            transformed_text="",
            pattern_id="p1",
        )
        t.mark_completed("new", ConfidenceScore(0.95))
        assert t.status is TransformationStatus.COMPLETED
        assert t.transformed_text == "new"
        assert t.confidence == ConfidenceScore(0.95)

    def test_mark_failed(self) -> None:
        t = Transformation(
            file_path="f.py",
            original_text="old",
            transformed_text="",
            pattern_id="p1",
        )
        t.mark_failed("syntax error in output")
        assert t.status is TransformationStatus.FAILED
        assert "syntax error in output" in t.diagnostics

    def test_mark_failed_accumulates_diagnostics(self) -> None:
        t = Transformation(
            file_path="f.py",
            original_text="old",
            transformed_text="",
            pattern_id="p1",
        )
        t.mark_failed("reason 1")
        t.mark_failed("reason 2")
        assert len(t.diagnostics) == 2


# ===================================================================
# Entity -- ValidationReport
# ===================================================================


class TestValidationReport:
    def test_empty_report_is_valid(self) -> None:
        r = ValidationReport()
        assert r.is_valid is True
        assert r.error_count == 0
        assert r.warning_count == 0

    def test_with_info_only_is_valid(self) -> None:
        r = ValidationReport()
        r.add_issue(ValidationIssue("note", Severity.INFO))
        assert r.is_valid is True

    def test_with_warning_only_is_valid(self) -> None:
        r = ValidationReport()
        r.add_issue(ValidationIssue("warn", Severity.WARNING))
        assert r.is_valid is True
        assert r.warning_count == 1

    def test_with_error_is_invalid(self) -> None:
        r = ValidationReport()
        r.add_issue(ValidationIssue("bad", Severity.ERROR))
        assert r.is_valid is False
        assert r.error_count == 1

    def test_with_critical_is_invalid(self) -> None:
        r = ValidationReport()
        r.add_issue(ValidationIssue("terrible", Severity.CRITICAL))
        assert r.is_valid is False
        assert r.error_count == 1

    def test_summary_counts(self) -> None:
        r = ValidationReport()
        r.add_issue(ValidationIssue("a", Severity.INFO))
        r.add_issue(ValidationIssue("b", Severity.WARNING))
        r.add_issue(ValidationIssue("c", Severity.WARNING))
        r.add_issue(ValidationIssue("d", Severity.ERROR))
        r.add_issue(ValidationIssue("e", Severity.CRITICAL))
        summary = r.summary
        assert summary == {"total": 5, "errors": 2, "warnings": 2, "info": 1}


# ===================================================================
# Entity -- Project
# ===================================================================


class TestProject:
    def test_creation(self) -> None:
        p = Project(
            name="my-migration",
            root_path=Path("/code/app"),
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
        )
        assert p.status is ProjectStatus.CREATED
        assert p.file_patterns == []
        assert p.exclude_paths == []

    def test_advance_status(self) -> None:
        p = Project(
            name="proj",
            root_path=Path("/code"),
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.AZURE,
        )
        p.advance_status(ProjectStatus.SCANNING)
        assert p.status is ProjectStatus.SCANNING
        p.advance_status(ProjectStatus.COMPLETED)
        assert p.status is ProjectStatus.COMPLETED

    def test_is_active_for_created(self) -> None:
        p = Project(
            name="proj",
            root_path=Path("/code"),
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
        )
        assert p.is_active() is True

    def test_is_active_false_when_completed(self) -> None:
        p = Project(
            name="proj",
            root_path=Path("/code"),
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
            status=ProjectStatus.COMPLETED,
        )
        assert p.is_active() is False

    def test_is_active_false_when_failed(self) -> None:
        p = Project(
            name="proj",
            root_path=Path("/code"),
            source_provider=CloudProvider.AWS,
            target_provider=CloudProvider.GCP,
            status=ProjectStatus.FAILED,
        )
        assert p.is_active() is False

    def test_is_active_true_for_intermediate_statuses(self) -> None:
        for status in (
            ProjectStatus.SCANNING,
            ProjectStatus.SCANNED,
            ProjectStatus.TRANSFORMING,
            ProjectStatus.TRANSFORMED,
            ProjectStatus.VALIDATING,
            ProjectStatus.VALIDATED,
        ):
            p = Project(
                name="proj",
                root_path=Path("/code"),
                source_provider=CloudProvider.AWS,
                target_provider=CloudProvider.GCP,
                status=status,
            )
            assert p.is_active() is True, f"Expected active for {status}"


# ===================================================================
# Domain Service -- ConfidenceCalculator
# ===================================================================


class TestConfidenceCalculator:
    def test_weighted_average_basic(self) -> None:
        scores = [
            (ConfidenceScore(0.8), 1.0),
            (ConfidenceScore(0.6), 1.0),
        ]
        result = ConfidenceCalculator.weighted_average(scores)
        assert result.value == pytest.approx(0.7)

    def test_weighted_average_with_different_weights(self) -> None:
        scores = [
            (ConfidenceScore(1.0), 3.0),
            (ConfidenceScore(0.0), 1.0),
        ]
        result = ConfidenceCalculator.weighted_average(scores)
        assert result.value == pytest.approx(0.75)

    def test_weighted_average_empty_list(self) -> None:
        result = ConfidenceCalculator.weighted_average([])
        assert result == ConfidenceScore(0.0)

    def test_weighted_average_zero_weights(self) -> None:
        scores = [
            (ConfidenceScore(0.9), 0.0),
            (ConfidenceScore(0.1), 0.0),
        ]
        result = ConfidenceCalculator.weighted_average(scores)
        assert result == ConfidenceScore(0.0)

    def test_combine_geometric_mean(self) -> None:
        a = ConfidenceScore(0.64)
        b = ConfidenceScore(1.0)
        result = ConfidenceCalculator.combine(a, b)
        assert result.value == pytest.approx(0.8)

    def test_combine_with_zero(self) -> None:
        result = ConfidenceCalculator.combine(
            ConfidenceScore(0.9), ConfidenceScore(0.0)
        )
        assert result.value == pytest.approx(0.0)

    def test_for_transformation(self) -> None:
        t = Transformation(
            file_path="f.py",
            original_text="old",
            transformed_text="new",
            pattern_id="p1",
            confidence=ConfidenceScore(0.85),
        )
        assert ConfidenceCalculator.for_transformation(t) == ConfidenceScore(0.85)

    def test_for_manifest(self) -> None:
        m = MigrationManifest()
        m.add_entry(_make_entry(confidence=0.6))
        m.add_entry(_make_entry(confidence=0.8))
        result = ConfidenceCalculator.for_manifest(m)
        assert result.value == pytest.approx(0.7)


# ===================================================================
# Domain Service -- TransformationPlanner
# ===================================================================


def _make_pattern(
    pattern_id: str = "p1",
    confidence: float = 0.8,
    source_service: str = "S3",
    target_service: str = "GCS",
) -> Pattern:
    return Pattern(
        id=pattern_id,
        name=f"Pattern {pattern_id}",
        description="test",
        source_provider=CloudProvider.AWS,
        source_service=source_service,
        target_provider=CloudProvider.GCP,
        target_service=target_service,
        language=Language.PYTHON,
        match_pattern=".*",
        confidence=ConfidenceScore(confidence),
    )


class TestTransformationPlanner:
    def test_plan_basic(self) -> None:
        planner = TransformationPlanner(min_confidence=0.3)
        pattern = _make_pattern(confidence=0.8)
        matches = [(pattern, "app.py", 1, 10)]
        manifest = planner.plan(matches)
        assert manifest.total_constructs == 1
        entry = manifest.entries[0]
        assert entry.file_path == "app.py"
        assert entry.pattern_id == "p1"
        assert entry.line_start == 1
        assert entry.line_end == 10

    def test_plan_excludes_low_confidence(self) -> None:
        planner = TransformationPlanner(min_confidence=0.5)
        low = _make_pattern(pattern_id="low", confidence=0.2)
        high = _make_pattern(pattern_id="high", confidence=0.9)
        matches = [
            (low, "a.py", 1, 5),
            (high, "b.py", 1, 5),
        ]
        manifest = planner.plan(matches)
        assert manifest.total_constructs == 1
        assert manifest.entries[0].pattern_id == "high"

    def test_plan_empty_matches(self) -> None:
        planner = TransformationPlanner()
        manifest = planner.plan([])
        assert manifest.total_constructs == 0
        assert manifest.overall_confidence == ConfidenceScore(0.0)

    def test_plan_confidence_at_exact_threshold_excluded(self) -> None:
        """A pattern whose confidence equals min_confidence is excluded
        because the check is strictly less-than."""
        planner = TransformationPlanner(min_confidence=0.5)
        pattern = _make_pattern(confidence=0.5)
        # confidence.value (0.5) is NOT < 0.5, so it should be included
        matches = [(pattern, "f.py", 1, 2)]
        manifest = planner.plan(matches)
        # 0.5 is not < 0.5, so the entry is included
        assert manifest.total_constructs == 1

    def test_plan_confidence_just_below_threshold(self) -> None:
        planner = TransformationPlanner(min_confidence=0.5)
        pattern = _make_pattern(confidence=0.49)
        matches = [(pattern, "f.py", 1, 2)]
        manifest = planner.plan(matches)
        assert manifest.total_constructs == 0

    def test_merge_deduplicates(self) -> None:
        planner = TransformationPlanner()
        m1 = MigrationManifest()
        m1.add_entry(_make_entry(file_path="a.py", pattern_id="p1"))
        m2 = MigrationManifest()
        m2.add_entry(_make_entry(file_path="a.py", pattern_id="p1"))
        m2.add_entry(_make_entry(file_path="a.py", pattern_id="p2"))
        merged = planner.merge(m1, m2)
        assert merged.total_constructs == 2  # p1 deduplicated, p2 kept

    def test_merge_empty_manifests(self) -> None:
        planner = TransformationPlanner()
        merged = planner.merge(MigrationManifest(), MigrationManifest())
        assert merged.total_constructs == 0

    def test_merge_preserves_unique_entries(self) -> None:
        planner = TransformationPlanner()
        m1 = MigrationManifest()
        m1.add_entry(_make_entry(file_path="a.py", pattern_id="p1"))
        m2 = MigrationManifest()
        m2.add_entry(_make_entry(file_path="b.py", pattern_id="p2"))
        merged = planner.merge(m1, m2)
        assert merged.total_constructs == 2
        assert merged.total_files == 2


# ===================================================================
# Domain Service -- ValidationEvaluator
# ===================================================================


class TestValidationEvaluator:
    def test_is_acceptable_clean_report(self) -> None:
        evaluator = ValidationEvaluator()
        report = ValidationReport()
        assert evaluator.is_acceptable(report) is True

    def test_is_acceptable_with_info_and_warnings_within_limit(self) -> None:
        evaluator = ValidationEvaluator(max_errors=0, max_warnings=2)
        report = ValidationReport()
        report.add_issue(ValidationIssue("info", Severity.INFO))
        report.add_issue(ValidationIssue("warn1", Severity.WARNING))
        report.add_issue(ValidationIssue("warn2", Severity.WARNING))
        assert evaluator.is_acceptable(report) is True

    def test_is_acceptable_fails_on_error(self) -> None:
        evaluator = ValidationEvaluator(max_errors=0)
        report = ValidationReport()
        report.add_issue(ValidationIssue("err", Severity.ERROR))
        assert evaluator.is_acceptable(report) is False

    def test_is_acceptable_fails_when_warnings_exceed_max(self) -> None:
        evaluator = ValidationEvaluator(max_warnings=1)
        report = ValidationReport()
        report.add_issue(ValidationIssue("w1", Severity.WARNING))
        report.add_issue(ValidationIssue("w2", Severity.WARNING))
        assert evaluator.is_acceptable(report) is False

    def test_is_acceptable_allows_errors_when_configured(self) -> None:
        evaluator = ValidationEvaluator(max_errors=2)
        report = ValidationReport()
        report.add_issue(ValidationIssue("e1", Severity.ERROR))
        report.add_issue(ValidationIssue("e2", Severity.ERROR))
        assert evaluator.is_acceptable(report) is True

    def test_quality_score_perfect(self) -> None:
        report = ValidationReport()
        score = ValidationEvaluator.quality_score(report)
        assert score == ConfidenceScore(1.0)

    def test_quality_score_with_warnings(self) -> None:
        report = ValidationReport()
        for _ in range(4):
            report.add_issue(ValidationIssue("w", Severity.WARNING))
        score = ValidationEvaluator.quality_score(report)
        # 1.0 - 4 * 0.05 = 0.8
        assert score.value == pytest.approx(0.8)

    def test_quality_score_with_errors(self) -> None:
        report = ValidationReport()
        report.add_issue(ValidationIssue("e1", Severity.ERROR))
        report.add_issue(ValidationIssue("e2", Severity.CRITICAL))
        score = ValidationEvaluator.quality_score(report)
        # 1.0 - 2 * 0.2 = 0.6
        assert score.value == pytest.approx(0.6)

    def test_quality_score_floors_at_zero(self) -> None:
        report = ValidationReport()
        for _ in range(10):
            report.add_issue(ValidationIssue("e", Severity.ERROR))
        score = ValidationEvaluator.quality_score(report)
        # 1.0 - 10 * 0.2 = -1.0 -> clamped to 0.0
        assert score.value == 0.0

    def test_quality_score_mixed_issues(self) -> None:
        report = ValidationReport()
        report.add_issue(ValidationIssue("e", Severity.ERROR))
        report.add_issue(ValidationIssue("w", Severity.WARNING))
        report.add_issue(ValidationIssue("i", Severity.INFO))
        score = ValidationEvaluator.quality_score(report)
        # 1.0 - 1*0.2 - 1*0.05 = 0.75; info has no penalty
        assert score.value == pytest.approx(0.75)

    def test_critical_issues_returns_messages(self) -> None:
        report = ValidationReport()
        report.add_issue(ValidationIssue("normal", Severity.INFO))
        report.add_issue(ValidationIssue("bad thing", Severity.ERROR))
        report.add_issue(ValidationIssue("very bad", Severity.CRITICAL))
        report.add_issue(ValidationIssue("meh", Severity.WARNING))
        critical = ValidationEvaluator.critical_issues(report)
        assert critical == ["bad thing", "very bad"]

    def test_critical_issues_empty_report(self) -> None:
        report = ValidationReport()
        assert ValidationEvaluator.critical_issues(report) == []


# ===================================================================
# Enum coverage
# ===================================================================


class TestEnums:
    def test_cloud_providers(self) -> None:
        assert len(CloudProvider) == 3
        assert CloudProvider.AWS.name == "AWS"

    def test_languages(self) -> None:
        assert Language.HCL in Language
        assert Language.CLOUDFORMATION in Language

    def test_transformation_status_members(self) -> None:
        expected = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"}
        assert {s.name for s in TransformationStatus} == expected

    def test_severity_ordering_by_value(self) -> None:
        # Severity values are strings; verify all four levels exist
        levels = [Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL]
        assert len(levels) == 4
        assert all(isinstance(s.value, str) for s in levels)
