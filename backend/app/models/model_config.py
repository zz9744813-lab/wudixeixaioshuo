"""
Model Config Models - 模型配置模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ModelProvider(Base):
    """模型提供商表"""
    __tablename__ = "model_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 显示名称
    provider_type = Column(String(50), nullable=False)  # 类型: openai, anthropic, gemini, openrouter, custom

    # 连接配置
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text)  # 加密存储的API Key
    api_key_mask = Column(String(100))  # 掩码显示

    # 默认模型
    default_model = Column(String(200))

    # 状态
    is_enabled = Column(Integer, default=1)
    is_default = Column(Integer, default=0)

    # 高级参数默认值
    default_temperature = Column(Float, default=0.7)
    default_top_p = Column(Float, default=1.0)
    default_max_tokens = Column(Integer, default=4000)

    # 限制
    timeout_seconds = Column(Integer, default=120)
    retry_times = Column(Integer, default=3)
    rate_limit = Column(Integer)  # 每分钟请求数限制

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_tested_at = Column(DateTime)
    last_test_result = Column(String(50))  # success / failed

    # 关系
    roles = relationship("ModelRole", back_populates="provider")


class ModelRole(Base):
    """模型角色映射表"""
    __tablename__ = "model_roles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # 全局或项目特定
    provider_id = Column(Integer, ForeignKey("model_providers.id"))

    role = Column(String(50), nullable=False)  # planner, draft, critic, rewrite, memory, embedding
    model_name = Column(String(200), nullable=False)

    # 角色特定参数
    temperature = Column(Float)
    top_p = Column(Float)
    max_tokens = Column(Integer)

    # 优先级（用于多个配置时的选择）
    priority = Column(Integer, default=1)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    provider = relationship("ModelProvider", back_populates="roles")


class ModelCallLog(Base):
    """模型调用日志表"""
    __tablename__ = "model_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("model_providers.id"))

    # 调用信息
    role = Column(String(50))  # 使用的角色
    model_name = Column(String(200))
    request_type = Column(String(100))  # 请求类型

    # Token统计
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 成本（估算）
    estimated_cost = Column(Float)

    # 耗时
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_ms = Column(Integer)

    # 状态
    status = Column(String(50))  # success / failed / timeout
    error_message = Column(Text)

    # 请求内容摘要
    prompt_summary = Column(Text)
    response_summary = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
