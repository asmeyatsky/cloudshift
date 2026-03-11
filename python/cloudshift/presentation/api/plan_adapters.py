"""
API-facing adapters for the Plan use case.

GeneratePlanUseCase expects pattern_engine.match_patterns(file_path, services,
source_provider, target_provider) async. This adapter reads the file, loads
patterns from the store, and calls the Rust engine.match(source, patterns, language).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cloudshift.domain.value_objects.types import CloudProvider, Language


def _infer_language_from_path(file_path: str) -> Language:
    ext = (file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "")
    if ext in ("py",):
        return Language.PYTHON
    if ext in ("ts", "tsx", "js", "jsx"):
        return Language.TYPESCRIPT
    if ext in ("tf", "hcl"):
        return Language.HCL
    if ext in ("json", "yml", "yaml"):
        return Language.CLOUDFORMATION  # CloudFormation / ARM-like; engine may match CF patterns
    return Language.PYTHON  # fallback


class PlanPatternEngineAdapter:
    """Exposes async match_patterns: reads file, loads patterns, runs Rust engine.match."""

    def __init__(
        self,
        *,
        pattern_store: Any,
        walker: Any,
        pattern_engine: Any,
    ) -> None:
        self._pattern_store = pattern_store
        self._walker = walker
        self._pattern_engine = pattern_engine

    async def match_patterns(
        self,
        file_path: str,
        services: list[str],
        source_provider: str,
        target_provider: str,
    ) -> list[Any]:
        try:
            content = await asyncio.to_thread(
                self._walker.read, Path(file_path)
            )
        except Exception:
            return []
        try:
            src = (source_provider.upper() if isinstance(source_provider, str) else source_provider.name)
            tgt = (target_provider.upper() if isinstance(target_provider, str) else target_provider.name)
            source_prov = CloudProvider[src]
            target_prov = CloudProvider[tgt]
        except (KeyError, TypeError, AttributeError):
            return []
        language = _infer_language_from_path(file_path)
        patterns = self._pattern_store.list_all(
            source_provider=source_prov,
            target_provider=target_prov,
            language=language,
        )
        services_lower = [s.lower() for s in services]
        patterns = [p for p in patterns if p.source_service.lower() in services_lower]
        if not patterns:
            return []
        try:
            matches = await asyncio.to_thread(
                self._pattern_engine.match,
                content,
                patterns,
                language,
            )
        except Exception:
            return []
        out = []
        for pattern, _line_start, _line_end in matches:
            out.append(
                SimpleNamespace(
                    pattern_id=pattern.id,
                    description=pattern.description or pattern.name,
                    confidence=pattern.confidence,
                )
            )
        return out


class PlanStoreAdapter:
    """Exposes async get_plan(plan_id) for ApplyTransformationUseCase."""

    def __init__(self) -> None:
        from cloudshift.presentation.api.plan_store import get_plan as _get_plan
        self._get_plan = _get_plan

    async def get_plan(self, plan_id: str) -> Any:
        return await self._get_plan(plan_id)
