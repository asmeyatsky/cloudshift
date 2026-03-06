"""Local YAML-directory pattern store implementing PatternStorePort."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from cloudshift.domain.entities.pattern import Pattern
from cloudshift.domain.value_objects.types import CloudProvider, ConfidenceScore, Language


_PROVIDER_MAP: dict[str, CloudProvider] = {
    "aws": CloudProvider.AWS,
    "azure": CloudProvider.AZURE,
    "gcp": CloudProvider.GCP,
}

_LANGUAGE_MAP: dict[str, Language] = {
    "python": Language.PYTHON,
    "typescript": Language.TYPESCRIPT,
    "hcl": Language.HCL,
    "cloudformation": Language.CLOUDFORMATION,
}


class LocalPatternStore:
    """Implements PatternStorePort by reading YAML pattern files from a directory.

    Protocol methods:
        get(pattern_id) -> Pattern | None
        list_all(*, source_provider, target_provider, language) -> list[Pattern]
        save(pattern) -> None
        delete(pattern_id) -> None
    """

    def __init__(self, directory: str | Path | None = None) -> None:
        self._patterns: dict[str, Pattern] = {}
        if directory is not None:
            self.load_all(str(directory))

    def load_all(self, directory: str) -> list[Pattern]:
        """Recursively load YAML pattern files from *directory*."""
        root = Path(directory)
        if not root.is_dir():
            return []
        loaded: list[Pattern] = []
        for yaml_file in sorted(root.rglob("*.y*ml")):
            try:
                patterns = self._parse_yaml(yaml_file)
                for p in patterns:
                    self._patterns[p.id] = p
                    loaded.append(p)
            except Exception:
                continue
        return loaded

    def get(self, pattern_id: str) -> Pattern | None:
        return self._patterns.get(pattern_id)

    def list_all(
        self,
        *,
        source_provider: CloudProvider | None = None,
        target_provider: CloudProvider | None = None,
        language: Language | None = None,
    ) -> list[Pattern]:
        results: list[Pattern] = []
        for p in self._patterns.values():
            if source_provider and p.source_provider != source_provider:
                continue
            if target_provider and p.target_provider != target_provider:
                continue
            if language and p.language != language:
                continue
            results.append(p)
        return results

    def save(self, pattern: Pattern) -> None:
        self._patterns[pattern.id] = pattern

    def delete(self, pattern_id: str) -> None:
        self._patterns.pop(pattern_id, None)

    def find_by_id(self, pattern_id: str) -> Pattern | None:
        """Alias for get()."""
        return self.get(pattern_id)

    def find_by_service(self, provider: str, service: str) -> list[Pattern]:
        """Find patterns matching a specific provider and service."""
        prov = _PROVIDER_MAP.get(provider.lower())
        return [
            p for p in self._patterns.values()
            if p.source_provider == prov and p.source_service == service
        ]

    @staticmethod
    def _parse_yaml(path: Path) -> list[Pattern]:
        """Parse a YAML file into one or more Pattern entities."""
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return []
        items: list[dict[str, Any]] = data if isinstance(data, list) else [data]
        patterns: list[Pattern] = []
        for item in items:
            try:
                patterns.append(_dict_to_pattern(item))
            except (KeyError, ValueError):
                continue
        return patterns


def _dict_to_pattern(d: dict[str, Any]) -> Pattern:
    return Pattern(
        id=d["id"],
        name=d.get("name", d["id"]),
        description=d.get("description", ""),
        source_provider=_PROVIDER_MAP[d["source_provider"].lower()],
        source_service=d["source_service"],
        target_provider=_PROVIDER_MAP[d["target_provider"].lower()],
        target_service=d["target_service"],
        language=_LANGUAGE_MAP[d["language"].lower()],
        match_pattern=d.get("match_pattern", ""),
        transform_spec=d.get("transform_spec", {}),
        confidence=ConfidenceScore(d.get("confidence", 0.5)),
        tags=d.get("tags", []),
    )
