"""
Technique Models - 技巧卡模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TechniqueCategory(str, PyEnum):
    """技巧类别"""
    STRUCTURE = "structure"      # 结构
    CHARACTER = "character"      # 人物
    PACING = "pacing"            # 节奏
    HOOK = "hook"                # 钩子
    EMOTION = "emotion"          # 情绪
    STYLE = "style"              # 文风
    READABILITY = "readability"  # 可读性
    COMMERCIAL = "commercial"    # 商业性


class TechniqueCard(Base):
    """技巧卡表"""
    __tablename__ = "technique_cards"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)  # 可选的来源书籍

    category = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)

    # 观察来源
    observation = Column(Text)  # 观察描述
    source_chapters = Column(JSON, default=list)  # 来源章节索引

    # 技巧描述
    description = Column(Text)  # 技巧描述
    principle = Column(Text)  # 为什么有效

    # 迁移规则
    transfer_rule = Column(Text)  # 可迁移场景
    usage_instruction = Column(Text)  # 使用指令

    # 反模式
    anti_pattern = Column(Text)  # 容易翻车的地方
    prevention_rule = Column(Text)  # 预防措施

    # 评分
    confidence_score = Column(Float, default=0.0)  # 置信度
    success_rate = Column(Float, default=0.0)  # 成功率
    usage_count = Column(Integer, default=0)  # 使用次数

    # Prompt指令（给Agent用）
    prompt_instruction = Column(Text)

    # 标签
    applicable_genres = Column(JSON, default=list)  # 适用题材
    tags = Column(JSON, default=list)

    # 状态
    is_active = Column(Integer, default=1)
    is_verified = Column(Integer, default=0)  # 是否已验证

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    book = relationship("Book", back_populates="technique_cards")


class StoryPattern(Base):
    """故事套路表"""
    __tablename__ = "story_patterns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    genre = Column(String(100))  # 适用题材
    description = Column(Text)

    # 结构步骤
    structure_steps = Column(JSON, default=list)  # 步骤列表
    expected_length = Column(String(100))  # 预期篇幅

    # 使用说明
    usable_for = Column(Text)  # 适合场景
    risks = Column(Text)  # 风险点

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)


class FailurePattern(Base):
    """失败模式表"""
    __tablename__ = "failure_patterns"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    category = Column(String(100), nullable=False)  # 失败类别
    symptom = Column(Text, nullable=False)  # 症状描述
    cause = Column(Text)  # 原因分析
    prevention_rule = Column(Text)  # 预防规则
    example_note = Column(Text)  # 案例说明

    # 发生次数
    occurrence_count = Column(Integer, default=1)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectPlaybook(Base):
    """项目写作手册表"""
    __tablename__ = "project_playbooks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)

    # 来源
    source_books = Column(JSON, default=list)  # 参考书籍ID
    source_techniques = Column(JSON, default=list)  # 使用的技巧卡

    # 规则
    rules = Column(JSON, default=list)  # 写作规则列表

    # 风格边界
    style_boundaries = Column(Text)  # 风格约束
    tone_guidelines = Column(Text)  # 语气指导

    # 章节模板
    chapter_template = Column(JSON)  # 章节结构模板

    # 评分标准
    scoring_rubric = Column(JSON)  # 评分细则

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
