"""
Production Models - 自动排产系统
P4 Phase 5: 24小时生产
"""

from datetime import datetime
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import relationship

from app.database import Base


class ProductionPolicy(Base):
    """生产策略表 - 项目排产配置"""
    __tablename__ = "production_policies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True, index=True)

    # 开关
    enabled = Column(Integer, default=0)  # 是否启用自动排产

    # 每日目标
    target_daily_words = Column(Integer, default=10000)  # 目标日字数
    target_daily_chapters = Column(Integer, default=3)  # 目标日章节数
    max_daily_cost = Column(Float, default=5.0)  # 每日成本上限
    max_daily_tokens = Column(Integer, default=500000)  # 每日token上限

    # 质量阈值
    min_quality_score = Column(Float, default=80.0)  # 最低质量分
    max_rewrite_rounds = Column(Integer, default=2)  # 最大改写轮数
    max_consecutive_failures = Column(Integer, default=3)  # 最大连续失败数

    # 自动行为
    auto_create_next_chapter = Column(Integer, default=1)  # 自动创建下一章
    auto_pause_on_failure = Column(Integer, default=1)  # 失败时自动暂停
    auto_pause_on_budget = Column(Integer, default=1)  # 超预算时自动暂停

    # 运行时间
    active_hours = Column(JSON, default=list)  # 活跃时间段 [[9, 12], [14, 18]]
    priority = Column(Integer, default=2)  # 优先级 1-5

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductionLog(Base):
    """生产日志表 - 排产执行记录"""
    __tablename__ = "production_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)

    # 日志类型
    log_type = Column(String(50), index=True)  # auto_created / paused / resumed / completed / failed

    # 详情
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("generation_tasks.id"), nullable=True)

    # 统计
    words_written = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    # 消息
    message = Column(Text)
    details = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index('idx_production_log_project', 'project_id', 'created_at'),
        Index('idx_production_log_type', 'log_type', 'created_at'),
    )


class ProductionStats(Base):
    """生产统计表 - 每日统计"""
    __tablename__ = "production_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    date = Column(String(10), index=True)  # YYYY-MM-DD

    # 完成情况
    chapters_completed = Column(Integer, default=0)
    words_written = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # 质量
    avg_score = Column(Float, default=0.0)
    rewrite_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # 目标达成率
    word_goal_achievement = Column(Float, default=0.0)  # 0-1
    chapter_goal_achievement = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 唯一约束
    __table_args__ = (
        Index('idx_production_stats_project_date', 'project_id', 'date', unique=True),
    )
