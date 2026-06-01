"""NovelForge AI - SSE event broadcaster"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.config import settings

event_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
_active_streams: set[str] = set()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def event_to_sse(event: dict[str, Any]) -> str:
    payload = {
        **event,
        "ts": _utcnow().isoformat(),
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _broadcast_loop(project_id: str, queue: asyncio.Queue) -> None:
    from app.events import create_event_publisher

    publisher = create_event_publisher(project_id)
    try:
        while True:
            event = await queue.get()
            await publisher(event)
    except asyncio.CancelledError:
        pass
    finally:
        publisher.close()


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def _get_or_create_queue(self, project_id: str) -> asyncio.Queue:
        if project_id not in self._queues:
            self._queues[project_id] = asyncio.Queue(maxsize=1024)
        return self._queues[project_id]

    async def publish(self, project_id: str, event: dict[str, Any]) -> None:
        try:
            queue = self._get_or_create_queue(project_id)
            await queue.put(event)
        except asyncio.QueueFull:
            pass

    async def subscribe(self, project_id: str) -> asyncio.Queue:
        queue = self._get_or_create_queue(project_id)
        if project_id not in self._tasks or self._tasks[project_id].done():
            self._tasks[project_id] = asyncio.create_task(_broadcast_loop(project_id, queue))
        return queue


event_bus = EventBus()


def dispatch_event(project_id: str, event: dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(event_bus.publish(project_id, event))
    except RuntimeError:
        asyncio.run(event_bus.publish(project_id, event))
