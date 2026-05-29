"""
Chapter Schemas - 章节相关模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChapterBase(BaseModel):
    """章节基础字段"""
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=300)
    chapter_index: int = Field(..., ge=1)


class ChapterCreate(ChapterBase):
    """创建章节请求"""
    pass


class ChapterUpdate(BaseModel):
    """更新章节请求"""
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=300)
    status: Optional[str] = None
    final_content: Optional[str] = None


class ChapterOut(ChapterBase):
    """章节响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str

    # 内容
    final_content: Optional[str] = None
    final_word_count: int = 0

    # 评分
    total_score: Optional[float] = None
    plot_progress_score: Optional[float] = None
    character_consistency_score: Optional[float] = None
    pacing_score: Optional[float] = None
    hook_score: Optional[float] = None
    emotional_reward_score: Optional[float] = None
    style_consistency_score: Optional[float] = None
    continuity_score: Optional[float] = None
    clarity_score: Optional[float] = None
    readability_score: Optional[float] = None

    # 版本
    current_version: int = 0
    best_version: int = 0

    # 时间戳
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class ChapterList(BaseModel):
    """章节列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_index: int
    title: str
    status: str
    final_word_count: int
    total_score: Optional[float] = None
    created_at: datetime


class ChapterVersionOut(BaseModel):
    """章节版本响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_id: int
    version_number: int

    # 内容
    plan_content: Optional[str] = None
    draft_content: Optional[str] = None
    final_content: Optional[str] = None

    # 评分
    total_score: Optional[float] = None
    critic_report: Optional[str] = None
    continuity_report: Optional[str] = None

    # 元数据
    rewrite_count: int = 0
    improvement_from_last: Optional[float] = None
    is_accepted: int = 0
    acceptance_reason: Optional[str] = None

    created_at: datetime
