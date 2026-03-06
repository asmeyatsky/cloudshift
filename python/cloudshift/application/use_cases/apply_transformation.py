"""Use case: apply pattern-based transformations and generate diffs."""

from __future__ import annotations

import hashlib
from typing import Protocol

from cloudshift.application.dtos.transform import DiffResult, HunkDTO, TransformRequest, TransformResult


# ---------------------------------------------------------------------------
# Port protocols
# ---------------------------------------------------------------------------

class PlanStore(Protocol):
    """Retrieve a transformation plan and its steps."""

    async def get_plan(self, plan_id: str) -> Plan | None: ...


class Plan(Protocol):
    @property
    def plan_id(self) -> str: ...
    @property
    def steps(self) -> list[PlanStep]: ...


class PlanStep(Protocol):
    @property
    def step_id(self) -> str: ...
    @property
    def file_path(self) -> str: ...
    @property
    def pattern_id(self) -> str: ...
    @property
    def depends_on(self) -> list[str]: ...


class PatternEngine(Protocol):
    async def apply_pattern(self, pattern_id: str, content: str) -> str: ...


class FileSystem(Protocol):
    async def read_file(self, path: str) -> str: ...
    async def write_file(self, path: str, content: str) -> None: ...
    async def copy_file(self, src: str, dst: str) -> None: ...


class DiffEngine(Protocol):
    async def compute_diff(self, original: str, modified: str, path: str) -> list[DiffHunkRaw]: ...


class DiffHunkRaw(Protocol):
    @property
    def start_line(self) -> int: ...
    @property
    def end_line(self) -> int: ...
    @property
    def original_text(self) -> str: ...
    @property
    def modified_text(self) -> str: ...
    @property
    def context(self) -> str: ...


class EventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------

class ApplyTransformationUseCase:
    """Apply pattern transforms file-by-file, respecting dependency ordering, and produce diffs."""

    def __init__(
        self,
        plan_store: PlanStore,
        pattern_engine: PatternEngine,
        fs: FileSystem,
        diff_engine: DiffEngine,
        event_bus: EventPublisher | None = None,
    ) -> None:
        self._plan_store = plan_store
        self._pattern_engine = pattern_engine
        self._fs = fs
        self._diff_engine = diff_engine
        self._event_bus = event_bus

    async def execute(self, request: TransformRequest) -> TransformResult:
        plan = await self._plan_store.get_plan(request.plan_id)
        if plan is None:
            return TransformResult(plan_id=request.plan_id, success=False, errors=[f"Plan {request.plan_id!r} not found."])

        await self._emit({"type": "TransformStarted", "plan_id": request.plan_id})

        # Filter to requested steps.
        steps = plan.steps
        if request.step_ids:
            wanted = set(request.step_ids)
            steps = [s for s in steps if s.step_id in wanted]

        # Topological ordering: process steps whose dependencies are satisfied first.
        completed: set[str] = set()
        ordered = self._topological_sort(steps)

        applied: list[str] = []
        diffs: list[DiffResult] = []
        errors: list[str] = []
        modified_files: set[str] = set()

        for step in ordered:
            unsatisfied = [d for d in step.depends_on if d not in completed]
            if unsatisfied:
                errors.append(f"Step {step.step_id}: unsatisfied deps {unsatisfied}")
                continue

            try:
                diff = await self._apply_step(step, request.dry_run, request.backup)
                if diff is not None:
                    diffs.append(diff)
                    modified_files.add(step.file_path)
                applied.append(step.step_id)
                completed.add(step.step_id)
            except Exception as exc:
                errors.append(f"Step {step.step_id}: {exc}")

        await self._emit({"type": "TransformCompleted", "plan_id": request.plan_id, "applied": len(applied)})

        return TransformResult(
            plan_id=request.plan_id,
            applied_steps=applied,
            diffs=diffs,
            files_modified=len(modified_files),
            success=len(errors) == 0,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _apply_step(self, step: PlanStep, dry_run: bool, backup: bool) -> DiffResult | None:
        original = await self._fs.read_file(step.file_path)
        modified = await self._pattern_engine.apply_pattern(step.pattern_id, original)

        if original == modified:
            return None

        hunks_raw = await self._diff_engine.compute_diff(original, modified, step.file_path)
        hunks = [
            HunkDTO(
                start_line=h.start_line,
                end_line=h.end_line,
                original_text=h.original_text,
                modified_text=h.modified_text,
                context=h.context,
            )
            for h in hunks_raw
        ]

        if not dry_run:
            if backup:
                await self._fs.copy_file(step.file_path, step.file_path + ".bak")
            await self._fs.write_file(step.file_path, modified)

        return DiffResult(
            file_path=step.file_path,
            original_hash=hashlib.sha256(original.encode()).hexdigest()[:16],
            modified_hash=hashlib.sha256(modified.encode()).hexdigest()[:16],
            hunks=hunks,
        )

    @staticmethod
    def _topological_sort(steps: list[PlanStep]) -> list[PlanStep]:
        """Kahn's algorithm for topological ordering."""
        step_map = {s.step_id: s for s in steps}
        in_degree: dict[str, int] = {s.step_id: 0 for s in steps}
        for s in steps:
            for dep in s.depends_on:
                if dep in in_degree:
                    in_degree[s.step_id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        ordered: list[PlanStep] = []

        while queue:
            sid = queue.pop(0)
            ordered.append(step_map[sid])
            for s in steps:
                if sid in s.depends_on:
                    in_degree[s.step_id] -= 1
                    if in_degree[s.step_id] == 0:
                        queue.append(s.step_id)

        # Append any remaining (cyclic) steps at the end with a warning.
        remaining = [s for s in steps if s.step_id not in {o.step_id for o in ordered}]
        ordered.extend(remaining)
        return ordered

    async def _emit(self, event: object) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)
