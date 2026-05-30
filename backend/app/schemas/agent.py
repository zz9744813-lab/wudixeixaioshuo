"""
Agent Schemas - Agent运行相关请求/响应模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateAgentRunRequest(BaseModel):
    """创建Agent运行请求"""
    user_request: str = Field(..., description="用户创作需求")
    project_id: Optional[int] = None
    mode: str = "autonomous"
    budget_tokens: Optional[int] = None
    budget_cost: Optional[float] = None
    max_steps: int = 30
    max_retries: int = 2
    max_concurrency: int = 3


class AgentRunResponse(BaseModel):
    """Agent运行响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    mode: str
    user_request: str
    project_id: Optional[int] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class AgentRunDetailResponse(BaseModel):
    """Agent运行详情响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    mode: str
    user_request: str
    project_id: Optional[int] = None
    budget_tokens: Optional[int] = None
    budget_cost: Optional[float] = None
    used_tokens: int = 0
    used_cost: float = 0.0
    max_steps: int = 30
    max_retries: int = 2
    max_concurrency: int = 3
    final_report: Optional[str] = None
    error_message: Optional[str] = None
    plans: List[Dict[str, Any]] = []
    steps: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class AgentPlanResponse(BaseModel):
    """Agent计划响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    title: str
    summary: Optional[str] = None
    plan_json: Dict[str, Any]
    planner_model: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class AgentStepResponse(BaseModel):
    """Agent步骤响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    plan_id: int
    step_key: str
    title: str
    tool_name: str
    args_json: Optional[Dict[str, Any]] = None
    depends_on: Optional[List[str]] = None
    status: str
    attempt_count: int = 0
    input_snapshot: Optional[Dict[str, Any]] = None
    output_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AgentReportResponse(BaseModel):
    """Agent运行报告响应"""
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    status: str
    report: Optional[Dict[str, Any]] = None
