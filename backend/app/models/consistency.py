"""
Consistency Models - 元数据对齐检查模型 (B4)
人设、战力、时间线一致性检查
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, Enum
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ConsistencyCheckType(str, PyEnum):
    """对齐检查类型"""
    CHARACTER = "character"           # 人设一致性
    POWER = "power"                   # 战力体系
    TIMELINE = "timeline"             # 时间线
    WORLD_SETTING = "world_setting"   # 世界观设定
    RELATIONSHIP = "relationship"     # 人物关系
    LOCATION = "location"             # 地点/场景
    ITEM = "item"                     # 物品/道具


class ConsistencyIssueSeverity(str, PyEnum):
    """一致性问题严重程度"""
    CRITICAL = "critical"     # 严重：逻辑矛盾，必须修复
    MAJOR = "major"           # 重要：明显偏差，建议修复
    MINOR = "minor"           # 轻微：细节不一致，可选修复
    INFO = "info"             # 提示：潜在风险，注意即可


class ConsistencyRule(Base):
    """
    一致性检查规则
    定义项目级别的对齐规则和约束
    """
    __tablename__ = "consistency_rules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 规则定义
    rule_type = Column(Enum(ConsistencyCheckType), nullable=False)
    rule_name = Column(String(200), nullable=False)
    description = Column(Text)

    # 规则配置（JSON格式，根据类型不同结构不同）
    rule_config = Column(JSON, default=dict)
    # character规则示例:
    # {
    #     "character_name": "主角名",
    #     "attributes": ["性格", "口头禅", "习惯性动作"],
    #     "forbidden_changes": ["核心价值观", "核心能力"]
    # }
    # power规则示例:
    # {
    #     "power_system_name": "修炼体系",
    #     "levels": ["炼气", "筑基", "金丹", "元婴"],
    #     "rules": ["高阶对低阶压制", "同阶战力差距上限"]
    # }
    # timeline规则示例:
    # {
    #     "start_date": "第一章日期",
    #     "time_flow": "linear",  # linear, flashback, parallel
    #     "key_events": [{"chapter": 1, "event": "事件", "time": "时间"}]
    # }

    # 检查配置
    auto_check = Column(Boolean, default=True)  # 是否自动检查
    check_frequency = Column(String(20), default="per_chapter")  # per_chapter, per_volume, manual
    alert_threshold = Column(Enum(ConsistencyIssueSeverity), default=ConsistencyIssueSeverity.MAJOR)

    # 状态
    is_active = Column(Boolean, default=True)

    # 元数据
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    project = relationship("Project", back_populates="consistency_rules")
    check_results = relationship(
        "ConsistencyCheckResult",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "rule_type": self.rule_type.value if self.rule_type else None,
            "rule_name": self.rule_name,
            "description": self.description,
            "rule_config": self.rule_config,
            "auto_check": self.auto_check,
            "check_frequency": self.check_frequency,
            "alert_threshold": self.alert_threshold.value if self.alert_threshold else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConsistencyCheckResult(Base):
    """
    一致性检查结果
    存储每次检查的结果和发现的问题
    """
    __tablename__ = "consistency_check_results"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(
        Integer,
        ForeignKey("consistency_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 检查范围
    checked_chapters = Column(JSON, default=list)  # 检查的章节ID列表
    check_scope = Column(String(50), default="single")  # single, volume, full

    # 检查结果摘要
    total_issues = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    major_count = Column(Integer, default=0)
    minor_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)

    # 状态
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    # 元数据
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime)

    # 关系
    rule = relationship("ConsistencyRule", back_populates="check_results")
    issues = relationship(
        "ConsistencyIssue",
        back_populates="check_result",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "checked_chapters": self.checked_chapters,
            "check_scope": self.check_scope,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "info_count": self.info_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ConsistencyIssue(Base):
    """
    一致性问题详情
    存储具体的对齐问题和修复建议
    """
    __tablename__ = "consistency_issues"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(
        Integer,
        ForeignKey("consistency_check_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 问题描述
    issue_type = Column(Enum(ConsistencyCheckType), nullable=False)
    severity = Column(Enum(ConsistencyIssueSeverity), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)

    # 问题位置
    location = Column(String(200))  # 如 "第3章第2段"
    quote = Column(Text)  # 引用原文

    # 对比信息（前后不一致的内容）
    expected_value = Column(Text)  # 预期值（来自圣经/前文）
    actual_value = Column(Text)    # 实际值（当前章节）
    reference_location = Column(String(200))  # 参考位置（如 "第1章"）
    reference_quote = Column(Text)  # 参考原文

    # 修复建议
    fix_suggestion = Column(Text)
    auto_fixable = Column(Boolean, default=False)
    auto_fix_prompt = Column(Text)  # 用于自动修复的prompt

    # 状态
    status = Column(String(20), default="open")  # open, acknowledged, fixed, ignored
    fixed_at = Column(DateTime)
    fixed_by = Column(String(50))  # user, auto, manual

    # 元数据
    created_at = Column(DateTime, default=utc_now)

    # 关系
    check_result = relationship("ConsistencyCheckResult", back_populates="issues")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "chapter_id": self.chapter_id,
            "issue_type": self.issue_type.value if self.issue_type else None,
            "severity": self.severity.value if self.severity else None,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "quote": self.quote,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "reference_location": self.reference_location,
            "reference_quote": self.reference_quote,
            "fix_suggestion": self.fix_suggestion,
            "auto_fixable": self.auto_fixable,
            "status": self.status,
            "fixed_at": self.fixed_at.isoformat() if self.fixed_at else None,
            "fixed_by": self.fixed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CharacterConsistencyLog(Base):
    """
    人物一致性日志
    记录人物属性在各章节的变化历史
    """
    __tablename__ = "character_consistency_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    character_name = Column(String(100), nullable=False, index=True)
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 属性快照
    attributes = Column(JSON, default=dict)
    # 示例: {
    #     "cultivation_level": "金丹期",
    #     "personality_traits": ["冷静", "果断"],
    #     "appearance": "黑衣长发",
    #     "relationships": {"师父": "张三", "仇敌": "李四"}
    # }

    # 变化标记
    changed_fields = Column(JSON, default=list)  # 本次发生变化的字段
    change_type = Column(String(20), default="unchanged")  # unchanged, evolution, contradiction, correction

    # 元数据
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "character_name": self.character_name,
            "chapter_id": self.chapter_id,
            "attributes": self.attributes,
            "changed_fields": self.changed_fields,
            "change_type": self.change_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TimelineEvent(Base):
    """
    时间线事件
    记录故事中的关键时间点和事件
    """
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 事件信息
    event_name = Column(String(200), nullable=False)
    event_description = Column(Text)

    # 时间信息
    story_time = Column(String(100))  # 故事内时间（如 "天元历1024年三月"）
    story_time_order = Column(Float, default=0.0)  # 用于排序的时间值
    time_type = Column(String(20), default="point")  # point, duration_start, duration_end

    # 关联信息
    related_characters = Column(JSON, default=list)  # 参与角色
    related_locations = Column(JSON, default=list)  # 发生地点
    related_items = Column(JSON, default=list)  # 涉及物品

    # 标记
    is_key_event = Column(Boolean, default=False)  # 是否关键转折点
    is_flashback = Column(Boolean, default=False)  # 是否为回忆/倒叙

    # 元数据
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "event_name": self.event_name,
            "event_description": self.event_description,
            "story_time": self.story_time,
            "story_time_order": self.story_time_order,
            "time_type": self.time_type,
            "related_characters": self.related_characters,
            "related_locations": self.related_locations,
            "related_items": self.related_items,
            "is_key_event": self.is_key_event,
            "is_flashback": self.is_flashback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
