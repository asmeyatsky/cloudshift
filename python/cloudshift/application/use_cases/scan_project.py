"""Use case: scan a project directory to build a migration manifest."""

from __future__ import annotations

import asyncio
import uuid
from typing import Protocol

from cloudshift.application.dtos.scan import FileEntry, ScanRequest, ScanResult
from cloudshift.domain.value_objects.types import CloudProvider, ConfidenceScore, Language


# ---------------------------------------------------------------------------
# Port protocols (structural subtyping so we don't depend on concrete ports)
# ---------------------------------------------------------------------------

class FileSystemReader(Protocol):
    """Subset of FileSystemPort needed by this use case."""

    async def list_files(self, root: str, exclude: list[str] | None = None) -> list[str]: ...
    async def read_file(self, path: str) -> str: ...


class Parser(Protocol):
    """Subset of ParserPort needed by this use case."""

    async def detect_language(self, path: str, content: str) -> Language | None: ...
    async def count_lines(self, content: str) -> int: ...


class Detector(Protocol):
    """Subset of DetectorPort needed by this use case."""

    async def detect_services(
        self, content: str, language: Language, provider: CloudProvider
    ) -> list[tuple[str, ConfidenceScore]]: ...


class EventPublisher(Protocol):
    """Subset of EventBusPort needed by this use case."""

    async def publish(self, event: object) -> None: ...


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------

class ScanProjectUseCase:
    """Walk a project directory, parse files, detect cloud services, and build a manifest."""

    def __init__(
        self,
        fs: FileSystemReader,
        parser: Parser,
        detector: Detector,
        event_bus: EventPublisher | None = None,
    ) -> None:
        self._fs = fs
        self._parser = parser
        self._detector = detector
        self._event_bus = event_bus

    async def execute(self, request: ScanRequest) -> ScanResult:
        project_id = uuid.uuid4().hex[:12]

        await self._emit({"type": "ScanStarted", "project_id": project_id, "root": request.root_path})

        try:
            paths = await self._fs.list_files(request.root_path, request.exclude_patterns or None)
        except Exception as exc:
            return ScanResult(
                project_id=project_id,
                root_path=request.root_path,
                source_provider=request.source_provider,
                target_provider=request.target_provider,
                error=str(exc),
            )

        allowed_languages = set(request.languages) if request.languages else None
        entries: list[FileEntry] = []
        all_services: set[str] = set()

        tasks = [self._scan_file(p, request.source_provider, allowed_languages) for p in paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                continue
            if result is not None:
                entries.append(result)
                all_services.update(result.services_detected)

        await self._emit(
            {"type": "ScanCompleted", "project_id": project_id, "files": len(entries)},
        )

        return ScanResult(
            project_id=project_id,
            root_path=request.root_path,
            source_provider=request.source_provider,
            target_provider=request.target_provider,
            files=entries,
            total_files_scanned=len(paths),
            services_found=sorted(all_services),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _scan_file(
        self,
        path: str,
        provider: CloudProvider,
        allowed: set[Language] | None,
    ) -> FileEntry | None:
        content = await self._fs.read_file(path)
        language = await self._parser.detect_language(path, content)

        if language is None:
            return None
        if allowed and language not in allowed:
            return None

        detections = await self._detector.detect_services(content, language, provider)
        if not detections:
            return None

        best_confidence = max((float(c) for _, c in detections), default=0.0)
        line_count = await self._parser.count_lines(content)

        return FileEntry(
            path=path,
            language=language,
            services_detected=[svc for svc, _ in detections],
            confidence=best_confidence,
            line_count=line_count,
        )

    async def _emit(self, event: object) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)
