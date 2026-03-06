"""Use case: generate an audit report summarising the migration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from cloudshift.application.dtos.report import FileSummary, ReportDTO
from cloudshift.domain.value_objects.types import CloudProvider


# ---------------------------------------------------------------------------
# Port protocols
# ---------------------------------------------------------------------------

class ProjectStore(Protocol):
    async def get_project(self, project_id: str) -> ProjectInfo | None: ...


class ProjectInfo(Protocol):
    @property
    def project_id(self) -> str: ...
    @property
    def source_provider(self) -> CloudProvider: ...
    @property
    def target_provider(self) -> CloudProvider: ...


class ScanStore(Protocol):
    async def get_scan_summary(self, project_id: str) -> ScanSummary | None: ...


class ScanSummary(Protocol):
    @property
    def total_files(self) -> int: ...
    @property
    def entries(self) -> list[ScanFileEntry]: ...


class ScanFileEntry(Protocol):
    @property
    def path(self) -> str: ...
    @property
    def services(self) -> list[str]: ...
    @property
    def confidence(self) -> float: ...


class TransformStore(Protocol):
    async def get_transform_summary(self, project_id: str) -> TransformSummary | None: ...


class TransformSummary(Protocol):
    @property
    def files_modified(self) -> int: ...
    @property
    def patterns_applied(self) -> int: ...
    @property
    def modified_paths(self) -> list[str]: ...


class ValidationStore(Protocol):
    async def get_validation_summary(self, project_id: str) -> ValidationSummary | None: ...


class ValidationSummary(Protocol):
    @property
    def passed(self) -> bool: ...
    @property
    def issue_count(self) -> int: ...
    @property
    def warnings(self) -> list[str]: ...


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------

class GenerateReportUseCase:
    """Aggregate scan, transform, and validation data into an audit report."""

    def __init__(
        self,
        project_store: ProjectStore,
        scan_store: ScanStore,
        transform_store: TransformStore,
        validation_store: ValidationStore,
    ) -> None:
        self._projects = project_store
        self._scans = scan_store
        self._transforms = transform_store
        self._validations = validation_store

    async def execute(self, project_id: str) -> ReportDTO:
        report_id = uuid.uuid4().hex[:12]

        project = await self._projects.get_project(project_id)
        if project is None:
            return ReportDTO(
                report_id=report_id,
                project_id=project_id,
                source_provider=CloudProvider.AWS,
                target_provider=CloudProvider.GCP,
                notes=f"Project {project_id!r} not found.",
            )

        scan = await self._scans.get_scan_summary(project_id)
        transform = await self._transforms.get_transform_summary(project_id)
        validation = await self._validations.get_validation_summary(project_id)

        modified_paths = set(transform.modified_paths) if transform else set()

        file_summaries: list[FileSummary] = []
        if scan:
            for entry in scan.entries:
                file_summaries.append(
                    FileSummary(
                        path=entry.path,
                        services_migrated=entry.services if entry.path in modified_paths else [],
                        issues=0,
                        confidence=entry.confidence,
                    )
                )

        confidences = [fs.confidence for fs in file_summaries if fs.confidence > 0]
        overall = sum(confidences) / len(confidences) if confidences else 0.0

        return ReportDTO(
            report_id=report_id,
            project_id=project_id,
            source_provider=project.source_provider,
            target_provider=project.target_provider,
            generated_at=datetime.now(timezone.utc),
            total_files=scan.total_files if scan else 0,
            files_changed=transform.files_modified if transform else 0,
            patterns_applied=transform.patterns_applied if transform else 0,
            validation_passed=validation.passed if validation else False,
            overall_confidence=round(overall, 4),
            file_summaries=file_summaries,
            warnings=validation.warnings if validation else [],
        )
