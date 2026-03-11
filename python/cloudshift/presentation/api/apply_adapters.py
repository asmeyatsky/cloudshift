"""
API-facing adapters for the Apply use case.

ApplyTransformationUseCase expects async read_file/write_file/copy_file (str paths)
and async compute_diff. Infrastructure provides sync LocalFileSystem and sync
RustDiffAdapter. These wrappers run sync in asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


class AsyncApplyFs:
    """Wraps sync file_system so Apply can await read_file/write_file/copy_file (str)."""

    def __init__(self, fs: Any) -> None:
        self._fs = fs

    async def read_file(self, path: str) -> str:
        return await asyncio.to_thread(self._fs.read, Path(path))

    async def write_file(self, path: str, content: str) -> None:
        await asyncio.to_thread(self._fs.write, Path(path), content)

    async def copy_file(self, src: str, dst: str) -> None:
        await asyncio.to_thread(self._fs.copy_file, Path(src), Path(dst))


class AsyncDiffEngineAdapter:
    """Wraps sync diff engine so Apply can await compute_diff."""

    def __init__(self, diff: Any) -> None:
        self._diff = diff

    async def compute_diff(self, original: str, modified: str, path: str) -> list[Any]:
        return await asyncio.to_thread(
            self._diff.compute_diff, original, modified
        )
