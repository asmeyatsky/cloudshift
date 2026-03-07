"""Rust-backed diff adapter implementing DiffPort."""

from __future__ import annotations

from cloudshift.domain.value_objects.types import DiffHunk
from cloudshift.infrastructure.rust_adapters.detector_adapter import _dict_to_py_node

import cloudshift.cloudshift_core as core


class RustDiffAdapter:
    """Implements DiffPort by delegating to the Rust core.

    Protocol methods:
        compute_diff(original, modified) -> list[DiffHunk]
        apply_diff(original, hunks) -> str
    """

    def compute_diff(self, original: str, modified: str) -> list[DiffHunk]:
        raw = core.py_unified_diff(original, modified, "<diff>")
        if not raw.strip():
            return []
        return self._parse_unified_diff(raw, original, modified)

    def apply_diff(self, original: str, hunks: list[DiffHunk]) -> str:
        lines = original.splitlines(keepends=True)
        # Apply hunks in reverse order to preserve line numbers.
        for hunk in sorted(hunks, key=lambda h: h.start_line, reverse=True):
            start = hunk.start_line - 1
            end = hunk.end_line
            replacement = hunk.modified_text.splitlines(keepends=True)
            lines[start:end] = replacement
        return "".join(lines)

    def unified_diff(self, old_text: str, new_text: str, file_path: str) -> str:
        """Raw unified diff string (convenience, not part of the port)."""
        return core.py_unified_diff(old_text, new_text, file_path)

    def ast_diff(
        self,
        old_nodes: list[dict],
        new_nodes: list[dict],
        file_path: str,
    ) -> list[dict[str, str]]:
        """Structural AST diff (convenience, not part of the port)."""
        py_old = [_dict_to_py_node(n) for n in old_nodes]
        py_new = [_dict_to_py_node(n) for n in new_nodes]
        return core.py_ast_diff(py_old, py_new, file_path)

    @staticmethod
    def _parse_unified_diff(raw: str, original: str, modified: str) -> list[DiffHunk]:
        """Parse unified diff output into DiffHunk value objects."""
        hunks: list[DiffHunk] = []
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)

        current_old_start = 0
        current_old_count = 0
        current_new_start = 0
        current_new_count = 0
        in_hunk = False

        for line in raw.splitlines():
            if line.startswith("@@"):
                if in_hunk:
                    hunks.append(_build_hunk(
                        current_old_start, current_old_count,
                        orig_lines, mod_lines,
                        current_new_start, current_new_count,
                    ))
                parts = line.split()
                old_range = parts[1].lstrip("-").split(",")
                new_range = parts[2].lstrip("+").split(",")
                current_old_start = int(old_range[0])
                current_old_count = int(old_range[1]) if len(old_range) > 1 else 1
                current_new_start = int(new_range[0])
                current_new_count = int(new_range[1]) if len(new_range) > 1 else 1
                in_hunk = True

        if in_hunk:
            hunks.append(_build_hunk(
                current_old_start, current_old_count,
                orig_lines, mod_lines,
                current_new_start, current_new_count,
            ))
        return hunks


def _build_hunk(
    old_start: int,
    old_count: int,
    orig_lines: list[str],
    mod_lines: list[str],
    new_start: int,
    new_count: int,
) -> DiffHunk:
    s = old_start - 1
    e = s + old_count
    original_text = "".join(orig_lines[s:e])
    ns = new_start - 1
    ne = ns + new_count
    modified_text = "".join(mod_lines[ns:ne])
    return DiffHunk(
        file_path="<diff>",
        start_line=old_start,
        end_line=old_start + old_count - 1,
        original_text=original_text,
        modified_text=modified_text,
    )
