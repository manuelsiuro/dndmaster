from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import WebSocket


class VoiceConnectionRegistry:
    """Tracks active voice websocket connections for moderation actions."""

    def __init__(self) -> None:
        self._sockets: dict[str, dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def register(
        self,
        session_id: str,
        user_id: str,
        websocket: WebSocket,
    ) -> AsyncIterator[None]:
        async with self._lock:
            self._sockets[session_id][user_id].add(websocket)
        try:
            yield
        finally:
            async with self._lock:
                room = self._sockets.get(session_id)
                if room is not None:
                    user_sockets = room.get(user_id)
                    if user_sockets is not None:
                        user_sockets.discard(websocket)
                        if not user_sockets:
                            room.pop(user_id, None)
                    if not room:
                        self._sockets.pop(session_id, None)

    async def close_user_connections(
        self,
        session_id: str,
        user_id: str,
        *,
        code: int = 4408,
        reason: str = "Voice connection closed by host",
    ) -> None:
        async with self._lock:
            room = self._sockets.get(session_id, {})
            sockets = list(room.get(user_id, ()))

        for websocket in sockets:
            with suppress(RuntimeError):
                await websocket.close(code=code, reason=reason)
