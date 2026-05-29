"""
Events Router - SSE 实时事件流
"""

import json
from fastapi import APIRouter, Request, Query, HTTPException, status, Depends
from sse_starlette.sse import EventSourceResponse

from app.services.event_bus import event_bus
from app.deps.auth import get_api_key_from_env
import hmac
import os

router = APIRouter()


def validate_api_key(request: Request, api_key: str = Query(default="", description="API Key for SSE authentication (fallback if header not available)")):
    """验证API Key，优先从header获取，其次从URL参数获取（原生EventSource兼容性）"""
    expected_key = get_api_key_from_env()
    app_env = os.getenv("APP_ENV", "development").lower()

    # 未配置 API Key 时的处理
    if not expected_key:
        # 开发环境放行
        if app_env in ("development", "dev", "local"):
            return True
        # 生产/预发环境拒绝服务
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APP_API_KEY is not configured on server",
        )

    # 优先从header获取API Key
    header_key = request.headers.get("X-API-Key", "")
    # 其次从query参数获取（原生EventSource只能带query）
    actual_key = header_key if header_key else api_key

    if not actual_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key (provide via X-API-Key header or api_key query parameter)",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not hmac.compare_digest(actual_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


@router.get("/stream")
async def stream_events(
    request: Request,
    _auth: bool = Depends(validate_api_key),
):
    """SSE事件流端点 - 支持header或URL参数传递api_key"""
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
