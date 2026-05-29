"""
Common Schemas - 通用响应模型
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


class ApiResponse(BaseModel):
    """通用API响应"""
    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    model_config = ConfigDict(from_attributes=True)

    success: bool = False
    error: str
    detail: Optional[str] = None


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """分页响应"""
    model_config = ConfigDict(from_attributes=True)

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthCheck(BaseModel):
    """健康检查响应"""
    model_config = ConfigDict(from_attributes=True)

    status: str
    service: str
    version: str
    database: str
