"""
SubAgent Result Model - 子Agent结果模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class SubAgentResultStatus(str, PyEnum):
    """子Agent结果状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubAgentResult(Base):
    """子Agent结果表 - 记录子Agent执行后的汇总/合并结果"""
    __tablename__ = "subagent_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    parent_step_id = Column(Integer, ForeignKey("agent_steps.id"), nullable=True, index=True)

    result_type = Column(String(64), nullable=False)       # merge/summary/critic_report
    title = Column(String(255), nullable=False)
    status = Column(String(32), default=SubAgentResultStatus.PENDING)

    # 输入的子任务ID列表
    input_task_ids = Column(JSON, nullable=True)           # [1, 2, 3]
    
    # 汇总结果
    merged_output = Column(Text, nullable=True)
    parsed_output = Column(JSON, nullable=True)
    
    # 使用的模型信息
    provider_name = Column(String(128), nullable=True)
    model_name = Column(String(128), nullable=True)
    token_count = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # 关系
    run = relationship("AgentRun", back_populates="subagent_results")
