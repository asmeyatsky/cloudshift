"""Rust-backed service detector adapter implementing DetectorPort."""

from __future__ import annotations

from cloudshift.domain.value_objects.types import CloudProvider, Language

import cloudshift.cloudshift_core as core


_PROVIDER_KEYWORDS: dict[str, CloudProvider] = {
    "aws": CloudProvider.AWS,
    "azure": CloudProvider.AZURE,
    "gcp": CloudProvider.GCP,
}


def _dict_to_py_node(d: dict) -> core.PyAstNode:
    """Convert a dict (from parser adapter) to a PyO3 PyAstNode."""
    return core.PyAstNode(
        node_type=d["node_type"],
        name=d["name"],
        text=d["text"],
        start_line=d["start_line"],
        end_line=d["end_line"],
        start_col=d.get("start_col", 0),
        end_col=d.get("end_col", 0),
        children=[_dict_to_py_node(c) for c in d.get("children", [])],
        metadata=d.get("metadata", {}),
    )


class RustDetectorAdapter:
    """Implements DetectorPort by delegating to the Rust core.

    Protocol methods:
        detect(source, language) -> list[tuple[str, int, int]]
        detect_provider(source) -> CloudProvider | None
    """

    def __init__(self, parser: object | None = None) -> None:
        # Lazily import to avoid circular deps; accept an injected parser.
        self._parser = parser

    def _get_parser(self):
        if self._parser is None:
            from cloudshift.infrastructure.rust_adapters.parser_adapter import RustParserAdapter

            self._parser = RustParserAdapter()
        return self._parser

    def detect(
        self, source: str, language: Language,
    ) -> list[tuple[str, int, int]]:
        parser = self._get_parser()
        constructs = parser.extract_constructs(source, language)
        py_nodes = [_dict_to_py_node(c) for c in constructs]
        detections = core.py_detect_services(py_nodes)
        return [
            (d.service, d.start_line, d.end_line) for d in detections
        ]

    def detect_provider(self, source: str) -> CloudProvider | None:
        # Quick heuristic: try parsing as Python, then check detections.
        for lang in (Language.PYTHON, Language.TYPESCRIPT, Language.HCL):
            try:
                hits = self.detect(source, lang)
                if hits:
                    # Re-run to get provider info
                    parser = self._get_parser()
                    constructs = parser.extract_constructs(source, lang)
                    py_nodes = [_dict_to_py_node(c) for c in constructs]
                    detections = core.py_detect_services(py_nodes)
                    if detections:
                        return _PROVIDER_KEYWORDS.get(detections[0].provider)
            except Exception:
                continue
        return None

    def detect_services_raw(
        self, nodes: list[dict],
    ) -> list[dict]:
        """Return full detection dicts (convenience, not part of the port)."""
        py_nodes = [_dict_to_py_node(n) for n in nodes]
        detections = core.py_detect_services(py_nodes)
        return [
            {
                "provider": d.provider,
                "service": d.service,
                "construct_type": d.construct_type,
                "confidence": d.confidence,
                "node_name": d.node_name,
                "start_line": d.start_line,
                "end_line": d.end_line,
                "metadata": dict(d.metadata),
            }
            for d in detections
        ]
