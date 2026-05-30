"""
Feedback Models - 反馈模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class FeedbackSource(str, PyEnum):
    """反馈来源"""
    USER = "user"           # 用户反馈
    READER = "reader"       # 读者反馈
    SYSTEM = "system"       # 系统反馈
    CRITIC = "critic"       # 审稿Agent
    CONTINUITY = "continuity"  # 连续性Agent


class Feedback(Base):
    """反馈表"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"))

    source = Column(String(50), nullable=False)
    raw_text = Column(Text, nullable=False)  # 原始反馈文本

    # 解析结果
    parsed_category = Column(String(100))  # 解析后的类别
    parsed_rule = Column(Text)  # 转化成的规则
    priority = Column(Integer, default=2)  # 优先级 1-5

    # 关联评分
    score_impact = Column(Integer)  # 对评分的影响

    # 状态
    is_processed = Column(Integer, default=0)  # 是否已处理
    is_applied = Column(Integer, default=0)  # 是否已应用

    # === 异步真人训练营扩展字段 ===
    reader_score = Column(Float, nullable=True)        # 真人总分 0-100
    dimension_scores = Column(JSON, nullable=True)     # 维度分
    anchor = Column(JSON, nullable=True)               # 段落批注 [{para, quote, comment, type}]
    reaction = Column(String(50), nullable=True)       # hooked / meh / dropped
    applied_from_chapter = Column(Integer, nullable=True)  # 规则从哪一章开始影响
    batch_id = Column(Integer, ForeignKey("feedback_batches.id"), nullable=True)
    status = Column(String(50), default="queued")      # queued / batched / applied / failed

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    processed_at = Column(DateTime)

    # 关系
    batch = relationship("FeedbackBatch", back_populates="feedbacks")


class FeedbackBatch(Base):
    """真人反馈批次 - 多条反馈批处理后形成"""
    __tablename__ = "feedback_batches"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)
    chapter_id = Column(Integer, index=True, nullable=True)

    feedback_ids = Column(JSON, default=list)
    feedback_count = Column(Integer, default=0)

    avg_reader_score = Column(Float, nullable=True)
    avg_system_score = Column(Float, nullable=True)
    critic_gap = Column(Float, nullable=True)

    derived_rules = Column(JSON, default=list)
    dimension_summary = Column(JSON, default=dict)
    reaction_summary = Column(JSON, default=dict)

    triggered_evolution = Column(Integer, default=0)
    triggered_critic_calibration = Column(Integer, default=0)

    status = Column(String(50), default="processed")  # waiting / processing / processed / failed
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    processed_at = Column(DateTime, nullable=True)

    # 关系
    feedbacks = relationship("Feedback", back_populates="batch")


class UserPreference(Base):
    """用户偏好表 - 记录用户的喜好"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    category = Column(String(100), nullable=False)  # 偏好类别
    preference = Column(Text, nullable=False)  # 偏好内容
    weight = Column(Float, default=1.0)  # 权重

    # 来源
    source_feedback_id = Column(Integer, ForeignKey("feedback.id"))

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
