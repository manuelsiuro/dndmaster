from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class SessionEventBroker:
    """In-memory pub/sub for per-session realtime updates."""

    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def subscribe(self, session_id: str) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        async with self._lock:
            self._queues[session_id].add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                listeners = self._queues.get(session_id)
                if listeners is not None:
                    listeners.discard(queue)
                    if not listeners:
                        self._queues.pop(session_id, None)

    async def publish(self, session_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            listeners = list(self._queues.get(session_id, ()))
        for queue in listeners:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop newest payload only for a saturated consumer.
                continue
