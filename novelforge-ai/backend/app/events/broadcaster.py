"""NovelForge AI - SSE broadcaster"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("novelforge.events")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def event_to_sse(event: dict[str, Any]) -> str:
    payload = {
        **event,
        "ts": _utcnow().isoformat(),
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = {}

    def _get_or_create(self, project_id: str) -> list[asyncio.Queue]:
        if project_id not in self._queues:
            self._queues[project_id] = []
        return self._queues[project_id]

    async def publish(self, project_id: str, event: dict[str, Any]) -> None:
        queues = self._get_or_create(project_id)
        for queue in list(queues):
            try:
                await queue.put(event_to_sse(event))
            except asyncio.QueueFull:
                logger.warning("event queue full for project %s", project_id)

    async def subscribe(self, project_id: str) -> asyncio.Queue:
        queues = self._get_or_create(project_id)
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        queues.append(queue)
        return queue

    async def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        queues = self._queues.get(project_id)
        if not queues:
            return
        try:
            queues.remove(queue)
        except ValueError:
            pass


event_bus = EventBus()


def dispatch_event(project_id: str, event: dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(event_bus.publish(project_id, event))
    except RuntimeError:
        asyncio.run(event_bus.publish(project_id, event))
