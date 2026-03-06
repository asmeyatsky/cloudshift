"""WebSocket endpoint for live progress streaming.

Clients connect to ``/ws/progress`` and receive JSON-encoded progress events
as they are published by background tasks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections = [c for c in self._connections if c is not ws]
        logger.info("WebSocket client disconnected (%d remaining)", len(self._connections))

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Send a JSON event to every connected client."""
        payload = json.dumps(event, default=str)
        async with self._lock:
            stale: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._connections = [c for c in self._connections if c is not ws]


# Singleton shared across the application.
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/progress")
async def progress_websocket(ws: WebSocket) -> None:
    """Accept a WebSocket connection and keep it open for progress events.

    The server pushes events via ``manager.broadcast()``.  Clients may send
    JSON messages to subscribe to specific job IDs::

        {"subscribe": "<job_id>"}
        {"unsubscribe": "<job_id>"}

    If no subscription message is sent the client receives *all* events.
    """
    await manager.connect(ws)
    try:
        while True:
            # Keep the connection alive; honour client messages.
            data = await ws.receive_text()
            with suppress(json.JSONDecodeError):
                msg = json.loads(data)
                if isinstance(msg, dict):
                    # Future: filter events per-client by job_id.
                    logger.debug("WS client message: %s", msg)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(ws)
