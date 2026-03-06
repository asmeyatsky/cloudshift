"""Domain service for calculating and combining confidence scores."""

from __future__ import annotations

from cloudshift.domain.entities.manifest import MigrationManifest
from cloudshift.domain.entities.transformation import Transformation
from cloudshift.domain.value_objects.types import ConfidenceScore


class ConfidenceCalculator:
    """Pure domain logic for confidence-score arithmetic."""

    @staticmethod
    def weighted_average(
        scores: list[tuple[ConfidenceScore, float]],
    ) -> ConfidenceScore:
        """Compute a weighted average of *(score, weight)* pairs."""
        if not scores:
            return ConfidenceScore(0.0)
        total_weight = sum(w for _, w in scores)
        if total_weight == 0.0:
            return ConfidenceScore(0.0)
        weighted = sum(s.value * w for s, w in scores) / total_weight
        return ConfidenceScore(weighted)

    @staticmethod
    def combine(a: ConfidenceScore, b: ConfidenceScore) -> ConfidenceScore:
        """Combine two independent confidence scores (geometric mean)."""
        return ConfidenceScore((a.value * b.value) ** 0.5)

    @staticmethod
    def for_transformation(transformation: Transformation) -> ConfidenceScore:
        """Return the confidence for a single transformation."""
        return transformation.confidence

    @staticmethod
    def for_manifest(manifest: MigrationManifest) -> ConfidenceScore:
        """Return the aggregate confidence for the entire manifest."""
        return manifest.overall_confidence
