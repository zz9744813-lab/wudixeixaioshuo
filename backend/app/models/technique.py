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
    """技巧卡表 - P4扩展版，支持分类体系和效果追踪"""
    __tablename__ = "technique_cards"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)  # 可选的来源书籍

    category = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)

    # P4新增：分类体系
    taxonomy_level_1 = Column(String(100), index=True)  # 一级分类
    taxonomy_level_2 = Column(String(100), index=True)  # 二级分类
    scene_stage = Column(String(100))  # 适用场景阶段
    # opening / daily_scene / conflict / climax / transition / ending / volume_opening / volume_finale

    suitable_chapter_range = Column(JSON, default=list)  # 适合章节范围，如 [1, 10] 表示开篇
    source_book_type = Column(String(100))  # 来源书籍类型：爽文/玄幻/都市/悬疑/恋爱等

    # P4新增：难度与风险
    difficulty = Column(Integer, default=3)  # 难度 1-5
    risk_level = Column(Integer, default=1)  # 风险等级 1-5

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

    # 评分 - P4扩展
    confidence_score = Column(Float, default=0.0)  # 置信度
    success_rate = Column(Float, default=0.0)  # 成功率
    usage_count = Column(Integer, default=0)  # 使用次数
    effectiveness_score = Column(Float, default=0.0)  # 效果评分
    positive_review_count = Column(Integer, default=0)  # 好评数
    negative_review_count = Column(Integer, default=0)  # 差评数

    # P4新增：使用追踪
    used_in_chapters = Column(JSON, default=list)  # 使用过的章节ID列表
    cluster_id = Column(Integer, nullable=True)  # 聚类ID，用于去重

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


# P4新增：BookProfile 书籍档案
class BookProfile(Base):
    """书籍档案表 - 记录书籍的题材、风格等元数据"""
    __tablename__ = "book_profiles"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), unique=True)

    # 基本分类
    genre = Column(String(100))  # 主题材
    sub_genre = Column(String(100))  # 子题材
    audience = Column(String(100))  # 目标读者群

    # 风格标签
    style_tags = Column(JSON, default=list)  # 风格标签列表
    narrative_pov = Column(String(50))  # 叙事视角
    pacing_type = Column(String(50))  # 节奏类型

    # 商业属性
    commercial_density = Column(Integer, default=5)  # 爽点密度 1-10
    adult_level = Column(Integer, default=0)  # 成人向程度 0-10

    # 分析结果
    strengths = Column(JSON, default=list)  # 优点列表
    weaknesses = Column(JSON, default=list)  # 缺点列表
    reusable_skill_categories = Column(JSON, default=list)  # 可复用技巧分类

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
