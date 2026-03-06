"""Null LLM adapter -- returns empty/default responses (no-LLM mode)."""

from __future__ import annotations

from cloudshift.domain.value_objects.types import ConfidenceScore, Language


class NullLLMAdapter:
    """Implements LLMPort with no-op behaviour.

    Used when no LLM is configured or when running in a
    deterministic-only mode (pure pattern matching).
    """

    async def complete(self, prompt: str, **kwargs) -> str:
        return ""

    async def transform_code(
        self, source: str, instruction: str, language: Language,
    ) -> str:
        return source

    async def assess_confidence(
        self, original: str, transformed: str,
    ) -> ConfidenceScore:
        return ConfidenceScore(0.0)
