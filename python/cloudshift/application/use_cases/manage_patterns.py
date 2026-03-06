"""Use case: manage migration patterns (CRUD + search)."""

from __future__ import annotations

import inspect
from typing import Protocol

from cloudshift.application.dtos.pattern import PatternDTO
from cloudshift.domain.value_objects.types import CloudProvider, Language


class PatternStore(Protocol):
    def list_all(self) -> list: ...
    def get_by_id(self, pattern_id: str): ...
    def add(self, pattern) -> str: ...
    def delete(self, pattern_id: str) -> bool: ...


class ManagePatternsUseCase:
    """List, get, add, and search migration patterns."""

    def __init__(
        self,
        pattern_store: PatternStore,
        embedding_search=None,
    ) -> None:
        self._store = pattern_store
        self._search = embedding_search

    async def _call(self, method, *args, **kwargs):
        """Call a method, handling both sync and async implementations."""
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def list_patterns(self) -> list[PatternDTO]:
        stored = await self._call(self._store.list_all)
        return [self._to_dto(p) for p in stored]

    async def get_pattern(self, pattern_id: str) -> PatternDTO | None:
        p = await self._call(self._store.get_by_id, pattern_id)
        return self._to_dto(p) if p is not None else None

    async def add_pattern(self, dto: PatternDTO) -> str:
        return await self._call(self._store.add, dto)

    async def delete_pattern(self, pattern_id: str) -> bool:
        return await self._call(self._store.delete, pattern_id)

    async def search_patterns(self, query: str = "", top_k: int = 10) -> list[PatternDTO]:
        all_patterns = await self._call(self._store.list_all)
        if not query:
            return [self._to_dto(p) for p in all_patterns][:top_k]
        q = query.lower()
        def _get(p, key):
            if isinstance(p, dict):
                return p.get(key, '')
            return getattr(p, key, '')
        return [
            self._to_dto(p)
            for p in all_patterns
            if q in _get(p, 'name').lower() or q in _get(p, 'description').lower()
        ][:top_k]

    @staticmethod
    def _to_dto(p) -> PatternDTO:
        if isinstance(p, dict):
            return PatternDTO(
                pattern_id=p.get("id", p.get("pattern_id", "")),
                name=p.get("name", ""),
                description=p.get("description", ""),
                source_provider=p.get("source_provider", ""),
                target_provider=p.get("target_provider", ""),
                language=p.get("language", ""),
                source_snippet=p.get("source_snippet", ""),
                target_snippet=p.get("target_snippet", ""),
                tags=p.get("tags", []),
                confidence=p.get("base_confidence", p.get("confidence", 0.0)),
                version=p.get("version", "1.0"),
            )
        return PatternDTO(
            pattern_id=getattr(p, 'pattern_id', getattr(p, 'id', '')),
            name=getattr(p, 'name', ''),
            description=getattr(p, 'description', ''),
            source_provider=getattr(p, 'source_provider', ''),
            target_provider=getattr(p, 'target_provider', ''),
            language=getattr(p, 'language', ''),
            source_snippet=getattr(p, 'source_snippet', ''),
            target_snippet=getattr(p, 'target_snippet', ''),
            tags=list(getattr(p, 'tags', [])),
            confidence=getattr(p, 'confidence', getattr(p, 'base_confidence', 0.0)),
            version=getattr(p, 'version', '1.0'),
        )
