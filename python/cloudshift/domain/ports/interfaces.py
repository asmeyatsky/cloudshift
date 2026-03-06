"""Port definitions (Protocol interfaces) for the domain layer.

Infrastructure adapters implement these protocols; the domain and application
layers depend only on the abstractions defined here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cloudshift.domain.entities.manifest import MigrationManifest
from cloudshift.domain.entities.pattern import Pattern
from cloudshift.domain.entities.transformation import Transformation
from cloudshift.domain.entities.validation_report import ValidationReport
from cloudshift.domain.events.base import DomainEvent
from cloudshift.domain.value_objects.types import (
    CloudProvider,
    ConfidenceScore,
    DiffHunk,
    Language,
)


# ---------------------------------------------------------------------------
# Source-code analysis ports
# ---------------------------------------------------------------------------

@runtime_checkable
class ParserPort(Protocol):
    """Parses source files into an intermediate representation."""

    def parse(self, source: str, language: Language) -> dict[str, Any]: ...

    def extract_constructs(
        self, source: str, language: Language,
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class DetectorPort(Protocol):
    """Detects cloud-provider constructs in source code."""

    def detect(
        self, source: str, language: Language,
    ) -> list[tuple[str, int, int]]: ...

    def detect_provider(self, source: str) -> CloudProvider | None: ...


@runtime_checkable
class PatternEnginePort(Protocol):
    """Matches patterns against source code and applies transformations."""

    def match(
        self, source: str, patterns: list[Pattern], language: Language,
    ) -> list[tuple[Pattern, int, int]]: ...

    def apply(
        self, source: str, pattern: Pattern, language: Language,
    ) -> str: ...


# ---------------------------------------------------------------------------
# Diff / merge port
# ---------------------------------------------------------------------------

@runtime_checkable
class DiffPort(Protocol):
    """Computes and applies unified diffs."""

    def compute_diff(self, original: str, modified: str) -> list[DiffHunk]: ...

    def apply_diff(self, original: str, hunks: list[DiffHunk]) -> str: ...


# ---------------------------------------------------------------------------
# LLM port
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMPort(Protocol):
    """Facade for large-language-model interactions."""

    async def complete(self, prompt: str, **kwargs: Any) -> str: ...

    async def transform_code(
        self,
        source: str,
        instruction: str,
        language: Language,
    ) -> str: ...

    async def assess_confidence(
        self,
        original: str,
        transformed: str,
    ) -> ConfidenceScore: ...


# ---------------------------------------------------------------------------
# Persistence ports
# ---------------------------------------------------------------------------

@runtime_checkable
class PatternStorePort(Protocol):
    """CRUD access to the pattern catalogue."""

    def get(self, pattern_id: str) -> Pattern | None: ...

    def list_all(
        self,
        *,
        source_provider: CloudProvider | None = None,
        target_provider: CloudProvider | None = None,
        language: Language | None = None,
    ) -> list[Pattern]: ...

    def save(self, pattern: Pattern) -> None: ...

    def delete(self, pattern_id: str) -> None: ...


@runtime_checkable
class FileSystemPort(Protocol):
    """Abstraction over file-system operations."""

    def read(self, path: Path) -> str: ...

    def write(self, path: Path, content: str) -> None: ...

    def list_files(
        self, root: Path, patterns: list[str] | None = None,
    ) -> list[Path]: ...

    def exists(self, path: Path) -> bool: ...


# ---------------------------------------------------------------------------
# Validation port
# ---------------------------------------------------------------------------

@runtime_checkable
class ValidationPort(Protocol):
    """Runs validation checks on transformed code."""

    def validate_syntax(self, source: str, language: Language) -> ValidationReport: ...

    def validate_transformation(
        self, transformation: Transformation,
    ) -> ValidationReport: ...

    def validate_manifest(self, manifest: MigrationManifest) -> ValidationReport: ...


# ---------------------------------------------------------------------------
# Embedding port
# ---------------------------------------------------------------------------

@runtime_checkable
class EmbeddingPort(Protocol):
    """Generates vector embeddings for semantic search."""

    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    async def similarity(self, a: str, b: str) -> float: ...


# ---------------------------------------------------------------------------
# Event bus port
# ---------------------------------------------------------------------------

@runtime_checkable
class EventBusPort(Protocol):
    """Publishes and subscribes to domain events."""

    def publish(self, event: DomainEvent) -> None: ...

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Any,
    ) -> None: ...
