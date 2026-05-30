"""
LLM Router Schemas - LLM路由相关请求/响应模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProviderRouteConfigBase(BaseModel):
    """Provider路由配置基础模型"""
    model_config = ConfigDict(from_attributes=True)

    provider_id: int
    role: str = Field(..., description="角色: planner/draft/critic/continuity/research/meta_prompt")
    priority: int = Field(default=100, description="优先级，越小越高")
    weight: int = Field(default=1, description="同优先级负载权重")
    enabled: bool = Field(default=True)
    rpm_limit: Optional[int] = Field(default=None, description="每分钟请求数限制")
    tpm_limit: Optional[int] = Field(default=None, description="每分钟token数限制")
    timeout_seconds: int = Field(default=60)
    max_retries: int = Field(default=2)


class ProviderRouteConfigCreate(ProviderRouteConfigBase):
    """创建路由配置请求"""
    pass


class ProviderRouteConfigUpdate(BaseModel):
    """更新路由配置请求"""
    model_config = ConfigDict(from_attributes=True)

    priority: Optional[int] = None
    weight: Optional[int] = None
    enabled: Optional[bool] = None
    rpm_limit: Optional[int] = None
    tpm_limit: Optional[int] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None


class ProviderRouteConfigResponse(ProviderRouteConfigBase):
    """路由配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None

    # 熔断状态
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: int = 300
    consecutive_failures: int = 0
    circuit_breaker_opened_at: Optional[datetime] = None
    is_circuit_open: bool = False

    # 统计信息
    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    avg_latency_ms: Optional[int] = None

    created_at: datetime
    updated_at: datetime


class ProviderRouteConfigListResponse(BaseModel):
    """路由配置列表响应"""
    model_config = ConfigDict(from_attributes=True)

    items: List[ProviderRouteConfigResponse]
    total: int


class RouteTestRequest(BaseModel):
    """路由测试请求"""
    role: str = Field(..., description="要测试的角色")
    prompt: str = Field(default="Hello, this is a test message.", description="测试提示词")
    max_tokens: int = Field(default=100)
    temperature: float = Field(default=0.7)


class RouteTestResponse(BaseModel):
    """路由测试响应"""
    model_config = ConfigDict(from_attributes=True)

    success: bool
    role: str
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    content: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    duration_ms: int = 0
    error_message: Optional[str] = None


class RoleRouteInfo(BaseModel):
    """角色路由信息"""
    model_config = ConfigDict(from_attributes=True)

    role: str
    description: str
    route_count: int
    enabled_route_count: int
    primary_provider: Optional[str] = None
    fallback_providers: List[str] = []


class RoleListResponse(BaseModel):
    """角色列表响应"""
    model_config = ConfigDict(from_attributes=True)

    roles: List[RoleRouteInfo]


class RouteStats(BaseModel):
    """路由统计信息"""
    model_config = ConfigDict(from_attributes=True)

    role: str
    total_calls: int
    success_calls: int
    failed_calls: int
    success_rate: float
    avg_latency_ms: Optional[int]
    total_cost: float
    recent_failures: int


class RouteStatsResponse(BaseModel):
    """路由统计响应"""
    model_config = ConfigDict(from_attributes=True)

    stats: List[RouteStats]
    overall_total_calls: int
    overall_total_cost: float
