"""
API-facing adapters so ScanProjectUseCase gets async ports with correct signatures.

Use cases expect async list_files/read_file, detect_language/count_lines, detect_services.
Infrastructure provides sync walker, parser, detector. These adapters wrap them
and run sync work in asyncio.to_thread so the use case can await correctly.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cloudshift.domain.value_objects.types import ConfidenceScore, Language


class AsyncScanFs:
    """Wraps sync walker so ScanProjectUseCase can await list_files/read_file."""

    def __init__(self, walker: Any) -> None:
        self._walker = walker

    async def list_files(self, root: str, exclude: list[str] | None = None) -> list[str]:
        paths = await asyncio.to_thread(
            self._walker.list_files, Path(root), exclude
        )
        return [str(p) for p in paths]

    async def read_file(self, path: str) -> str:
        return await asyncio.to_thread(self._walker.read, Path(path))


class AsyncScanParser:
    """Wraps sync parser so ScanProjectUseCase can await detect_language/count_lines."""

    def __init__(self, parser: Any) -> None:
        self._parser = parser

    async def detect_language(self, path: str, content: str) -> Language | None:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang_map = {
            "py": Language.PYTHON,
            "ts": Language.TYPESCRIPT,
            "tsx": Language.TYPESCRIPT,
            "js": Language.TYPESCRIPT,
            "jsx": Language.TYPESCRIPT,
            "tf": Language.HCL,
            "json": Language.CLOUDFORMATION,
            "bicep": Language.CLOUDFORMATION,
            "yml": Language.CLOUDFORMATION,
            "yaml": Language.CLOUDFORMATION,
        }
        if ext in lang_map:
            return lang_map[ext]
        for lang in (Language.PYTHON, Language.TYPESCRIPT):
            try:
                await asyncio.to_thread(self._parser.parse, content, lang)
                return lang
            except Exception:
                continue
        return None

    async def count_lines(self, content: str) -> int:
        return len(content.splitlines())


def _detect_azure_heuristic(content: str) -> list[tuple[str, float]]:
    """Heuristic Azure detection for ARM/Bicep/JSON so scan shows findings."""
    content_lower = content.lower()
    services: list[tuple[str, float]] = []
    if "microsoft." in content_lower or "azurerm" in content_lower or "resourcegroup" in content_lower:
        services.append(("arm", 0.85))
    if "microsoft.storage" in content_lower or "azurerm_storage" in content_lower or "storageaccount" in content_lower:
        services.append(("storage", 0.8))
    if "microsoft.compute" in content_lower or "azurerm_virtual_machine" in content_lower or "virtualmachine" in content_lower:
        services.append(("compute", 0.8))
    if "microsoft.web" in content_lower or "azurerm_function_app" in content_lower or "functionapp" in content_lower:
        services.append(("functions", 0.75))
    if "microsoft.documentdb" in content_lower or "azurerm_cosmosdb" in content_lower or "cosmosdb" in content_lower:
        services.append(("cosmosdb", 0.8))
    if "microsoft.eventhub" in content_lower or "azurerm_eventhub" in content_lower:
        services.append(("eventhub", 0.8))
    if "microsoft.servicebus" in content_lower or "azurerm_servicebus" in content_lower:
        services.append(("servicebus", 0.8))
    if "microsoft.insights" in content_lower or "azurerm_application_insights" in content_lower:
        services.append(("monitoring", 0.75))
    if "microsoft.keyvault" in content_lower or "azurerm_key_vault" in content_lower:
        services.append(("keyvault", 0.8))
    if "microsoft.network" in content_lower or "azurerm_virtual_network" in content_lower:
        services.append(("networking", 0.75))
    if not services and ("microsoft." in content_lower or "azurerm" in content_lower):
        services.append(("arm", 0.7))
    return services


class AsyncScanDetector:
    """Wraps sync detector so ScanProjectUseCase can await detect_services."""

    def __init__(self, detector: Any) -> None:
        self._detector = detector

    async def detect_services(
        self, content: str, language: Any, provider: Any
    ) -> list[tuple[str, ConfidenceScore]]:
        # Azure ARM/Bicep/JSON: Rust detector may not recognize; use heuristic first.
        content_lower = content.lower()
        if ("microsoft." in content_lower or "azurerm" in content_lower or "resourcegroup" in content_lower) and language == Language.CLOUDFORMATION:
            hits = _detect_azure_heuristic(content)
            return [(svc, ConfidenceScore(conf)) for svc, conf in hits]
        hits = await asyncio.to_thread(self._detector.detect, content, language)
        return [(svc, ConfidenceScore(0.9)) for svc, _a, _b in hits]
