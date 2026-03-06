"""Simple in-memory event bus implementing EventBusPort."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type alias for event handlers.
AsyncHandler = Callable[[Any], Coroutine[Any, Any, None]]
SyncHandler = Callable[[Any], None]
Handler = AsyncHandler | SyncHandler


class EventDispatcher:
    """In-memory publish/subscribe event bus.

    Supports both sync and async handlers. Handlers are matched by event type
    string (``event["type"]`` for dicts, or ``type(event).__name__`` for objects).

    This class satisfies the ``EventBusPort`` protocol expected by use cases::

        dispatcher = EventDispatcher()
        dispatcher.subscribe("ScanStarted", my_handler)
        await dispatcher.publish({"type": "ScanStarted", "project_id": "abc"})
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._global_handlers: list[Handler] = []

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Register a handler that receives every event."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        """Remove a handler for a specific event type."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, event: Any) -> None:
        """Dispatch *event* to all matching handlers.

        The event type is resolved as:
        - ``event["type"]`` if the event is a dict with a ``"type"`` key
        - ``type(event).__name__`` otherwise
        """
        event_type = self._resolve_type(event)
        handlers = list(self._handlers.get(event_type, [])) + list(self._global_handlers)

        if not handlers:
            return

        tasks: list[Coroutine[Any, Any, None]] = []
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    tasks.append(result)
            except Exception:
                logger.exception("Sync handler %r failed for event %r", handler, event_type)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.exception("Async handler failed for event %r: %s", event_type, r)

    def publish_sync(self, event: Any) -> None:
        """Dispatch *event* synchronously (only invokes sync handlers)."""
        event_type = self._resolve_type(event)
        handlers = list(self._handlers.get(event_type, [])) + list(self._global_handlers)

        for handler in handlers:
            try:
                result = handler(event)
                # If the handler is async, we can't await it here; log a warning.
                if asyncio.iscoroutine(result):
                    result.close()
                    logger.warning("Async handler %r skipped during sync publish.", handler)
            except Exception:
                logger.exception("Handler %r failed for event %r", handler, event_type)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def handler_count(self) -> int:
        """Total number of registered handlers (type-specific + global)."""
        return sum(len(h) for h in self._handlers.values()) + len(self._global_handlers)

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
        self._global_handlers.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_type(event: Any) -> str:
        if isinstance(event, dict) and "type" in event:
            return event["type"]
        return type(event).__name__
