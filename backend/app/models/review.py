"""
Review Models - 独立评审系统
P4 Phase 4: 独立评审模型、多维度评审
"""

from datetime import datetime
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ReviewProfile(Base):
    """评审配置表 - 可配置的评审策略"""
    __tablename__ = "review_profiles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    name = Column(String(200), nullable=False)
    is_default = Column(Integer, default=0)

    # 评审角色配置
    reviewer_roles = Column(JSON, default=list)
    # ["reviewer_plot", "reviewer_character", "reviewer_continuity", ...]

    # 阈值
    quality_threshold = Column(Float, default=80.0)  # 通过阈值
    rewrite_threshold = Column(Float, default=75.0)  # 改写阈值
    auto_reject_threshold = Column(Float, default=60.0)  # 自动拒绝阈值

    # 维度权重
    weights = Column(JSON, default=dict)
    # {"plot": 0.2, "character": 0.15, "continuity": 0.15, ...}

    # 严格度
    strictness = Column(Integer, default=5)  # 1-10
    max_review_rounds = Column(Integer, default=2)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ReviewResult(Base):
    """评审结果表 - 记录每次评审的详细结果"""
    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("generation_tasks.id"), index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True)
    version_id = Column(Integer, ForeignKey("chapter_versions.id"), nullable=True)

    # 评审者信息
    reviewer_role = Column(String(100), index=True)  # reviewer_plot/reviewer_character/...
    reviewer_model = Column(String(200))
    provider_name = Column(String(100))

    # 评分
    total_score = Column(Float)
    score_breakdown = Column(JSON, default=dict)
    # {
    #   "plot_progress": 85,
    #   "character_consistency": 80,
    #   "continuity": 78,
    #   "pacing": 82,
    #   "hook": 88,
    #   "emotional_reward": 85,
    #   "foreshadow_quality": 75,
    #   "style_consistency": 80,
    #   "readability": 90,
    #   "commercial_potential": 88,
    #   "memory_consistency": 82,
    #   "safety_boundary": 95
    # }

    # 问题与建议
    problems = Column(JSON, default=list)  # 发现的问题
    suggestions = Column(JSON, default=list)  # 改进建议
    required_fixes = Column(JSON, default=list)  # 必须修复项

    # 状态
    pass_status = Column(String(50))  # pass/rewrite/reject/manual_review

    # 原始输出
    raw_output = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=utc_now)

    # 索引
    __table_args__ = (
        Index('idx_review_chapter_role', 'chapter_id', 'reviewer_role'),
        Index('idx_review_task', 'task_id', 'created_at'),
    )


class FinalReview(Base):
    """最终评审表 - FinalJudge汇总多评审结果"""
    __tablename__ = "final_reviews"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("generation_tasks.id"), index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True)
    version_id = Column(Integer, ForeignKey("chapter_versions.id"), nullable=True)

    # 汇总评分
    weighted_score = Column(Float)
    min_score = Column(Float)  # 最低维度分
    max_score = Column(Float)  # 最高维度分

    # 各评审结果引用
    review_result_ids = Column(JSON, default=list)

    # 维度评分汇总
    dimension_scores = Column(JSON, default=dict)

    # 关键问题
    critical_issues = Column(JSON, default=list)
    warnings = Column(JSON, default=list)

    # 最终判定
    final_status = Column(String(50))  # pass/rewrite/reject
    rewrite_focus = Column(JSON, default=list)  # 改写重点

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
