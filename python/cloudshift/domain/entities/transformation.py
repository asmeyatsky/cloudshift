"""Transformation entity -- the result of applying a pattern to source code."""

from __future__ import annotations

from dataclasses import dataclass, field

from cloudshift.domain.value_objects.types import ConfidenceScore, TransformationStatus


@dataclass(slots=True)
class Transformation:
    """Tracks the transformation of a single file or code fragment."""

    file_path: str
    original_text: str
    transformed_text: str
    pattern_id: str
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.0))
    status: TransformationStatus = TransformationStatus.PENDING
    diagnostics: list[str] = field(default_factory=list)

    def mark_completed(self, text: str, confidence: ConfidenceScore) -> None:
        self.transformed_text = text
        self.confidence = confidence
        self.status = TransformationStatus.COMPLETED

    def mark_failed(self, reason: str) -> None:
        self.status = TransformationStatus.FAILED
        self.diagnostics.append(reason)
