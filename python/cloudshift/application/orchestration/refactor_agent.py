"""RefactorAgent: 7-step pipeline INGEST -> DETECT -> PLAN -> MATCH -> TRANSFORM -> VALIDATE -> COMMIT."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol

from cloudshift.application.dtos.plan import PlanRequest
from cloudshift.application.dtos.scan import ScanRequest
from cloudshift.application.dtos.transform import TransformRequest
from cloudshift.application.dtos.validation import ValidationRequest
from cloudshift.application.orchestration.dag import DAGOrchestrator
from cloudshift.domain.value_objects.types import CloudProvider


class PipelineStage(Enum):
    INGEST = auto()
    DETECT = auto()
    PLAN = auto()
    MATCH = auto()
    TRANSFORM = auto()
    VALIDATE = auto()
    COMMIT = auto()


@dataclass
class PipelineContext:
    """Mutable context threaded through the pipeline stages."""

    root_path: str
    source_provider: CloudProvider
    target_provider: CloudProvider
    # Populated as the pipeline progresses.
    project_id: str | None = None
    manifest_id: str | None = None
    plan_id: str | None = None
    dry_run: bool = False
    stage: PipelineStage = PipelineStage.INGEST
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return len(self.errors) > 0


class ScanUseCase(Protocol):
    async def execute(self, request: ScanRequest) -> Any: ...


class PlanUseCase(Protocol):
    async def execute(self, request: PlanRequest) -> Any: ...


class TransformUseCase(Protocol):
    async def execute(self, request: TransformRequest) -> Any: ...


class ValidateUseCase(Protocol):
    async def execute(self, request: ValidationRequest) -> Any: ...


class CommitPort(Protocol):
    """Port for committing the final result (e.g., git commit, artifact upload)."""

    async def commit(self, root_path: str, plan_id: str, message: str) -> str: ...


class EventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...


class RefactorAgent:
    """Coordinate the full 7-step migration pipeline.

    Stages:
        1. INGEST   - Discover project files
        2. DETECT   - Scan for cloud services
        3. PLAN     - Generate migration plan
        4. MATCH    - Match transformation patterns (part of plan generation)
        5. TRANSFORM - Apply transformations
        6. VALIDATE - Verify correctness
        7. COMMIT   - Persist result
    """

    def __init__(
        self,
        scan: ScanUseCase,
        plan: PlanUseCase,
        transform: TransformUseCase,
        validate: ValidateUseCase,
        commit_port: CommitPort | None = None,
        event_bus: EventPublisher | None = None,
        max_parallel: int = 4,
    ) -> None:
        self._scan = scan
        self._plan = plan
        self._transform = transform
        self._validate = validate
        self._commit = commit_port
        self._event_bus = event_bus
        self._max_parallel = max_parallel

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        """Execute the full pipeline, updating *ctx* in place."""
        stages = [
            (PipelineStage.INGEST, self._stage_ingest),
            (PipelineStage.DETECT, self._stage_detect),
            (PipelineStage.PLAN, self._stage_plan),
            (PipelineStage.MATCH, self._stage_match),
            (PipelineStage.TRANSFORM, self._stage_transform),
            (PipelineStage.VALIDATE, self._stage_validate),
            (PipelineStage.COMMIT, self._stage_commit),
        ]

        for stage_enum, handler in stages:
            ctx.stage = stage_enum
            await self._emit({"type": "PipelineStageStarted", "stage": stage_enum.name})
            try:
                await handler(ctx)
            except Exception as exc:
                ctx.errors.append(f"[{stage_enum.name}] {exc}")
                await self._emit({"type": "PipelineStageFailed", "stage": stage_enum.name, "error": str(exc)})
                break
            if ctx.failed:
                break
            await self._emit({"type": "PipelineStageCompleted", "stage": stage_enum.name})

        return ctx

    async def run_parallel(self, ctx: PipelineContext) -> PipelineContext:
        """Execute using DAG orchestrator where stages allow parallelism.

        Currently the 7-step pipeline is linear, but the DAG wiring allows future
        fan-out (e.g., parallel per-file transforms).
        """
        dag = DAGOrchestrator(max_parallel=self._max_parallel)

        async def _wrap(stage: PipelineStage, handler, _deps: dict | None = None):  # noqa: ANN001
            ctx.stage = stage
            await handler(ctx)
            return ctx.results.get(stage.name)

        dag.add_node("INGEST", lambda: _wrap(PipelineStage.INGEST, self._stage_ingest))
        dag.add_node("DETECT", lambda deps: _wrap(PipelineStage.DETECT, self._stage_detect, deps), depends_on=["INGEST"])
        dag.add_node("PLAN", lambda deps: _wrap(PipelineStage.PLAN, self._stage_plan, deps), depends_on=["DETECT"])
        dag.add_node("MATCH", lambda deps: _wrap(PipelineStage.MATCH, self._stage_match, deps), depends_on=["PLAN"])
        dag.add_node("TRANSFORM", lambda deps: _wrap(PipelineStage.TRANSFORM, self._stage_transform, deps), depends_on=["MATCH"])
        dag.add_node("VALIDATE", lambda deps: _wrap(PipelineStage.VALIDATE, self._stage_validate, deps), depends_on=["TRANSFORM"])
        dag.add_node("COMMIT", lambda deps: _wrap(PipelineStage.COMMIT, self._stage_commit, deps), depends_on=["VALIDATE"])

        await dag.execute()
        return ctx

    # ------------------------------------------------------------------
    # Pipeline stage implementations
    # ------------------------------------------------------------------

    async def _stage_ingest(self, ctx: PipelineContext) -> None:
        """Stage 1+2: scan project and detect services."""
        scan_result = await self._scan.execute(
            ScanRequest(
                root_path=ctx.root_path,
                source_provider=ctx.source_provider,
                target_provider=ctx.target_provider,
            )
        )
        if scan_result.error:
            ctx.errors.append(f"Scan failed: {scan_result.error}")
            return
        ctx.project_id = scan_result.project_id
        ctx.manifest_id = scan_result.project_id  # Manifest shares project ID in simple mode.
        ctx.results["INGEST"] = scan_result

    async def _stage_detect(self, ctx: PipelineContext) -> None:
        """Stage 2: detection is performed during scan; this is a validation checkpoint."""
        scan_result = ctx.results.get("INGEST")
        if scan_result is None or not scan_result.services_found:
            ctx.errors.append("No cloud services detected during scan.")
            return
        ctx.results["DETECT"] = scan_result.services_found

    async def _stage_plan(self, ctx: PipelineContext) -> None:
        """Stage 3: generate migration plan."""
        plan_result = await self._plan.execute(
            PlanRequest(
                project_id=ctx.project_id or "",
                manifest_id=ctx.manifest_id or "",
            )
        )
        if plan_result.error:
            ctx.errors.append(f"Plan generation failed: {plan_result.error}")
            return
        ctx.plan_id = plan_result.plan_id
        ctx.results["PLAN"] = plan_result

    async def _stage_match(self, ctx: PipelineContext) -> None:
        """Stage 4: pattern matching (already done inside plan generation; validate here)."""
        plan_result = ctx.results.get("PLAN")
        if plan_result is None or not plan_result.steps:
            ctx.errors.append("No transformation steps produced by planning.")
            return
        ctx.results["MATCH"] = [s.pattern_id for s in plan_result.steps]

    async def _stage_transform(self, ctx: PipelineContext) -> None:
        """Stage 5: apply transformations."""
        transform_result = await self._transform.execute(
            TransformRequest(
                plan_id=ctx.plan_id or "",
                dry_run=ctx.dry_run,
            )
        )
        if not transform_result.success:
            ctx.errors.append(f"Transform failed: {'; '.join(transform_result.errors)}")
            return
        ctx.results["TRANSFORM"] = transform_result

    async def _stage_validate(self, ctx: PipelineContext) -> None:
        """Stage 6: validate transformations."""
        validation_result = await self._validate.execute(
            ValidationRequest(plan_id=ctx.plan_id or "")
        )
        if not validation_result.passed:
            issues_summary = "; ".join(i.message for i in validation_result.issues[:5])
            ctx.errors.append(f"Validation failed: {issues_summary}")
            return
        ctx.results["VALIDATE"] = validation_result

    async def _stage_commit(self, ctx: PipelineContext) -> None:
        """Stage 7: commit the result."""
        if ctx.dry_run:
            ctx.results["COMMIT"] = "dry-run: no commit"
            return
        if self._commit is None:
            ctx.results["COMMIT"] = "no commit port configured"
            return
        commit_ref = await self._commit.commit(
            ctx.root_path,
            ctx.plan_id or "",
            f"cloudshift: migrate {ctx.source_provider.name} -> {ctx.target_provider.name}",
        )
        ctx.results["COMMIT"] = commit_ref

    async def _emit(self, event: object) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)
