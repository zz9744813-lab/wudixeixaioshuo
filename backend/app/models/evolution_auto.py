"""
Prompt Evolution Models - Prompt自治进化模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class PromptEvolutionPolicy(Base):
    """Prompt进化策略表 - 配置何时触发进化"""
    __tablename__ = "prompt_evolution_policies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=True, index=True)
    role = Column(String(64), nullable=False, index=True)
    enabled = Column(Boolean, default=True)

    # 触发条件
    min_sample_count = Column(Integer, default=20)
    min_average_score = Column(Float, default=80.0)
    max_rewrite_rate = Column(Float, default=0.4)
    trigger_window_days = Column(Integer, default=7)

    # 进化参数
    candidate_count = Column(Integer, default=3)
    ab_test_sample_count = Column(Integer, default=10)
    min_improvement = Column(Float, default=3.0)
    auto_apply = Column(Boolean, default=True)
    rollout_ratio = Column(Float, default=0.2)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PromptEvolutionRunStatus(str, PyEnum):
    """Prompt进化运行状态"""
    PENDING = "pending"
    DIAGNOSING = "diagnosing"
    PROPOSING = "proposing"
    TESTING = "testing"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class PromptEvolutionRun(Base):
    """Prompt进化运行记录表"""
    __tablename__ = "prompt_evolution_runs"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("prompt_evolution_policies.id"), nullable=False, index=True)

    role = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default=PromptEvolutionRunStatus.PENDING)

    # 诊断结果
    diagnosis = Column(Text, nullable=True)
    failure_samples_json = Column(JSON, nullable=True)

    # 候选Prompt
    candidate_prompts_json = Column(JSON, nullable=True)

    # A/B测试结果
    ab_test_result_json = Column(JSON, nullable=True)

    # 应用信息
    applied_prompt_version_id = Column(Integer, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    rollback_reason = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)
