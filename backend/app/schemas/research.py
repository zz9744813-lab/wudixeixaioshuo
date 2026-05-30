"""
Research Schemas - 联网研究相关请求/响应模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateResearchRunRequest(BaseModel):
    """创建研究运行请求"""
    topic: str = Field(..., description="研究主题")
    research_type: str = Field(default="pattern", description="研究类型: pattern/comment/trend/style")
    project_id: Optional[int] = None
    run_id: Optional[int] = None


class ResearchRunResponse(BaseModel):
    """研究运行响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: Optional[int] = None
    run_id: Optional[int] = None
    topic: str
    research_type: str
    status: str
    query_plan_json: Optional[Dict[str, Any]] = None
    extracted_summary: Optional[str] = None
    result_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ResearchSourceResponse(BaseModel):
    """研究来源响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    research_run_id: int
    title: Optional[str] = None
    url: str
    source_type: Optional[str] = None
    trust_score: float = 0.5
    excerpt: Optional[str] = None
    used_for: Optional[str] = None
    created_at: Optional[datetime] = None


class KnowledgePatternResponse(BaseModel):
    """知识模式响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    genre: Optional[str] = None
    tag: Optional[str] = None
    pattern_name: str
    pattern_type: str
    description: str
    applicable_scene: Optional[str] = None
    anti_patterns: Optional[str] = None
    source_ids: Optional[List[int]] = None
    confidence: float = 0.5
    created_at: Optional[datetime] = None


class ReaderInsightResponse(BaseModel):
    """读者洞察响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    genre: Optional[str] = None
    insight_type: str
    title: str
    description: str
    evidence: Optional[str] = None
    source_ids: Optional[List[int]] = None
    confidence: float = 0.5
    created_at: Optional[datetime] = None


class TrendReportResponse(BaseModel):
    """趋势报告响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    genre: Optional[str] = None
    platform: Optional[str] = None
    report_title: str
    report_body: str
    trend_tags: Optional[List[str]] = None
    source_ids: Optional[List[int]] = None
    created_at: Optional[datetime] = None


class ApplyToProjectRequest(BaseModel):
    """应用知识到项目请求"""
    knowledge_type: str = Field(..., description="知识类型: pattern/insight/trend")
    knowledge_ids: List[int] = Field(..., description="知识ID列表")
    project_id: int = Field(..., description="目标项目ID")
    apply_to_bible: bool = Field(default=True, description="是否应用到Bible")
    apply_to_critic: bool = Field(default=False, description="是否应用到Critic维度")
    apply_to_prompt: bool = Field(default=False, description="是否应用到Prompt模板")
