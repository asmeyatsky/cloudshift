"""Gemini LLM adapter for demo mode (cloud API)."""

from __future__ import annotations

import logging

import httpx

from cloudshift.domain.value_objects.types import ConfidenceScore, Language

logger = logging.getLogger(__name__)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiAdapter:
    """Implements LLMPort via Google Gemini REST API.

    Used when deployment_mode=demo. Requires CLOUDSHIFT_GEMINI_API_KEY.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def _url(self) -> str:
        return f"{_BASE_URL}/models/{self._model}:generateContent?key={self._api_key}"

    async def complete(self, prompt: str, **kwargs) -> str:
        system = kwargs.pop("system", "")
        payload: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": kwargs.pop("temperature", 0.2)},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        resp = await self._client.post(self._url(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        try:
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
        except (IndexError, KeyError):
            text = ""
        if not (text or "").strip():
            # Blocked, empty, or unexpected shape - log for debugging
            logger.warning(
                "Gemini returned no text. candidates=%s",
                data.get("candidates", [])[:1],
            )
        return text or ""

    async def transform_code(
        self, source: str, instruction: str, language: Language,
    ) -> str:
        prompt = (
            f"Transform the following {language.name.lower()} code according to "
            f"this instruction:\n\n{instruction}\n\n"
            f"```{language.name.lower()}\n{source}\n```\n\n"
            "Return only the transformed code inside a code block."
        )
        response = await self.complete(
            prompt,
            system="You are an expert cloud migration engineer. Return only code.",
        )
        return _extract_code_block(response) or response

    async def assess_confidence(
        self, original: str, transformed: str,
    ) -> ConfidenceScore:
        prompt = (
            "Rate the quality of this code transformation on a scale of 0.0 to 1.0.\n\n"
            f"Original:\n```\n{original}\n```\n\n"
            f"Transformed:\n```\n{transformed}\n```\n\n"
            "Return only a decimal number between 0.0 and 1.0."
        )
        response = await self.complete(prompt, temperature=0.0)
        try:
            score = float(response.strip().split()[0])
            return ConfidenceScore(score)
        except (ValueError, IndexError):
            return ConfidenceScore(0.5)

    async def close(self) -> None:
        await self._client.aclose()


def _extract_code_block(text: str) -> str | None:
    """Extract the first fenced code block from LLM output."""
    lines = text.split("\n")
    inside = False
    code_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("```") and not inside:
            inside = True
            continue
        if line.strip().startswith("```") and inside:
            break
        if inside:
            code_lines.append(line)
    return "\n".join(code_lines) if code_lines else None
