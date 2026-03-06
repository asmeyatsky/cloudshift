"""Local filesystem adapter implementing FileSystemPort."""

from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path


class LocalFileSystem:
    """Implements FileSystemPort with plain Python pathlib/shutil operations.

    Use this when Rust walker is not needed (e.g., for targeted file I/O
    without the gitignore-aware directory walk).

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
        if not root.is_dir():
            return []
        all_files = sorted(f for f in root.rglob("*") if f.is_file())
        if patterns:
            return [
                f for f in all_files
                if any(f.match(p) for p in patterns)
            ]
        return all_files

    def exists(self, path: Path) -> bool:
        return path.exists()

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy a file, creating parent directories as needed."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def remove(self, path: Path) -> bool:
        """Remove a file if it exists."""
        if path.is_file():
            path.unlink()
            return True
        return False

    def mkdir(self, path: Path) -> None:
        """Create a directory and parents."""
        path.mkdir(parents=True, exist_ok=True)
