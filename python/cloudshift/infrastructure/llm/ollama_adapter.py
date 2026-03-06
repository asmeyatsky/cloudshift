"""Ollama LLM adapter for air-gapped local inference."""

from __future__ import annotations

import httpx

from cloudshift.domain.value_objects.types import ConfidenceScore, Language


_DEFAULT_MODEL = "codellama:13b"
_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAdapter:
    """Implements LLMPort via a local Ollama HTTP API.

    Designed for air-gapped environments where no external network
    access is available.  Communicates with Ollama's ``/api/generate``
    and ``/api/chat`` endpoints over plain HTTP.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    async def complete(self, prompt: str, **kwargs) -> str:
        system = kwargs.pop("system", "")
        temperature = kwargs.pop("temperature", 0.2)
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        resp = await self._client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

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
