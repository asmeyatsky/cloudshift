"""Rust-backed pattern engine adapter implementing PatternEnginePort."""

from __future__ import annotations

from cloudshift.domain.entities.pattern import Pattern
from cloudshift.domain.value_objects.types import Language

import cloudshift.cloudshift_core as core


_LANG_MAP: dict[Language, str] = {
    Language.PYTHON: "python",
    Language.TYPESCRIPT: "typescript",
    Language.HCL: "hcl",
    Language.CLOUDFORMATION: "cloudformation",
}


class RustPatternEngineAdapter:
    """Implements PatternEnginePort by delegating to the Rust core.

    Protocol methods:
        match(source, patterns, language) -> list[tuple[Pattern, int, int]]
        apply(source, pattern, language) -> str
    """

    def __init__(self, parser: object | None = None) -> None:
        self._parser = parser
        self._loaded = False

    def _get_parser(self):
        if self._parser is None:
            from cloudshift.infrastructure.rust_adapters.parser_adapter import RustParserAdapter

            self._parser = RustParserAdapter()
        return self._parser

    def load_patterns(self, patterns_dir: str) -> int:
        """Load pattern rules into the Rust global catalogue."""
        count = core.py_load_patterns(patterns_dir)
        self._loaded = True
        return count

    def match(
        self,
        source: str,
        patterns: list[Pattern],
        language: Language,
    ) -> list[tuple[Pattern, int, int]]:
        parser = self._get_parser()
        constructs = parser.extract_constructs(source, language)
        lang_str = _LANG_MAP.get(language, language.name.lower())
        matches: list[tuple[Pattern, int, int]] = []

        for node_dict in constructs:
            for pattern in patterns:
                result = core.py_match_and_transform(
                    node_dict["node_type"],
                    node_dict["name"],
                    node_dict["text"],
                    pattern.source_provider.name.lower(),
                    pattern.source_service,
                    lang_str,
                    node_dict.get("metadata", {}),
                )
                if result is not None:
                    matches.append((
                        pattern,
                        node_dict["start_line"],
                        node_dict["end_line"],
                    ))
        return matches

    def apply(
        self,
        source: str,
        pattern: Pattern,
        language: Language,
    ) -> str:
        parser = self._get_parser()
        constructs = parser.extract_constructs(source, language)
        lang_str = _LANG_MAP.get(language, language.name.lower())
        modified = source

        for node_dict in constructs:
            result = core.py_match_and_transform(
                node_dict["node_type"],
                node_dict["name"],
                node_dict["text"],
                pattern.source_provider.name.lower(),
                pattern.source_service,
                lang_str,
                node_dict.get("metadata", {}),
            )
            if result is not None:
                modified = modified.replace(
                    result.original_text, result.transformed_text
                )
        return modified

    def match_and_transform(
        self,
        node_type: str,
        node_name: str,
        node_text: str,
        provider: str,
        service: str,
        language: str,
        metadata: dict[str, str] | None = None,
    ) -> dict | None:
        """Raw single-node match+transform (convenience, not part of the port)."""
        result = core.py_match_and_transform(
            node_type, node_name, node_text,
            provider, service, language,
            metadata or {},
        )
        if result is None:
            return None
        return {
            "pattern_id": result.pattern_id,
            "original_text": result.original_text,
            "transformed_text": result.transformed_text,
            "import_additions": list(result.import_additions),
            "import_removals": list(result.import_removals),
            "confidence": result.confidence,
            "metadata": dict(result.metadata),
        }
