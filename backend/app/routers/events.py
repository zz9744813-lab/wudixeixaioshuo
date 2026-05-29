"""
Events Router - SSE 实时事件流
"""

import json
from fastapi import APIRouter, Request, Query, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.services.event_bus import event_bus
from app.deps.auth import get_api_key_from_env
import hmac

router = APIRouter()


def validate_api_key(api_key: str):
    """验证API Key，支持URL参数传递（SSE无法自定义header）"""
    expected_key = get_api_key_from_env()

    # 生产环境必须配置 API Key
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APP_API_KEY is not configured on server",
        )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing api_key parameter",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


@router.get("/stream")
async def stream_events(
    request: Request,
    api_key: str = Query(default="", description="API Key for SSE authentication"),
):
    """SSE事件流端点 - 通过URL参数传递api_key"""
    # 验证API Key
    validate_api_key(api_key)

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
