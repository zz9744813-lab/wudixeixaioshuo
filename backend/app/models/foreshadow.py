"""
Foreshadow Models - 伏笔系统模型
P4 Phase 3: 伏笔埋设与回收
"""

from datetime import datetime
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class Foreshadow(Base):
    """伏笔表 - 记录伏笔的全生命周期"""
    __tablename__ = "foreshadows"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)

    # 基本信息
    title = Column(String(300), nullable=False)
    foreshadow_type = Column(String(100))  # item/dialogue/prophecy/secret/identity/relationship/world_rule/power/location

    # 章节追踪
    setup_chapter = Column(Integer, nullable=True, index=True)  # 埋设章节
    expected_payoff_chapter = Column(Integer, nullable=True)  # 预期回收章节
    actual_payoff_chapter = Column(Integer, nullable=True)  # 实际回收章节

    # 状态生命周期
    status = Column(String(50), default="planned", index=True)
    # planned / planted / developed / ready_to_payoff / paid_off / abandoned / risky

    # 内容
    setup_content = Column(Text)  # 埋设内容（原文或摘要）
    development_notes = Column(JSON, default=list)  # 推进记录 [{chapter: 3, note: "..."}]
    payoff_plan = Column(Text)  # 回收计划
    payoff_content = Column(Text)  # 实际回收内容

    # 关联
    related_characters = Column(JSON, default=list)  # 关联角色
    related_items = Column(JSON, default=list)  # 关联物品
    related_world_rules = Column(JSON, default=list)  # 关联世界观规则

    # 重要性
    importance_score = Column(Float, default=0.5)  # 重要性 0-1
    risk_score = Column(Float, default=0.0)  # 遗忘风险 0-1
    reader_expectation = Column(Float, default=0.5)  # 读者期待程度 0-1

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 索引优化
    __table_args__ = (
        Index('idx_foreshadow_project_status', 'project_id', 'status'),
        Index('idx_foreshadow_setup_chapter', 'project_id', 'setup_chapter'),
    )


class ForeshadowPlan(Base):
    """章节伏笔计划表 - 每章要处理的伏笔任务"""
    __tablename__ = "foreshadow_plans"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    chapter_index = Column(Integer, index=True)

    # 计划内容
    new_foreshadows = Column(JSON, default=list)  # 计划新增的伏笔 [{title, type, content}]
    develop_foreshadow_ids = Column(JSON, default=list)  # 要推进的伏笔ID
    payoff_foreshadow_ids = Column(JSON, default=list)  # 要回收的伏笔ID
    must_include_lines = Column(JSON, default=list)  # 必须包含的伏笔线索

    # 风险提醒
    risky_foreshadow_ids = Column(JSON, default=list)  # 风险伏笔（长期未回收）

    # 执行状态
    is_executed = Column(Integer, default=0)  # 是否已执行
    execution_result = Column(JSON, default=dict)  # 执行结果

    created_at = Column(DateTime, default=utc_now)


class ForeshadowReview(Base):
    """伏笔评审表 - 连续性检查中的伏笔专项评审"""
    __tablename__ = "foreshadow_reviews"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), index=True)

    # 评审结果
    forgotten_foreshadows = Column(JSON, default=list)  # 遗忘的伏笔
    premature_payoffs = Column(JSON, default=list)  # 过早回收
    delayed_payoffs = Column(JSON, default=list)  # 延迟回收
    payoff_quality_issues = Column(JSON, default=list)  # 回收质量问题
    contradictions = Column(JSON, default=list)  # 自相矛盾

    # 评分
    foreshadow_score = Column(Float, default=0.0)
    suggestions = Column(JSON, default=list)

    created_at = Column(DateTime, default=utc_now)
