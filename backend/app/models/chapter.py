"""
Chapter Models - 小说章节模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ChapterStatus(str, PyEnum):
    """章节状态"""
    PLANNED = "planned"       # 已规划
    DRAFTING = "drafting"     # 起草中
    CRITICING = "criticing"   # 审稿中
    REWRITING = "rewriting"   # 改稿中
    CHECKING = "checking"     # 连续性检查中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    MANUAL_REVIEW = "manual_review"  # 需人工审核


class Chapter(Base):
    """章节表"""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    chapter_index = Column(Integer, nullable=False)  # 章节序号
    title = Column(String(300))
    status = Column(String(30), default=ChapterStatus.PLANNED)

    # 最终内容
    final_content = Column(Text)
    final_word_count = Column(Integer, default=0)

    # 评分 (0-100)
    total_score = Column(Float)
    plot_progress_score = Column(Float)
    character_consistency_score = Column(Float)
    pacing_score = Column(Float)
    hook_score = Column(Float)
    emotional_reward_score = Column(Float)
    style_consistency_score = Column(Float)
    continuity_score = Column(Float)
    clarity_score = Column(Float)
    readability_score = Column(Float)

    # 版本管理
    current_version = Column(Integer, default=0)
    best_version = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # 关系
    project = relationship("Project", back_populates="chapters")
    tasks = relationship("GenerationTask", back_populates="chapter")
    steps = relationship("GenerationStep", back_populates="chapter")


class ChapterVersion(Base):
    """章节版本表 - 保存每个版本的草稿"""
    __tablename__ = "chapter_versions"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    version_number = Column(Integer, nullable=False)  # 版本号

    # 版本内容
    plan_content = Column(Text)  # 规划内容
    draft_content = Column(Text)  # 草稿内容
    final_content = Column(Text)  # 最终内容

    # 评分
    total_score = Column(Float)
    critic_report = Column(Text)  # 审稿报告
    continuity_report = Column(Text)  # 连续性报告

    # 元数据
    rewrite_count = Column(Integer, default=0)  # 改稿次数
    improvement_from_last = Column(Float)  # 相比上版本的提升

    # 是否被采纳
    is_accepted = Column(Integer, default=0)
    acceptance_reason = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
