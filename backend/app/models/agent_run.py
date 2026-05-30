"""
Agent Run Models - 自主Agent运行模型
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class AgentRunStatus(str, PyEnum):
    """Agent运行状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 运行中
    SUCCEEDED = "succeeded"   # 成功完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"    # 已取消
    PAUSED = "paused"         # 已暂停(预算/步骤超限)


class AgentRunMode(str, PyEnum):
    """Agent运行模式"""
    AUTONOMOUS = "autonomous"       # 完全自主
    REQUIRE_APPROVAL = "require_approval"  # 执行前需确认


class AgentRun(Base):
    """Agent运行记录表 - 一次主Agent自主运行"""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # 用户原始需求
    user_request = Column(Text, nullable=False)
    mode = Column(String(32), default=AgentRunMode.AUTONOMOUS)
    status = Column(String(32), default=AgentRunStatus.PENDING)

    # 预算控制
    budget_tokens = Column(Integer, nullable=True)      # token预算上限
    budget_cost = Column(Float, nullable=True)          # 费用预算上限(USD)
    used_tokens = Column(Integer, default=0)              # 已用token
    used_cost = Column(Float, default=0.0)              # 已用费用

    # 执行限制
    max_steps = Column(Integer, default=30)             # 最大步骤数
    max_retries = Column(Integer, default=2)            # 最大重试次数
    max_concurrency = Column(Integer, default=3)        # 最大并发数

    # 执行结果
    final_report = Column(Text, nullable=True)           # 最终报告
    error_message = Column(Text, nullable=True)         # 错误信息

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    project = relationship("Project", back_populates="agent_runs")
    plans = relationship("AgentPlan", back_populates="run", cascade="all, delete-orphan")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")
    subagent_tasks = relationship("SubAgentTask", back_populates="run", cascade="all, delete-orphan")
    subagent_results = relationship("SubAgentResult", back_populates="run", cascade="all, delete-orphan")


class AgentPlanStatus(str, PyEnum):
    """Agent计划状态"""
    CREATED = "created"       # 已创建
    APPROVED = "approved"     # 已批准
    EXECUTING = "executing"   # 执行中
    DONE = "done"             # 完成
    FAILED = "failed"         # 失败


class AgentPlan(Base):
    """Agent计划表 - 主Agent生成的计划DAG"""
    __tablename__ = "agent_plans"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    plan_json = Column(JSON, nullable=False)           # DAG原始结构
    planner_model = Column(String(128), nullable=True)   # 使用的规划模型
    status = Column(String(32), default=AgentPlanStatus.CREATED)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    run = relationship("AgentRun", back_populates="plans")
    steps = relationship("AgentStep", back_populates="plan", cascade="all, delete-orphan")


class AgentStepStatus(str, PyEnum):
    """Agent步骤状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 运行中
    SUCCEEDED = "succeeded"   # 成功
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 已跳过


class AgentStep(Base):
    """Agent步骤表 - 计划中的每一步"""
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("agent_plans.id"), nullable=False, index=True)

    step_key = Column(String(64), nullable=False)       # 步骤唯一标识
    title = Column(String(255), nullable=False)           # 步骤标题
    tool_name = Column(String(128), nullable=False)      # 调用的工具名
    args_json = Column(JSON, nullable=True)              # 工具参数
    depends_on = Column(JSON, nullable=True)             # 依赖的step_key列表

    status = Column(String(32), default=AgentStepStatus.PENDING)
    attempt_count = Column(Integer, default=0)           # 尝试次数

    input_snapshot = Column(JSON, nullable=True)       # 执行前的输入快照
    output_json = Column(JSON, nullable=True)           # 执行输出
    error_message = Column(Text, nullable=True)        # 错误信息

    # Token和成本统计
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # 关系
    run = relationship("AgentRun", back_populates="steps")
    plan = relationship("AgentPlan", back_populates="steps")
    subagent_tasks = relationship("SubAgentTask", back_populates="parent_step", cascade="all, delete-orphan")


class SubAgentTaskStatus(str, PyEnum):
    """子Agent任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubAgentTask(Base):
    """子Agent任务表"""
    __tablename__ = "subagent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    parent_step_id = Column(Integer, ForeignKey("agent_steps.id"), nullable=True, index=True)

    task_type = Column(String(64), nullable=False)       # draft/critic/continuity/research/summary
    title = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False)             # planner/draft/critic/research...
    status = Column(String(32), default=SubAgentTaskStatus.PENDING)

    context_json = Column(JSON, nullable=True)           # 上下文数据
    input_prompt = Column(Text, nullable=True)          # 输入prompt
    output_text = Column(Text, nullable=True)            # 输出文本
    parsed_output = Column(JSON, nullable=True)          # 解析后的结构化输出

    # 使用的模型信息
    provider_name = Column(String(128), nullable=True)
    model_name = Column(String(128), nullable=True)
    token_count = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # 关系
    run = relationship("AgentRun", back_populates="subagent_tasks")
    parent_step = relationship("AgentStep", back_populates="subagent_tasks")
