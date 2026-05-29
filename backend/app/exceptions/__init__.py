"""
Custom Exceptions - 自定义异常类
"""

from .base import (
    AppException,
    ValidationError,
    NotFoundError,
    ConflictError,
    PermissionError,
    RateLimitError,
    ExternalServiceError,
)

__all__ = [
    "AppException",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "PermissionError",
    "RateLimitError",
    "ExternalServiceError",
]
