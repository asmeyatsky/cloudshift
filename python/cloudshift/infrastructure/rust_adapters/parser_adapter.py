"""Rust-backed parser adapter implementing ParserPort."""

from __future__ import annotations

from typing import Any

from cloudshift.domain.value_objects.types import Language

import cloudshift.cloudshift_core as core


_LANG_MAP: dict[Language, str] = {
    Language.PYTHON: "python",
    Language.TYPESCRIPT: "typescript",
    Language.HCL: "hcl",
    Language.CLOUDFORMATION: "cloudformation",
}


def _py_ast_to_dict(py_ast: core.PyFileAst) -> dict[str, Any]:
    """Convert a PyO3 PyFileAst to a plain dictionary."""
    return {
        "file_path": py_ast.file_path,
        "language": py_ast.language,
        "nodes": [_py_node_to_dict(n) for n in py_ast.nodes],
    }


def _py_node_to_dict(py_node: core.PyAstNode) -> dict[str, Any]:
    """Convert a PyO3 PyAstNode to a plain dictionary."""
    return {
        "node_type": py_node.node_type,
        "name": py_node.name,
        "text": py_node.text,
        "start_line": py_node.start_line,
        "end_line": py_node.end_line,
        "start_col": py_node.start_col,
        "end_col": py_node.end_col,
        "children": [_py_node_to_dict(c) for c in py_node.children],
        "metadata": dict(py_node.metadata),
    }


class RustParserAdapter:
    """Implements ParserPort by delegating to the Rust core.

    Protocol methods:
        parse(source, language) -> dict
        extract_constructs(source, language) -> list[dict]

    Additional Rust-specific helpers:
        parse_file(path) -> dict
    """

    def parse(self, source: str, language: Language) -> dict[str, Any]:
        lang_str = _LANG_MAP.get(language, language.name.lower())
        py_ast = core.parse_source(source, lang_str, "<inline>")
        return _py_ast_to_dict(py_ast)

    def extract_constructs(
        self, source: str, language: Language,
    ) -> list[dict[str, Any]]:
        lang_str = _LANG_MAP.get(language, language.name.lower())
        py_ast = core.parse_source(source, lang_str, "<inline>")
        return [_py_node_to_dict(n) for n in py_ast.nodes]

    def parse_file(self, path: str) -> dict[str, Any]:
        """Parse a file on disk (convenience, not part of the port)."""
        py_ast = core.parse_file(path)
        return _py_ast_to_dict(py_ast)

    def parse_source(self, source: str, language: str, file_path: str) -> dict[str, Any]:
        """Parse source with string language name (convenience, not part of the port)."""
        py_ast = core.parse_source(source, language, file_path)
        return _py_ast_to_dict(py_ast)
