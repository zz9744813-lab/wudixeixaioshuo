"""
Worker Schemas - Worker状态相关模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkerStatusOut(BaseModel):
    """Worker状态响应"""
    model_config = ConfigDict(from_attributes=True)

    status: str  # running / paused / stopped
    current_task: Optional[Dict[str, Any]] = None

    # 今日统计
    daily_stats: Dict[str, Any] = {}
    uptime: int = 0  # 运行秒数


class WorkerControlRequest(BaseModel):
    """Worker控制请求"""
    model_config = ConfigDict(from_attributes=True)

    action: str = Field(..., pattern="^(start|stop|pause|resume)$")


class WorkerEventOut(BaseModel):
    """Worker事件响应"""
    model_config = ConfigDict(from_attributes=True)

    type: str
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None


class AgentStepOut(BaseModel):
    """Agent步骤状态"""
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    chapter_id: int
    agent: str
    step_index: int
    status: str  # running / completed / failed
    rewrite_round: Optional[int] = None
    tokens: int = 0
    cost: float = 0.0
    error: Optional[str] = None
