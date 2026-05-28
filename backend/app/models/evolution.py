"""
Evolution Models - 进化/Darwin模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class EvolutionDecision(str, PyEnum):
    """进化决策"""
    KEEP = "keep"       # 保留新版本
    REVERT = "revert"   # 回滚旧版本
    PENDING = "pending" # 待决定


class EvolutionTarget(str, PyEnum):
    """进化目标类型"""
    PLAYBOOK = "playbook"           # 写作手册
    PROMPT = "prompt"               # 提示词
    RUBRIC = "rubric"               # 评分标准
    CHARACTER_RULE = "character_rule"  # 人物规则
    CHAPTER_TEMPLATE = "chapter_template"  # 章节模板
    TECHNIQUE_WEIGHT = "technique_weight"  # 技巧卡权重


class EvolutionRun(Base):
    """进化运行记录表"""
    __tablename__ = "evolution_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    # 目标
    target_type = Column(String(50), nullable=False)
    target_name = Column(String(200))

    # 版本
    before_version = Column(Text)  # 改进前
    after_version = Column(Text)  # 改进后

    # 评分对比
    before_score = Column(Float)
    after_score = Column(Float)
    improvement = Column(Float)  # 提升幅度

    # 版本关联 - 新增
    before_version_id = Column(Integer, ForeignKey("version_history.id"))
    after_version_id = Column(Integer, ForeignKey("version_history.id"))

    # 决策
    decision = Column(String(20), default=EvolutionDecision.PENDING)
    reason = Column(Text)  # 决策理由

    # 测试信息
    test_sample_count = Column(Integer, default=0)  # 测试样本数
    judge_agents = Column(JSON, default=list)  # 参与评判的Agent

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)


class EvolutionLog(Base):
    """进化日志表"""
    __tablename__ = "evolution_logs"

    id = Column(Integer, primary_key=True, index=True)
    evolution_run_id = Column(Integer, ForeignKey("evolution_runs.id"))

    log_type = Column(String(50))  # info, warning, error, success
    message = Column(Text)

    # 详细数据
    details = Column(JSON)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)


class VersionHistory(Base):
    """版本历史表 - 保存所有历史版本"""
    __tablename__ = "version_history"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    asset_type = Column(String(50), nullable=False)  # 资产类型
    asset_name = Column(String(200), nullable=False)  # 资产名称
    version_number = Column(Integer, nullable=False)  # 版本号

    content = Column(Text)  # 版本内容
    checksum = Column(String(64))  # 内容校验和

    # 评分 - 新增
    score = Column(Float)  # 总分
    score_breakdown = Column(JSON)  # 各维度评分

    # 元数据
    created_by = Column(String(100))  # 创建者 (agent/user)
    change_summary = Column(Text)  # 变更摘要

    # 是否当前版本
    is_current = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
