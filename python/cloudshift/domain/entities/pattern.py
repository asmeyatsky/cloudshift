"""Pattern entity -- a reusable migration rule."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cloudshift.domain.value_objects.types import (
    CloudProvider,
    ConfidenceScore,
    Language,
)


@dataclass(slots=True)
class Pattern:
    """Describes how to detect and transform a specific cloud construct."""

    id: str
    name: str
    description: str
    source_provider: CloudProvider
    source_service: str
    target_provider: CloudProvider
    target_service: str
    language: Language
    match_pattern: str
    transform_spec: dict[str, Any] = field(default_factory=dict)
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.5))
    tags: list[str] = field(default_factory=list)
