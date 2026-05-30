"""
SubAgent Schemas - 子Agent任务相关请求/响应模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SubAgentTaskResponse(BaseModel):
    """子Agent任务响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    parent_step_id: Optional[int] = None
    task_type: str
    title: str
    role: str
    status: str
    context_json: Optional[Dict[str, Any]] = None
    input_prompt: Optional[str] = None
    output_text: Optional[str] = None
    parsed_output: Optional[Dict[str, Any]] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    token_count: int = 0
    cost: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SubAgentTreeResponse(BaseModel):
    """子Agent任务树响应"""
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    status: str
    tasks_by_parent_step: Dict[str, List[SubAgentTaskResponse]]


class SubAgentSummaryResponse(BaseModel):
    """子Agent汇总响应"""
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    total: int
    succeeded: int
    failed: int
    cancelled: int
    results: List[SubAgentTaskResponse]
