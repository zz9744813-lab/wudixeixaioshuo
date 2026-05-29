"""
Daily Usage Stats Model - 每日使用统计
P2-5: 成本统计持久化，支持预算硬上限
"""

from datetime import date
from typing import Optional

from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class DailyUsageStats(Base):
    """每日使用统计表"""
    __tablename__ = "daily_usage_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)  # 统计日期
    project_id = Column(Integer, index=True, nullable=True)  # 项目ID，None表示全局统计

    # 模型信息
    provider = Column(String(100))  # 提供商名称
    model_name = Column(String(200))  # 模型名称

    # Token 统计
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 成本统计
    cost = Column(Float, default=0.0)  # 成本（美元）

    # 任务统计
    chapter_count = Column(Integer, default=0)  # 生成章节数
    task_count = Column(Integer, default=0)  # 任务数
    success_count = Column(Integer, default=0)  # 成功数
    failure_count = Column(Integer, default=0)  # 失败数

    # 字数统计
    word_count = Column(Integer, default=0)  # 生成字数

    # 时间戳
    created_at = Column(Date, default=utc_now)
    updated_at = Column(Date, default=utc_now, onupdate=utc_now)

    # 唯一约束：日期 + 项目 + 提供商 + 模型
    __table_args__ = (
        UniqueConstraint('date', 'project_id', 'provider', 'model_name', name='uix_daily_stats'),
    )
