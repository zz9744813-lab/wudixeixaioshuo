"""
Books Router - 书籍/拆书路由
"""

import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.book import Book, BookChapter, BookStatus, SourceType
from app.services.mock_llm_service import mock_llm_service

router = APIRouter()

UPLOAD_DIR = "F:/kelaode/quanzidong/data/uploads"


# Pydantic 模型
class BookCreate(BaseModel):
    title: str
    author_alias: Optional[str] = None
    genre: Optional[str] = None
    source_type: str = "txt"
    target_usage: Optional[str] = None


class BookResponse(BaseModel):
    id: int
    title: str
    author_alias: Optional[str]
    genre: Optional[str]
    source_type: str
    status: str
    total_chapters: int
    total_words: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[BookResponse])
async def list_books(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取书籍列表"""
    query = db.query(Book)
    if status:
        query = query.filter(Book.status == status)
    books = query.offset(skip).limit(limit).all()

    return [
        {
            "id": b.id,
            "title": b.title,
            "author_alias": b.author_alias,
            "genre": b.genre,
            "source_type": b.source_type,
            "status": b.status,
            "total_chapters": b.total_chapters,
            "total_words": b.total_words,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in books
    ]


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    genre: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """上传书籍文件"""
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 保存文件
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 检测文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    source_type_map = {
        ".txt": SourceType.TXT,
        ".md": SourceType.MD,
        ".epub": SourceType.EPUB,
        ".docx": SourceType.DOCX,
        ".pdf": SourceType.PDF,
    }
    source_type = source_type_map.get(ext, SourceType.TXT)

    # 创建书籍记录
    book = Book(
        title=title or os.path.splitext(file.filename)[0],
        genre=genre,
        source_type=source_type,
        file_path=file_path,
        status=BookStatus.IMPORTED,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    return {
        "message": "书籍上传成功",
        "id": book.id,
        "title": book.title,
        "file_path": book.file_path,
    }


@router.post("/")
async def create_book(book: BookCreate, db: Session = Depends(get_db)):
    """创建书籍记录（用于粘贴文本）"""
    db_book = Book(
        title=book.title,
        author_alias=book.author_alias,
        genre=book.genre,
        source_type=book.source_type,
        target_usage=book.target_usage,
        status=BookStatus.IMPORTED,
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)

    return {
        "id": db_book.id,
        "title": db_book.title,
        "status": db_book.status,
    }


@router.get("/{book_id}")
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """获取书籍详情"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    return {
        "id": book.id,
        "title": book.title,
        "author_alias": book.author_alias,
        "genre": book.genre,
        "source_type": book.source_type,
        "status": book.status,
        "total_chapters": book.total_chapters,
        "total_words": book.total_words,
        "analysis_progress": book.analysis_progress,
        "analysis_report": book.analysis_report,
        "tags": book.tags,
        "chapters": [
            {
                "id": c.id,
                "index": c.chapter_index,
                "title": c.title,
                "word_count": c.word_count,
            }
            for c in book.chapters[:20]  # 只返回前20章
        ],
        "created_at": book.created_at.isoformat() if book.created_at else None,
    }


@router.post("/{book_id}/split")
async def split_book(book_id: int, db: Session = Depends(get_db)):
    """分章处理"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    book.status = BookStatus.SPLITTING
    db.commit()

    # 模拟分章处理
    import asyncio
    await asyncio.sleep(1)

    # 创建模拟章节
    for i in range(1, 121):
        chapter = BookChapter(
            book_id=book.id,
            chapter_index=i,
            title=f"第{i}章",
            content=f"这是第{i}章的内容...",
            word_count=3000 + (i % 10) * 100,
        )
        db.add(chapter)

    book.total_chapters = 120
    book.total_words = 385420
    book.status = BookStatus.COMPLETED
    db.commit()

    return {
        "message": "分章完成",
        "book_id": book.id,
        "total_chapters": book.total_chapters,
        "total_words": book.total_words,
    }


@router.post("/{book_id}/analyze")
async def analyze_book(book_id: int, db: Session = Depends(get_db)):
    """开始拆书分析"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    book.status = BookStatus.ANALYZING
    db.commit()

    # 模拟分析过程
    import asyncio
    await asyncio.sleep(2)

    # 使用 Mock LLM 生成分析报告
    response = await mock_llm_service.generate(
        prompt=f"分析书籍: {book.title}",
        role="analyze"
    )

    book.analysis_report = response["content"]
    book.analysis_progress = 100
    book.status = BookStatus.COMPLETED
    from datetime import datetime
    book.analyzed_at = datetime.utcnow()
    db.commit()

    return {
        "message": "分析完成",
        "book_id": book.id,
        "report_summary": book.analysis_report[:500] + "...",
    }


@router.get("/{book_id}/chapters/{chapter_id}")
async def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    """获取章节详情"""
    chapter = db.query(BookChapter).filter(BookChapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    return {
        "id": chapter.id,
        "book_id": chapter.book_id,
        "chapter_index": chapter.chapter_index,
        "title": chapter.title,
        "content": chapter.content[:2000] + "..." if len(chapter.content) > 2000 else chapter.content,
        "word_count": chapter.word_count,
        "summary": chapter.summary,
    }


@router.delete("/{book_id}")
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    """删除书籍"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 删除文件
    if book.file_path and os.path.exists(book.file_path):
        os.remove(book.file_path)

    db.delete(book)
    db.commit()

    return {"message": "书籍已删除", "id": book_id}
