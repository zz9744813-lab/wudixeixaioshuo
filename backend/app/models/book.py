"""
Book Models - 书籍/拆书学习模型
"""

from datetime import datetime, timezone
from app.utils.time_utils import utc_now
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


class BookStatus(str, PyEnum):
    """书籍状态"""
    IMPORTED = "imported"           # 已导入
    PROCESSING = "processing"       # 处理中
    SPLITTING = "splitting"         # 分章中
    SPLIT_COMPLETED = "split_completed"  # 分章完成
    ANALYZING = "analyzing"         # 分析中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"               # 失败


class SourceType(str, PyEnum):
    """来源类型"""
    TXT = "txt"
    EPUB = "epub"
    DOCX = "docx"
    MD = "md"
    PDF = "pdf"
    URL = "url"
    PASTE = "paste"


class Book(Base):
    """书籍表"""
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    author_alias = Column(String(200))  # 作者别名
    genre = Column(String(100))  # 题材
    source_type = Column(String(20), default=SourceType.TXT)
    file_path = Column(String(500))  # 文件路径
    original_url = Column(String(1000))  # 原始URL
    status = Column(String(20), default=BookStatus.IMPORTED)

    # 统计
    total_chapters = Column(Integer, default=0)
    total_words = Column(Integer, default=0)

    # 标签
    tags = Column(JSON, default=list)
    target_usage = Column(String(200))  # 目标用途

    # 分析进度
    analysis_progress = Column(Integer, default=0)  # 分析进度百分比
    analysis_report = Column(Text)  # 分析报告摘要

    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    analyzed_at = Column(DateTime)

    # 关系
    chapters = relationship("BookChapter", back_populates="book", order_by="BookChapter.chapter_index", cascade="all, delete-orphan")
    technique_cards = relationship(
        "TechniqueCard",
        back_populates="book",
        cascade="all, delete-orphan"
    )


class BookChapter(Base):
    """书籍章节表"""
    __tablename__ = "book_chapters"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"))
    chapter_index = Column(Integer, nullable=False)
    title = Column(String(300))
    content = Column(Text)  # 原始内容
    summary = Column(Text)  # 章节摘要
    word_count = Column(Integer, default=0)

    # 分析结果
    structure_analysis = Column(JSON)  # 结构分析
    character_mentions = Column(JSON)  # 提及的人物
    plot_points = Column(JSON)  # 剧情点
    emotional_beats = Column(JSON)  # 情绪节拍
    hooks = Column(JSON)  # 钩子分析

    # 时间戳
    created_at = Column(DateTime, default=utc_now)

    # 关系
    book = relationship("Book", back_populates="chapters")
