"""
Evolution Policy Schemas - Prompt进化策略相关请求/响应模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateEvolutionPolicyRequest(BaseModel):
    """创建进化策略请求"""
    role: str = Field(..., description="角色: draft/critic/rewrite/continuity")
    enabled: bool = True
    min_sample_count: int = 20
    min_average_score: float = 80.0
    max_rewrite_rate: float = 0.4
    trigger_window_days: int = 7
    candidate_count: int = 3
    ab_test_sample_count: int = 10
    min_improvement: float = 3.0
    auto_apply: bool = True
    rollout_ratio: float = 0.2


class UpdateEvolutionPolicyRequest(BaseModel):
    """更新进化策略请求"""
    enabled: Optional[bool] = None
    min_sample_count: Optional[int] = None
    min_average_score: Optional[float] = None
    max_rewrite_rate: Optional[float] = None
    trigger_window_days: Optional[int] = None
    candidate_count: Optional[int] = None
    ab_test_sample_count: Optional[int] = None
    min_improvement: Optional[float] = None
    auto_apply: Optional[bool] = None
    rollout_ratio: Optional[float] = None


class EvolutionPolicyResponse(BaseModel):
    """进化策略响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    enabled: bool
    min_sample_count: int
    min_average_score: float
    max_rewrite_rate: float
    trigger_window_days: int
    candidate_count: int
    ab_test_sample_count: int
    min_improvement: float
    auto_apply: bool
    rollout_ratio: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EvolutionRunResponse(BaseModel):
    """进化运行响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    role: str
    status: str
    diagnosis: Optional[str] = None
    failure_samples_json: Optional[List[Dict[str, Any]]] = None
    candidate_prompts_json: Optional[List[Dict[str, Any]]] = None
    ab_test_result_json: Optional[Dict[str, Any]] = None
    applied_prompt_version_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    rollback_reason: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RollbackEvolutionRequest(BaseModel):
    """回滚进化请求"""
    reason: str = Field(default="手动回滚", description="回滚原因")
