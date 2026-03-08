"""Rust-backed import organizer adapter."""

from __future__ import annotations

import cloudshift.cloudshift_core as core
from cloudshift.domain.value_objects.types import Language


class RustImportOrganizerAdapter:
    """Uses Rust core to clean and deduplicate imports."""

    async def organize(self, content: str, language: Language) -> str:
        lang_str = language.name.lower()
        if language == Language.PYTHON:
             # Rust core can handle sorting and deduplicating imports
             return core.py_organize_imports(content, lang_str)
        
        # For other languages, use a basic implementation or just return as-is
        # if Rust core doesn't support them yet.
        return core.py_organize_imports(content, lang_str)
