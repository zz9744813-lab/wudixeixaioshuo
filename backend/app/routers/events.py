"""
Events Router - SSE 实时事件流
"""

import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.services.event_bus import event_bus

router = APIRouter()


@router.get("/stream")
async def stream_events(request: Request):
    queue = await event_bus.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break

                event = await queue.get()
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"], ensure_ascii=False),
                }
        finally:
            event_bus.unsubscribe(queue)

    return EventSourceResponse(event_generator())
