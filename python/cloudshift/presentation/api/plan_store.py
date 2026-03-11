"""
In-memory plan store so Apply can resolve get_plan(plan_id).

Plan route stores result by job_id; when plan completes we also register
by plan_id so the Apply use case can load the plan.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from cloudshift.domain.value_objects.types import Language

# plan_id -> result dict (same shape as PlanResult.model_dump())
_plan_by_id: dict[str, dict[str, Any]] = {}


def register_plan(plan_id: str, result: dict[str, Any]) -> None:
    """Call when plan job completes. result must have plan_id, steps (list of step dicts)."""
    _plan_by_id[plan_id] = result


def _get_plan_sync(plan_id: str) -> SimpleNamespace | None:
    raw = _plan_by_id.get(plan_id)
    if not raw:
        return None
    steps = []
    for s in raw.get("steps", []):
        steps.append(
            SimpleNamespace(
                step_id=s.get("step_id", ""),
                file_path=s.get("file_path", ""),
                pattern_id=s.get("pattern_id", ""),
                language=Language.PYTHON,  # step DTO has no language; default for apply
                depends_on=s.get("depends_on", []),
            )
        )
    return SimpleNamespace(
        plan_id=raw.get("plan_id", plan_id),
        project_id=raw.get("project_id", ""),
        steps=steps,
    )


async def get_plan(plan_id: str) -> SimpleNamespace | None:
    """Async for use case compatibility."""
    return await asyncio.to_thread(_get_plan_sync, plan_id)
