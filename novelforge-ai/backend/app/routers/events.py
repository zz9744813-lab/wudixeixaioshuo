"""NovelForge AI - SSE router"""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.events.broadcaster import event_bus

router = APIRouter()


@router.get("/events/{project_id}")
async def project_events(project_id: str):
    async def stream():
        queue = await event_bus.subscribe(project_id)
        try:
            while True:
                payload = await queue.get()
                yield payload
        finally:
            await event_bus.unsubscribe(project_id, queue)

    return EventSourceResponse(stream())
