"""
Project Models - 小说项目模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ProjectStatus(str, PyEnum):
    """项目状态"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 进行中
    PAUSED = "paused"         # 暂停
    COMPLETED = "completed"   # 已完成
    ARCHIVED = "archived"     # 已归档


class QualityPriority(str, PyEnum):
    """质量优先级"""
    SPEED = "speed"      # 速度优先
    BALANCE = "balance"  # 平衡
    QUALITY = "quality"  # 质量优先


class Project(Base):
    """小说项目表"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # 基本目标
    genre = Column(String(100), nullable=False)  # 题材
    target_reader = Column(String(200))  # 目标读者
    total_word_goal = Column(Integer, default=100000)  # 总字数目标
    daily_word_goal = Column(Integer, default=3000)  # 每日字数目标
    chapter_word_goal = Column(Integer, default=3000)  # 每章字数目标
    daily_chapter_goal = Column(Integer, default=1)  # 每日章节目标
    update_time_slots = Column(JSON, default=list)  # 更新时间段

    # 质量目标 (1-10)
    plot_progress_intensity = Column(Integer, default=7)
    satisfaction_density = Column(Integer, default=7)
    emotional_tension = Column(Integer, default=6)
    writing_delicacy = Column(Integer, default=6)
    dialogue_ratio = Column(Integer, default=5)
    description_ratio = Column(Integer, default=5)
    commercial_pace = Column(Integer, default=7)
    adult_content_scale = Column(Integer, default=1)

    # 禁区
    forbidden_settings = Column(JSON, default=list)  # 禁止设定
    forbidden_relationships = Column(JSON, default=list)  # 禁止关系
    forbidden_plots = Column(JSON, default=list)  # 禁止剧情
    forbidden_genres = Column(JSON, default=list)  # 禁止跑偏题材

    # 参考经验
    technique_cards = Column(JSON, default=list)  # 使用的技巧卡ID
    excluded_techniques = Column(JSON, default=list)  # 排除的技巧卡
    preferred_template = Column(String(100))  # 偏好的章节模板

    # 配置
    quality_threshold = Column(Integer, default=80)  # 质量通过阈值
    quality_priority = Column(String(20), default=QualityPriority.BALANCE)
    max_rewrite_rounds = Column(Integer, default=3)  # 最大改稿轮数
    rewrite_improvement_threshold = Column(Float, default=2.0)  # 改稿提升阈值

    # 预算控制
    daily_budget = Column(Float, default=10.0)  # 每日预算上限(USD)
    total_budget = Column(Float)  # 总预算上限

    # 状态
    status = Column(String(20), default=ProjectStatus.DRAFT)
    current_chapter_index = Column(Integer, default=0)  # 当前章节序号
    total_words_written = Column(Integer, default=0)  # 已写字数

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 关系
    bible = relationship("NovelBible", back_populates="project", uselist=False)
    chapters = relationship(
        "Chapter",
        back_populates="project",
        order_by="Chapter.chapter_index",
        cascade="all, delete-orphan",
    )
    tasks = relationship(
        "GenerationTask",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    prompt_templates = relationship(
        "PromptTemplate",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    # Memory 相关级联关系
    character_memories = relationship(
        "CharacterMemory",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    world_memories = relationship(
        "WorldMemory",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    chapter_memories = relationship(
        "ChapterMemory",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    relationship_memories = relationship(
        "RelationshipMemory",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class NovelBible(Base):
    """小说圣经 - 世界观、人物、设定"""
    __tablename__ = "novel_bibles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)

    # 世界观设定
    world_setting = Column(Text)  # 世界观详细描述
    world_rules = Column(JSON, default=list)  # 世界规则
    timeline = Column(JSON, default=list)  # 时间线

    # 人物卡
    characters = Column(JSON, default=list)  # 人物列表
    character_relationships = Column(JSON, default=list)  # 人物关系

    # 故事设定
    main_plot = Column(Text)  # 主线剧情
    sub_plots = Column(JSON, default=list)  # 支线剧情
    foreshadowing = Column(JSON, default=list)  # 伏笔列表

    # 风格边界
    style_boundaries = Column(JSON, default=list)  # 风格约束
    tone_guidelines = Column(Text)  # 语气指导

    # 禁区
    forbidden_items = Column(JSON, default=list)  # 禁止项

    # 大纲
    volume_outline = Column(JSON, default=list)  # 卷纲
    chapter_outline = Column(JSON, default=list)  # 章纲

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    project = relationship("Project", back_populates="bible")
