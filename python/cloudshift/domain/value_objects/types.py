"""Domain value objects: enums, scores, and lightweight data carriers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CloudProvider(str, Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"


class Language(str, Enum):
    PYTHON = "PYTHON"
    TYPESCRIPT = "TYPESCRIPT"
    HCL = "HCL"
    CLOUDFORMATION = "CLOUDFORMATION"


class TransformationStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class ProjectStatus(Enum):
    CREATED = auto()
    SCANNING = auto()
    SCANNED = auto()
    TRANSFORMING = auto()
    TRANSFORMED = auto()
    VALIDATING = auto()
    VALIDATED = auto()
    COMPLETED = auto()
    FAILED = auto()


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """A confidence value clamped to [0.0, 1.0]."""

    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", max(0.0, min(1.0, float(self.value))))

    def __float__(self) -> float:
        return self.value

    def __lt__(self, other: ConfidenceScore) -> bool:
        return self.value < other.value

    def __le__(self, other: ConfidenceScore) -> bool:
        return self.value <= other.value


@dataclass(frozen=True, slots=True)
class ServiceMapping:
    """Maps a service identifier from one cloud provider to another."""

    source_provider: CloudProvider
    source_service: str
    target_provider: CloudProvider
    target_service: str


@dataclass(frozen=True, slots=True)
class DiffHunk:
    """Represents a single hunk in a unified diff."""

    file_path: str
    start_line: int
    end_line: int
    original_text: str
    modified_text: str
    context: str = ""


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single issue discovered during validation."""

    message: str
    severity: Severity
    file_path: str | None = None
    line: int | None = None
    rule: str | None = None
