"""
Error Handler - 全局异常处理器
统一处理各种异常，返回标准错误响应
"""

import traceback
from typing import Any, Dict, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.exceptions.base import AppException, LLMError, DatabaseError
from app.utils.logging import get_logger

logger = get_logger("app.error")


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """处理应用自定义异常"""
        logger.log_operation(
            operation="APP_EXCEPTION",
            entity_type="error",
            details={
                "error_code": exc.error_code,
                "message": exc.message,
                "path": request.url.path,
                "method": request.method,
            },
            level="WARNING",
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求参数验证错误"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        logger.log_operation(
            operation="VALIDATION_ERROR",
            entity_type="error",
            details={
                "path": request.url.path,
                "method": request.method,
                "errors": errors,
            },
            level="WARNING",
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": errors},
                }
            },
        )

    @app.exception_handler(PydanticValidationError)
    async def handle_pydantic_error(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        """处理 Pydantic 验证错误"""
        return await handle_validation_error(request, RequestValidationError(exc.errors()))

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """处理数据库完整性错误"""
        logger.log_operation(
            operation="DATABASE_INTEGRITY_ERROR",
            entity_type="error",
            details={
                "path": request.url.path,
                "message": str(exc),
            },
            level="ERROR",
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "DATABASE_INTEGRITY_ERROR",
                    "message": "Data conflict or constraint violation",
                    "details": {},
                }
            },
        )

    @app.exception_handler(OperationalError)
    async def handle_operational_error(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        """处理数据库操作错误"""
        logger.log_operation(
            operation="DATABASE_ERROR",
            entity_type="error",
            details={
                "path": request.url.path,
                "message": str(exc),
            },
            level="ERROR",
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Database operation failed",
                    "details": {},
                }
            },
        )

    @app.exception_handler(LLMError)
    async def handle_llm_error(request: Request, exc: LLMError) -> JSONResponse:
        """处理 LLM 服务错误"""
        logger.log_operation(
            operation="LLM_ERROR",
            entity_type="error",
            details={
                "path": request.url.path,
                "message": exc.message,
            },
            level="ERROR",
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """处理未知异常"""
        error_id = f"err_{id(exc):x}"

        logger.error(
            f"Unhandled exception [{error_id}]: {exc}",
            exc_info=True,
            extra={"extra_fields": {
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            }}
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "details": {"error_id": error_id},
                }
            },
        )


def http_exception(
    status_code: int,
    error_code: str,
    message: str,
    details: Dict[str, Any] = None,
) -> JSONResponse:
    """创建标准 HTTP 错误响应"""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            }
        },
    )
