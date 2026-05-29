"""
记忆系统模型 - Phase 1 最小闭环
支持长篇小说的长期记忆管理
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time_utils import utc_now


class CharacterMemory(Base):
    """角色长期记忆 - L1层"""
    __tablename__ = "character_memories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)

    name = Column(String(200), nullable=False, index=True)
    aliases = Column(JSON, default=list)  # 别名列表
    role_type = Column(String(50))  # protagonist/supporting/villain/mentor/love_interest

    stable_profile = Column(JSON, default=dict)  # 不轻易变的设定：出身、天赋、核心性格
    dynamic_state = Column(JSON, default=dict)   # 当前状态：境界、伤势、位置、资源
    personality = Column(JSON, default=dict)     # 性格特征
    goals = Column(JSON, default=list)           # 当前目标
    secrets = Column(JSON, default=list)         # 秘密

    first_appearance_chapter = Column(Integer)
    last_seen_chapter = Column(Integer)
    importance_score = Column(Float, default=0.5)  # 0-1，主角=1，路人=0.1

    summary = Column(Text)  # 角色摘要
    latest_update_reason = Column(Text)  # 上次更新原因

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 反向关系
    project = relationship("Project", back_populates="character_memories")

    # 索引优化查询
    __table_args__ = (
        Index('idx_char_memory_project_name', 'project_id', 'name'),
        Index('idx_char_memory_importance', 'project_id', 'importance_score'),
    )


class WorldMemory(Base):
    """世界观记忆 - L2层"""
    __tablename__ = "world_memories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)

    category = Column(String(50), index=True)  # location/organization/item/power_system/rule/history/event
    name = Column(String(200), nullable=False, index=True)
    aliases = Column(JSON, default=list)

    description = Column(Text)  # 描述
    rules = Column(JSON, default=list)  # 规则列表
    constraints = Column(JSON, default=list)  # 约束/限制
    related_characters = Column(JSON, default=list)  # 相关角色
    related_chapters = Column(JSON, default=list)  # 相关章节

    importance_score = Column(Float, default=0.5)  # 重要性
    is_canon = Column(Integer, default=1)  # 1=正史设定，0=临时/可改

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 反向关系
    project = relationship("Project", back_populates="world_memories")

    __table_args__ = (
        Index('idx_world_memory_project_cat', 'project_id', 'category'),
        Index('idx_world_memory_project_name', 'project_id', 'name'),
    )


class ChapterMemory(Base):
    """章节事件记忆 - L3层"""
    __tablename__ = "chapter_memories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), index=True, nullable=False)
    chapter_index = Column(Integer, index=True)

    short_summary = Column(Text)       # 短摘要 200-500字
    detailed_summary = Column(Text)    # 详细摘要 1000-2000字
    key_events = Column(JSON, default=list)  # 关键事件列表
    character_changes = Column(JSON, default=list)  # 角色变化
    world_updates = Column(JSON, default=list)      # 世界观更新
    relationship_changes = Column(JSON, default=list)  # 关系变化
    unresolved_questions = Column(JSON, default=list)  # 未解之谜
    foreshadow_updates = Column(JSON, default=list)    # 伏笔更新

    created_at = Column(DateTime, default=utc_now)

    # 反向关系
    project = relationship("Project", back_populates="chapter_memories")
    chapter = relationship("Chapter", back_populates="chapter_memory")

    __table_args__ = (
        Index('idx_chapter_memory_project_idx', 'project_id', 'chapter_index'),
    )


class RelationshipMemory(Base):
    """人物关系记忆 - L4层"""
    __tablename__ = "relationship_memories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)

    character_a = Column(String(200), index=True)
    character_b = Column(String(200), index=True)
    relationship_type = Column(String(100))  # enemy/ally/family/romance/master-disciple/rival
    current_status = Column(Text)  # 当前关系状态描述
    tension_level = Column(Integer, default=0)   # 紧张度 -100到100
    trust_level = Column(Integer, default=0)     # 信任度 -100到100

    history = Column(JSON, default=list)  # 关系变化历史
    last_changed_chapter = Column(Integer)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 反向关系
    project = relationship("Project", back_populates="relationship_memories")

    __table_args__ = (
        Index('idx_rel_memory_project_chars', 'project_id', 'character_a', 'character_b'),
    )


class MemoryQueryLog(Base):
    """记忆查询日志 - 用于优化检索策略"""
    __tablename__ = "memory_query_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True, nullable=True)

    query_type = Column(String(50))  # character/world/chapter/relationship
    query_params = Column(JSON, default=dict)  # 查询参数
    results_count = Column(Integer)  # 返回结果数
    created_at = Column(DateTime, default=utc_now)
