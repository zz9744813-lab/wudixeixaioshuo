"""
Provider Route Config Models - LLM路由配置模型
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ProviderRouteConfig(Base):
    """Provider路由配置表 - 多API路由池配置"""
    __tablename__ = "provider_route_configs"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("model_providers.id"), nullable=False, index=True)

    # 路由规则
    role = Column(String(64), nullable=False, index=True)     # planner/draft/critic/continuity/research/meta_prompt
    priority = Column(Integer, default=100)                    # 越小优先级越高
    weight = Column(Integer, default=1)                        # 同优先级负载权重
    enabled = Column(Boolean, default=True)

    # 限流配置
    rpm_limit = Column(Integer, nullable=True)                # 每分钟请求数限制
    tpm_limit = Column(Integer, nullable=True)                # 每分钟token数限制

    # 超时与重试
    timeout_seconds = Column(Integer, default=60)
    max_retries = Column(Integer, default=2)

    # 熔断配置
    circuit_breaker_threshold = Column(Integer, default=5)     # 连续失败多少次触发熔断
    circuit_breaker_reset_seconds = Column(Integer, default=300)  # 熔断后冷却时间(秒)
    consecutive_failures = Column(Integer, default=0)          # 当前连续失败次数
    circuit_breaker_opened_at = Column(DateTime, nullable=True)  # 熔断开始时间

    # 统计信息
    total_calls = Column(Integer, default=0)
    success_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    avg_latency_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    provider = relationship("ModelProvider")
