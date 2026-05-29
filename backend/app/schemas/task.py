"""
Task Schemas - 任务相关模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GenerationTaskOut(BaseModel):
    """生成任务响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    chapter_id: int
    task_type: str

    # 状态
    status: str
    priority: int

    # 进度
    completed_steps: int = 0
    total_steps: int = 0

    # 资源使用
    token_used: int = 0
    actual_cost: float = 0.0

    # 时间戳
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # 重试
    retry_count: int = 0
    max_retries: int = 3

    # 错误信息
    error_message: Optional[str] = None

    # 关联数据
    chapter_title: Optional[str] = None
    chapter_index: Optional[int] = None


class GenerationTaskDetail(GenerationTaskOut):
    """任务详情（包含步骤）"""
    model_config = ConfigDict(from_attributes=True)

    steps: List["GenerationStepOut"] = []


class GenerationStepOut(BaseModel):
    """生成步骤响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    chapter_id: int
    step_index: int
    agent_name: str

    # 输入输出
    input_prompt: Optional[str] = None
    raw_output: Optional[str] = None
    parsed_output: Optional[str] = None

    # 评分
    score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None

    # 模型信息
    model_name: str
    provider_name: str
    input_tokens: int = 0
    output_tokens: int = 0

    # 时间
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: int = 0

    # 错误
    error_message: Optional[str] = None


class TaskCreate(BaseModel):
    """创建任务请求"""
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    chapter_id: int
    task_type: str = "chapter_generation"
    priority: int = Field(default=5, ge=1, le=10)


class TaskStatusUpdate(BaseModel):
    """更新任务状态请求"""
    model_config = ConfigDict(from_attributes=True)

    status: str
    error_message: Optional[str] = None


class TaskList(BaseModel):
    """任务列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    chapter_id: int
    task_type: str
    status: str
    priority: int
    completed_steps: int
    total_steps: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    chapter_title: Optional[str] = None
    chapter_index: Optional[int] = None
