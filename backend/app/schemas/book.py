"""
Book Schemas - 书籍相关模型
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    """书籍基础字段"""
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=200)
    author_alias: Optional[str] = None
    genre: Optional[str] = None


class BookCreate(BookBase):
    """创建书籍请求"""
    source_type: str = "txt"
    target_usage: Optional[str] = None


class BookOut(BookBase):
    """书籍响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    status: str
    total_chapters: int
    total_words: int
    analysis_progress: int = 0
    created_at: Optional[datetime] = None


class BookDetail(BookOut):
    """书籍详情"""
    model_config = ConfigDict(from_attributes=True)

    analysis_report: Optional[str] = None
    tags: List[str] = []
    chapters: List["BookChapterOut"] = []


class BookChapterOut(BaseModel):
    """书籍章节响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_index: int
    title: str
    word_count: int
    summary: Optional[str] = None
    structure_analysis: Optional[Any] = None
    character_mentions: List[str] = []
    plot_points: List[str] = []


class BookUploadResponse(BaseModel):
    """书籍上传响应"""
    model_config = ConfigDict(from_attributes=True)

    message: str
    id: int
    title: str
    stored_filename: str
    size_bytes: int
    total_words: int
    content_preview: str
