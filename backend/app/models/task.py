"""
Task Models - 生成任务模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TaskType(str, PyEnum):
    """任务类型"""
    PLAN = "plan"           # 规划
    DRAFT = "draft"         # 起草
    CRITIC = "critic"       # 审稿
    REWRITE = "rewrite"     # 改稿
    CONTINUITY = "continuity"  # 连续性检查
    LEARN = "learn"         # 学习
    SPLIT = "split"         # 分章
    ANALYZE = "analyze"     # 分析


class TaskStatus(str, PyEnum):
    """任务状态"""
    PENDING = "pending"       # 待处理
    RUNNING = "running"       # 运行中
    PAUSED = "paused"         # 暂停
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


class TaskPriority(int, PyEnum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class GenerationTask(Base):
    """生成任务表"""
    __tablename__ = "generation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    chapter_id = Column(Integer, ForeignKey("chapters.id"))

    task_type = Column(String(30), nullable=False)
    status = Column(String(30), default=TaskStatus.PENDING)
    priority = Column(Integer, default=TaskPriority.NORMAL)

    # 任务配置
    target_agent = Column(String(100))  # 目标Agent
    model_config_id = Column(Integer)  # 使用的模型配置

    # 统计
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)

    # 成本
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    token_used = Column(Integer, default=0)

    # 错误信息
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)

    # 关系
    project = relationship("Project", back_populates="tasks")
    chapter = relationship("Chapter", back_populates="tasks")
    steps = relationship("GenerationStep", back_populates="task", order_by="GenerationStep.step_index")


class GenerationStep(Base):
    """生成步骤表 - 记录每个Agent的执行过程"""
    __tablename__ = "generation_steps"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("generation_tasks.id"))
    chapter_id = Column(Integer, ForeignKey("chapters.id"))

    step_index = Column(Integer, nullable=False)  # 步骤序号
    agent_name = Column(String(100), nullable=False)  # Agent名称

    # 输入输出
    input_prompt = Column(Text)  # 输入提示词
    raw_output = Column(Text)  # 原始输出
    parsed_output = Column(Text)  # 解析后的输出

    # 评分
    score = Column(Float)  # 评分
    score_breakdown = Column(JSON)  # 评分详情

    # 模型信息
    model_name = Column(String(200))
    provider_name = Column(String(100))

    # Token统计
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)

    # 耗时
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 错误信息
    error_message = Column(Text)

    # 产物文件路径
    artifact_path = Column(String(500))

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship("GenerationTask", back_populates="steps")
    chapter = relationship("Chapter", back_populates="steps")
