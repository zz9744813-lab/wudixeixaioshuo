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

    role = Column(String(64), nullable=False, index=True)       # draft/critic/rewrite/continuity
    enabled = Column(Boolean, default=True)

    # 触发条件
    min_sample_count = Column(Integer, default=20)              # 最小样本数
    min_average_score = Column(Float, default=80.0)             # 最低平均分(低于此触发)
    max_rewrite_rate = Column(Float, default=0.4)             # 最大重写率(高于此触发)
    trigger_window_days = Column(Integer, default=7)            # 统计窗口(天)

    # 进化参数
    candidate_count = Column(Integer, default=3)                # 生成候选数
    ab_test_sample_count = Column(Integer, default=10)          # A/B测试样本数
    min_improvement = Column(Float, default=3.0)              # 最小改进幅度
    auto_apply = Column(Boolean, default=True)                 # 是否自动应用
    rollout_ratio = Column(Float, default=0.2)                # 灰度比例

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PromptEvolutionRunStatus(str, PyEnum):
    """Prompt进化运行状态"""
    PENDING = "pending"
    DIAGNOSING = "diagnosing"       # 诊断中
    PROPOSING = "proposing"         # 生成候选中
    TESTING = "testing"             # A/B测试中
    APPLIED = "applied"             # 已应用
    ROLLED_BACK = "rolled_back"     # 已回滚
    FAILED = "failed"               # 失败


class PromptEvolutionRun(Base):
    """Prompt进化运行记录表"""
    __tablename__ = "prompt_evolution_runs"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("prompt_evolution_policies.id"), nullable=False, index=True)

    role = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default=PromptEvolutionRunStatus.PENDING)

    # 诊断结果
    diagnosis = Column(Text, nullable=True)                    # 问题诊断
    failure_samples_json = Column(JSON, nullable=True)        # 失败样本

    # 候选Prompt
    candidate_prompts_json = Column(JSON, nullable=True)      # 候选Prompt列表

    # A/B测试结果
    ab_test_result_json = Column(JSON, nullable=True)         # A/B测试结果

    # 应用信息
    applied_prompt_version_id = Column(Integer, nullable=True)   # 应用的版本ID
    applied_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    rollback_reason = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)
