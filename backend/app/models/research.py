"""
Research Agent Models - 联网研究Agent模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ResearchRunStatus(str, PyEnum):
    """研究运行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchRun(Base):
    """研究运行记录表"""
    __tablename__ = "research_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True, index=True)

    topic = Column(String(255), nullable=False)
    research_type = Column(String(64), nullable=False)      # pattern/comment/trend/style
    status = Column(String(32), default=ResearchRunStatus.PENDING)

    query_plan_json = Column(JSON, nullable=True)          # 搜索计划
    extracted_summary = Column(Text, nullable=True)        # 提取摘要
    result_json = Column(JSON, nullable=True)              # 研究结果

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)

    # 关系
    sources = relationship("ResearchSource", back_populates="research_run", cascade="all, delete-orphan")


class ResearchSource(Base):
    """研究来源表 - 保存搜索到的来源信息"""
    __tablename__ = "research_sources"

    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id"), nullable=False, index=True)

    title = Column(String(500), nullable=True)
    url = Column(Text, nullable=False)
    source_type = Column(String(64), nullable=True)         # search_result/article/comment/forum/ranking
    trust_score = Column(Float, default=0.5)              # 可信度评分

    extracted_text_hash = Column(String(128), nullable=True)  # 提取文本的哈希(用于去重)
    excerpt = Column(Text, nullable=True)                   # 短摘录(最多500字)
    used_for = Column(String(128), nullable=True)           # 用于什么目的

    created_at = Column(DateTime, default=utc_now)

    # 关系
    research_run = relationship("ResearchRun", back_populates="sources")


class KnowledgePattern(Base):
    """知识模式表 - 沉淀的套路知识"""
    __tablename__ = "knowledge_patterns"

    id = Column(Integer, primary_key=True, index=True)
    genre = Column(String(128), nullable=True, index=True)   # 题材
    tag = Column(String(128), nullable=True, index=True)      # 标签

    pattern_name = Column(String(255), nullable=False)
    pattern_type = Column(String(64), nullable=False, index=True)  # opening/hook/plot/character/pacing/conflict

    description = Column(Text, nullable=False)
    applicable_scene = Column(Text, nullable=True)            # 适用场景
    anti_patterns = Column(Text, nullable=True)             # 反模式/避坑指南
    source_ids = Column(JSON, nullable=True)                # 来源ID列表

    confidence = Column(Float, default=0.5)               # 置信度
    created_at = Column(DateTime, default=utc_now)


class ReaderInsight(Base):
    """读者洞察表 - 读者评论归纳"""
    __tablename__ = "reader_insights"

    id = Column(Integer, primary_key=True, index=True)
    genre = Column(String(128), nullable=True, index=True)

    insight_type = Column(String(64), nullable=False, index=True)  # like/dislike/subscribe/drop
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)                  # 证据/来源摘要
    source_ids = Column(JSON, nullable=True)

    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime, default=utc_now)


class TrendReport(Base):
    """趋势报告表 - 市场趋势分析"""
    __tablename__ = "trend_reports"

    id = Column(Integer, primary_key=True, index=True)
    genre = Column(String(128), nullable=True, index=True)
    platform = Column(String(128), nullable=True, index=True)  # 起点/晋江/番茄等

    report_title = Column(String(255), nullable=False)
    report_body = Column(Text, nullable=False)
    trend_tags = Column(JSON, nullable=True)                # 趋势标签
    source_ids = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now)
