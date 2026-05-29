"""
Event Bus - SSE 事件总线
用于 Worker 和 Agent 实时进度推送
"""

import asyncio
import json
from typing import Any, Dict, Set


class EventBus:
    def __init__(self):
        self.subscribers: Set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.discard(queue)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        event = {
            "type": event_type,
            "data": data,
        }

        dead_queues = []
        for queue in self.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for queue in dead_queues:
            self.unsubscribe(queue)


event_bus = EventBus()
