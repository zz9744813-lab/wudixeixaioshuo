"""
P6 评论区驱动评审系统 - 5 张新表
- reader_agent_profiles: 读者 Agent 长期权重 + 采纳历史
- review_comments: 评论/读者/主 Agent 回复 主表
- review_comment_groups: 主 Agent 合并后的评论组
- reader_review_runs: 每次自动评审的元数据
- review_settings: 项目级评论设置 (1:1 with project)
"""

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import backref, relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ReaderAgentProfile(Base):
    """读者 Agent 配置: 长期权重 + 采纳历史 (1:1 with agent_role)."""
    __tablename__ = "reader_agent_profiles"

    id = Column(Integer, primary_key=True, index=True)
    agent_role_id = Column(
        Integer,
        ForeignKey("model_roles.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    reader_key = Column(String(80), unique=True, index=True)
    display_name = Column(String(120))
    dimension = Column(String(80))

    weight = Column(Float, default=1.0)
    adopted_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    generated_comment_count = Column(Integer, default=0)

    enabled = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ReviewComment(Base):
    """评论主表: 用户/读者 Agent/主 Agent 三种作者共享一张表."""
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chapter_version_id = Column(
        Integer,
        ForeignKey("chapter_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_id = Column(
        Integer,
        ForeignKey("review_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    target_type = Column(String(30), default="chapter")  # project/chapter/version/book
    author_type = Column(String(30), index=True)  # user/reader_agent/chief_agent/system
    author_label = Column(String(120))
    agent_role_id = Column(
        Integer,
        ForeignKey("model_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    content = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)
    rating = Column(JSON, nullable=True)
    tags = Column(JSON, default=list)

    weight_at_created = Column(Float, default=1.0)

    status = Column(String(30), default="new", index=True)
    # new/replied/grouped/discussing/accepted/rejected/ignored/done

    priority = Column(Integer, default=50)

    related_group_id = Column(
        Integer,
        ForeignKey("review_comment_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_discussion_id = Column(
        Integer, nullable=True, index=True  # 关联现有 discussion_sessions.id
    )

    expires_at = Column(DateTime, nullable=True, index=True)

    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    replies = relationship(
        "ReviewComment",
        backref=backref("parent", remote_side="ReviewComment.id"),
        cascade="all, delete-orphan",
        single_parent=True,
    )


class ReviewCommentGroup(Base):
    """主 Agent 合并相似评论生成的评论组."""
    __tablename__ = "review_comment_groups"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chapter_version_id = Column(
        Integer,
        ForeignKey("chapter_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(200))
    summary = Column(Text)
    comment_ids = Column(JSON, default=list)

    severity = Column(String(20), default="medium")  # low/medium/high/blocker
    status = Column(String(30), default="new", index=True)
    # new/discussing/decided/rewrite_queued/done/ignored

    discussion_session_id = Column(Integer, nullable=True, index=True)
    decision = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ReaderReviewRun(Base):
    """每次读者评审 run 的元数据."""
    __tablename__ = "reader_review_runs"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    chapter_id = Column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    chapter_version_id = Column(
        Integer,
        ForeignKey("chapter_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    trigger = Column(String(40), default="chapter_completed")
    # chapter_completed / rewrite_completed / user_comment / scheduled

    status = Column(String(30), default="pending")
    # pending / running / succeeded / failed / partial

    reader_agent_keys = Column(JSON, default=list)
    generated_comment_ids = Column(JSON, default=list)

    total_cost_usd = Column(Float, default=0.0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)

    error = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)


class ReviewSettings(Base):
    """项目级评论设置 (1:1 with project)."""
    __tablename__ = "review_settings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    auto_reader_review = Column(Boolean, default=True)
    auto_chief_triage = Column(Boolean, default=True)
    auto_discussion = Column(Boolean, default=True)

    retention_days = Column(Integer, default=7)
    max_comments_per_chapter = Column(Integer, default=50)
    max_reader_comments_per_run = Column(Integer, default=5)

    min_severity_for_discussion = Column(String(20), default="medium")

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
