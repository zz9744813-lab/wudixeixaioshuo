"""
Logging Middleware - 请求日志中间件
"""

import time
import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import get_logger, app_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 记录请求和响应信息"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 生成请求 ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # 开始时间
        start_time = time.time()

        # 获取用户 ID（如果有认证）
        user_id: Optional[str] = None
        if hasattr(request.state, "user"):
            user_id = str(request.state.user.get("id")) if request.state.user else None

        # 创建带上下文的日志器
        logger = get_logger("app.api").with_context(
            request_id=request_id,
            user_id=user_id,
        )

        # 记录请求
        logger.log_operation(
            operation="REQUEST_START",
            entity_type="http_request",
            details={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
            },
        )

        # 执行请求
        try:
            response = await call_next(request)
        except Exception as exc:
            # 记录异常
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Unhandled exception: {exc}",
                exc_info=True,
                extra={"extra_fields": {
                    "duration_ms": duration_ms,
                    "method": request.method,
                    "path": request.url.path,
                }}
            )
            raise

        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000

        # 设置响应头
        response.headers["X-Request-ID"] = request_id

        # 记录响应
        level = "INFO" if response.status_code < 400 else "WARNING"
        logger.log_operation(
            operation="REQUEST_END",
            entity_type="http_response",
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
            level=level,
        )

        return response
