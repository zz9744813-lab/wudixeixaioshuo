"""
Base Exceptions - 基础异常类
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """
    应用基础异常

    Attributes:
        status_code: HTTP 状态码
        error_code: 业务错误码
        message: 错误消息
        details: 详细错误信息
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    default_message: str = "Internal server error"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message or self.default_message
        self.details = details or {}
        self.error_code = error_code or self.error_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(AppException):
    """参数验证错误"""
    status_code = 422
    error_code = "VALIDATION_ERROR"
    default_message = "Validation failed"


class NotFoundError(AppException):
    """资源不存在"""
    status_code = 404
    error_code = "NOT_FOUND"
    default_message = "Resource not found"


class ConflictError(AppException):
    """资源冲突"""
    status_code = 409
    error_code = "CONFLICT"
    default_message = "Resource conflict"


class PermissionError(AppException):
    """权限不足"""
    status_code = 403
    error_code = "FORBIDDEN"
    default_message = "Permission denied"


class RateLimitError(AppException):
    """请求频率限制"""
    status_code = 429
    error_code = "RATE_LIMITED"
    default_message = "Too many requests"


class ExternalServiceError(AppException):
    """外部服务错误"""
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    default_message = "External service error"


class LLMError(ExternalServiceError):
    """LLM 服务错误"""
    error_code = "LLM_ERROR"
    default_message = "LLM service error"


class DatabaseError(AppException):
    """数据库错误"""
    status_code = 500
    error_code = "DATABASE_ERROR"
    default_message = "Database error"


class TaskError(AppException):
    """任务执行错误"""
    status_code = 500
    error_code = "TASK_ERROR"
    default_message = "Task execution error"


class BudgetExceededError(AppException):
    """预算超限"""
    status_code = 429
    error_code = "BUDGET_EXCEEDED"
    default_message = "Daily budget exceeded"
