from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class VoiceSignalBroker:
    """In-memory pub/sub broker for per-session WebRTC signaling messages."""

    def __init__(self) -> None:
        self._queues: dict[str, dict[str, set[asyncio.Queue[dict[str, Any]]]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def subscribe(
        self,
        session_id: str,
        user_id: str,
    ) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._queues[session_id][user_id].add(queue)

        try:
            yield queue
        finally:
            async with self._lock:
                room = self._queues.get(session_id)
                if room is not None:
                    listeners = room.get(user_id)
                    if listeners is not None:
                        listeners.discard(queue)
                        if not listeners:
                            room.pop(user_id, None)

                    if not room:
                        self._queues.pop(session_id, None)

    async def publish(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        target_user_id: str | None = None,
        exclude_user_id: str | None = None,
    ) -> None:
        async with self._lock:
            room = self._queues.get(session_id, {})
            if target_user_id is not None:
                targets = list(room.get(target_user_id, ()))
            else:
                targets = [
                    queue
                    for user_id, queues in room.items()
                    if user_id != exclude_user_id
                    for queue in queues
                ]

        for queue in targets:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                continue
