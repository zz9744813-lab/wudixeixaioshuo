"""
Project Schemas - 项目相关模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """项目基础字段"""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    genre: str = Field(..., min_length=1, max_length=100)
    target_reader: Optional[str] = None


class ProjectCreate(ProjectBase):
    """创建项目请求"""
    total_word_goal: int = Field(default=100000, ge=1000)
    daily_word_goal: int = Field(default=3000, ge=100)
    chapter_word_goal: int = Field(default=3000, ge=100)
    daily_chapter_goal: int = Field(default=1, ge=1)

    # 质量目标
    plot_progress_intensity: int = Field(default=7, ge=1, le=10)
    satisfaction_density: int = Field(default=7, ge=1, le=10)
    emotional_tension: int = Field(default=6, ge=1, le=10)
    writing_delicacy: int = Field(default=6, ge=1, le=10)


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, min_length=1, max_length=100)
    target_reader: Optional[str] = None
    status: Optional[str] = None
    total_word_goal: Optional[int] = Field(None, ge=1000)
    daily_word_goal: Optional[int] = Field(None, ge=100)
    daily_budget: Optional[float] = Field(None, ge=0)


class ProjectOut(ProjectBase):
    """项目响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_word_goal: int
    daily_word_goal: int
    chapter_word_goal: int
    daily_chapter_goal: int
    current_chapter_index: int = 0
    total_words_written: int = 0
    status: str

    # 预算
    daily_budget: float = 10.0
    total_budget: Optional[float] = None

    # 质量目标
    plot_progress_intensity: int
    satisfaction_density: int
    emotional_tension: int
    writing_delicacy: int
    dialogue_ratio: int
    description_ratio: int
    commercial_pace: int
    adult_content_scale: int

    # 状态
    quality_threshold: int
    max_rewrite_rounds: int

    # 时间戳
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 统计
    chapter_count: Optional[int] = None
    task_count: Optional[int] = None


class ProjectList(BaseModel):
    """项目列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    genre: str
    status: str
    total_words_written: int
    total_word_goal: int
    created_at: datetime


class NovelBibleOut(BaseModel):
    """小说圣经响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    world_setting: Optional[str] = None
    world_rules: List[Any] = []
    timeline: List[Any] = []
    characters: List[Any] = []
    character_relationships: List[Any] = []
    main_plot: Optional[str] = None
    sub_plots: List[Any] = []
    foreshadowing: List[Any] = []
    style_boundaries: List[Any] = []
    tone_guidelines: Optional[str] = None
    forbidden_items: List[Any] = []
    volume_outline: List[Any] = []
    chapter_outline: List[Any] = []
    created_at: datetime
    updated_at: datetime


class NovelBibleUpdate(BaseModel):
    """更新小说圣经请求"""
    model_config = ConfigDict(from_attributes=True)

    world_setting: Optional[str] = None
    world_rules: Optional[List[Any]] = None
    timeline: Optional[List[Any]] = None
    characters: Optional[List[Any]] = None
    character_relationships: Optional[List[Any]] = None
    main_plot: Optional[str] = None
    sub_plots: Optional[List[Any]] = None
    foreshadowing: Optional[List[Any]] = None
    style_boundaries: Optional[List[Any]] = None
    tone_guidelines: Optional[str] = None
    forbidden_items: Optional[List[Any]] = None
    volume_outline: Optional[List[Any]] = None
    chapter_outline: Optional[List[Any]] = None
