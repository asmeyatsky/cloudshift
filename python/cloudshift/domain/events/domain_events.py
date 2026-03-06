"""Concrete domain events emitted during migration workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cloudshift.domain.events.base import DomainEvent
from cloudshift.domain.value_objects.types import ConfidenceScore


# -- Scan lifecycle ----------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ScanStarted(DomainEvent):
    project_name: str = ""
    root_path: Path = field(default_factory=lambda: Path("."))


@dataclass(frozen=True, slots=True)
class ScanCompleted(DomainEvent):
    project_name: str = ""
    files_scanned: int = 0
    patterns_matched: int = 0


# -- Transform lifecycle ----------------------------------------------------

@dataclass(frozen=True, slots=True)
class TransformStarted(DomainEvent):
    project_name: str = ""
    total_transformations: int = 0


@dataclass(frozen=True, slots=True)
class TransformCompleted(DomainEvent):
    project_name: str = ""
    succeeded: int = 0
    failed: int = 0


# -- Validation lifecycle ----------------------------------------------------

@dataclass(frozen=True, slots=True)
class ValidationStarted(DomainEvent):
    project_name: str = ""
    files_to_validate: int = 0


@dataclass(frozen=True, slots=True)
class ValidationCompleted(DomainEvent):
    project_name: str = ""
    is_valid: bool = True
    error_count: int = 0
    warning_count: int = 0


# -- Pattern events ----------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PatternMatched(DomainEvent):
    pattern_id: str = ""
    file_path: str = ""
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.0))
    line_start: int = 0
    line_end: int = 0
