"""Use case: generate a transformation plan from a scan manifest."""

from __future__ import annotations

import uuid
from typing import Protocol

from cloudshift.application.dtos.plan import PlanRequest, PlanResult, TransformStep
from cloudshift.domain.value_objects.types import ConfidenceScore


# ---------------------------------------------------------------------------
# Port protocols
# ---------------------------------------------------------------------------

class PatternEngine(Protocol):
    """Subset of PatternEnginePort needed by this use case."""

    async def match_patterns(
        self, file_path: str, services: list[str], source_provider: str, target_provider: str
    ) -> list[PatternMatch]: ...


class PatternMatch(Protocol):
    """Result of a pattern match."""

    @property
    def pattern_id(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def confidence(self) -> ConfidenceScore: ...


class ManifestStore(Protocol):
    """Retrieve a previously built manifest."""

    async def get_manifest(self, manifest_id: str) -> Manifest | None: ...


class Manifest(Protocol):
    """Structural protocol for a scan manifest."""

    @property
    def source_provider(self) -> str: ...
    @property
    def target_provider(self) -> str: ...
    @property
    def entries(self) -> list[ManifestEntry]: ...


class ManifestEntry(Protocol):
    @property
    def file_path(self) -> str: ...
    @property
    def services(self) -> list[str]: ...


class EventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------

class GeneratePlanUseCase:
    """Take a manifest, match patterns, and create an ordered transformation plan."""

    def __init__(
        self,
        pattern_engine: PatternEngine,
        manifest_store: ManifestStore,
        event_bus: EventPublisher | None = None,
    ) -> None:
        self._pattern_engine = pattern_engine
        self._manifest_store = manifest_store
        self._event_bus = event_bus

    async def execute(self, request: PlanRequest) -> PlanResult:
        plan_id = uuid.uuid4().hex[:12]

        manifest = await self._manifest_store.get_manifest(request.manifest_id)
        if manifest is None:
            return PlanResult(
                plan_id=plan_id,
                project_id=request.project_id,
                error=f"Manifest {request.manifest_id!r} not found.",
            )

        steps: list[TransformStep] = []
        warnings: list[str] = []
        confidences: list[float] = []

        for entry in manifest.entries:
            matches = await self._pattern_engine.match_patterns(
                file_path=entry.file_path,
                services=entry.services,
                source_provider=manifest.source_provider,
                target_provider=manifest.target_provider,
            )
            if not matches:
                warnings.append(f"No patterns matched for {entry.file_path}")
                continue

            for match in matches:
                step_id = uuid.uuid4().hex[:8]
                conf = float(match.confidence)
                confidences.append(conf)

                # Determine dependencies: steps in the same file are sequential.
                deps = [s.step_id for s in steps if s.file_path == entry.file_path]

                steps.append(
                    TransformStep(
                        step_id=step_id,
                        file_path=entry.file_path,
                        pattern_id=match.pattern_id,
                        description=match.description,
                        confidence=conf,
                        depends_on=deps,
                    )
                )

        # Apply strategy-based filtering.
        threshold = {"conservative": 0.8, "balanced": 0.5, "aggressive": 0.2}.get(request.strategy, 0.5)
        filtered = [s for s in steps if s.confidence >= threshold]
        low_conf = [s for s in steps if s.confidence < threshold]
        if low_conf:
            warnings.append(f"{len(low_conf)} step(s) dropped below {request.strategy} threshold ({threshold}).")

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return PlanResult(
            plan_id=plan_id,
            project_id=request.project_id,
            steps=filtered,
            estimated_files_changed=len({s.file_path for s in filtered}),
            estimated_confidence=round(avg_conf, 4),
            warnings=warnings,
        )
