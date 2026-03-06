"""Rust-backed file-system walker adapter implementing FileSystemPort."""

from __future__ import annotations

import shutil
from pathlib import Path

import cloudshift.cloudshift_core as core


class RustWalkerAdapter:
    """Implements FileSystemPort using the Rust core for walking and dependency analysis,
    with thin Python I/O for read/write/exists.

    Protocol methods:
        read(path) -> str
        write(path, content) -> None
        list_files(root, patterns) -> list[Path]
        exists(path) -> bool
    """

    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_files(
        self, root: Path, patterns: list[str] | None = None,
    ) -> list[Path]:
        all_files = core.walk_directory(str(root))
        paths = [Path(f) for f in all_files]
        if patterns:
            filtered: list[Path] = []
            for p in paths:
                if any(p.match(pat) for pat in patterns):
                    filtered.append(p)
            return filtered
        return paths

    def exists(self, path: Path) -> bool:
        return path.exists()

    # ---- Rust-powered extras (not part of FileSystemPort protocol) ----

    def walk_directory(self, root: str) -> list[str]:
        """Walk directory using Rust's ignore-aware walker."""
        return core.walk_directory(root)

    def build_dependency_graph(
        self, files: list[str],
    ) -> tuple[list[str], list[tuple[int, int]], list[int]]:
        """Build an import dependency graph and return topological order."""
        nodes, edges, order = core.build_dependency_graph(files)
        return nodes, [(a, b) for a, b in edges], list(order)

    def copy_file(self, src: str, dst: str) -> None:
        """Copy a file, creating parent directories as needed."""
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
