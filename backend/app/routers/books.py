"""
Books Router - 书籍/拆书路由
"""

import os
import re
import shutil
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.book import Book, BookChapter, BookStatus, SourceType
from app.services.openai_llm_service import llm_manager

router = APIRouter()

# 使用相对路径
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")


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

    # 读取文件内容统计
    content_preview = ""
    total_words = 0
    try:
        content_preview = read_file_content(file_path, source_type, max_chars=1000)
        total_words = len(content_preview)  # 粗略估计
    except Exception as e:
        print(f"读取文件预览失败: {e}")

    # 创建书籍记录
    book = Book(
        title=title or os.path.splitext(file.filename)[0],
        genre=genre,
        source_type=source_type,
        file_path=file_path,
        status=BookStatus.IMPORTED,
        total_words=total_words,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    return {
        "message": "书籍上传成功",
        "id": book.id,
        "title": book.title,
        "file_path": book.file_path,
        "total_words": total_words,
        "content_preview": content_preview[:500] + "..." if len(content_preview) > 500 else content_preview,
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
    """智能分章 - 读取真实文件内容并使用 LLM 分析章节结构"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    if not book.file_path or not os.path.exists(book.file_path):
        raise HTTPException(status_code=400, detail="书籍文件不存在")

    book.status = BookStatus.SPLITTING
    db.commit()

    try:
        # 1. 读取完整文件内容
        full_content = read_file_content(book.file_path, book.source_type)
        if not full_content:
            raise HTTPException(status_code=400, detail="无法读取文件内容")

        # 2. 使用 LLM 分析章节结构
        llm_manager.init_from_db(db)

        # 先分析整体结构
        structure_prompt = f"""请分析以下小说文本的章节结构。

文本内容（前10000字符）：
{full_content[:10000]}

请识别：
1. 章节标题的模式（如"第X章"、"Chapter X"等）
2. 预估总章节数
3. 章节分隔的特征

以JSON格式返回：
{{
    "chapter_pattern": "章节标题正则表达式",
    "estimated_chapters": 数字,
    "split_strategy": "auto|regex|llm"
}}"""

        structure_response = await llm_manager.generate(
            prompt=structure_prompt,
            role="split",
            temperature=0.3,
            max_tokens=1000
        )

        # 3. 执行分章
        chapters = smart_split_chapters(full_content, structure_response.get("content", ""))

        # 4. 保存章节到数据库
        for idx, (title, content) in enumerate(chapters, 1):
            chapter = BookChapter(
                book_id=book.id,
                chapter_index=idx,
                title=title,
                content=content,
                word_count=len(content),
            )
            db.add(chapter)

        book.total_chapters = len(chapters)
        book.total_words = sum(len(content) for _, content in chapters)
        book.status = BookStatus.SPLIT_COMPLETED if chapters else BookStatus.IMPORTED
        db.commit()

        return {
            "message": f"分章完成，共识别 {len(chapters)} 章",
            "book_id": book.id,
            "total_chapters": book.total_chapters,
            "total_words": book.total_words,
            "chapters_preview": [
                {"index": i+1, "title": title, "word_count": len(content)}
                for i, (title, content) in enumerate(chapters[:10])
            ],
        }

    except Exception as e:
        book.status = BookStatus.IMPORTED
        db.commit()
        raise HTTPException(status_code=500, detail=f"分章失败: {str(e)}")


@router.post("/{book_id}/analyze")
async def analyze_book(book_id: int, db: Session = Depends(get_db)):
    """开始拆书分析 - 使用真实 LLM 分析书籍"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 检查是否有章节
    if book.total_chapters == 0:
        raise HTTPException(status_code=400, detail="请先进行分章处理")

    book.status = BookStatus.ANALYZING
    book.analysis_progress = 0
    db.commit()

    try:
        # 初始化 LLM
        llm_manager.init_from_db(db)

        # 获取前5章内容作为样本
        sample_chapters = db.query(BookChapter).filter(
            BookChapter.book_id == book_id
        ).order_by(BookChapter.chapter_index).limit(5).all()

        sample_text = "\n\n".join([
            f"【{ch.title}】\n{ch.content[:2000]}"
            for ch in sample_chapters
        ])

        # 更新进度
        book.analysis_progress = 20
        db.commit()

        # 1. 分析叙事模型
        narrative_prompt = f"""请分析以下小说片段的叙事模型：

{sample_text[:5000]}

请分析：
1. 叙事视角（第一人称/第三人称/多视角）
2. 叙事结构（线性/非线性/多线并进）
3. 主要冲突类型
4. 节奏特点

以结构化格式返回。"""

        narrative_response = await llm_manager.generate(
            prompt=narrative_prompt,
            role="analyze",
            temperature=0.5,
            max_tokens=1500
        )

        book.analysis_progress = 50
        db.commit()

        # 2. 分析人物模型
        character_prompt = f"""请分析以下小说片段的人物塑造方式：

{sample_text[:5000]}

请分析：
1. 主要人物类型（成长型/智慧型/反派型等）
2. 人物塑造手法（外貌/对话/行动/心理）
3. 人物关系网络
4. 人物弧光设计

以结构化格式返回。"""

        character_response = await llm_manager.generate(
            prompt=character_prompt,
            role="analyze",
            temperature=0.5,
            max_tokens=1500
        )

        book.analysis_progress = 80
        db.commit()

        # 3. 分析爽点机制
        hook_prompt = f"""请分析以下小说片段的爽点/钩子设计：

{sample_text[:5000]}

请分析：
1. 主要爽点类型（能力觉醒/打脸/身份揭示/悬念等）
2. 钩子设置频率和位置
3. 情绪节奏控制
4. 可迁移的写作技巧

提取3-5个具体的技巧卡片，包含：技巧名称、描述、适用场景。"""

        hook_response = await llm_manager.generate(
            prompt=hook_prompt,
            role="analyze",
            temperature=0.5,
            max_tokens=2000
        )

        # 组合分析报告
        report = f"""# 《{book.title}》拆书分析报告

## 一、叙事模型分析

{narrative_response.get('content', '')}

## 二、人物模型分析

{character_response.get('content', '')}

## 三、爽点机制与技巧提取

{hook_response.get('content', '')}

---
分析完成时间：{datetime.utcnow().isoformat()}
分析样本：前{len(sample_chapters)}章
"""

        book.analysis_report = report
        book.analysis_progress = 100
        book.status = BookStatus.COMPLETED
        book.analyzed_at = datetime.utcnow()
        db.commit()

        return {
            "message": "分析完成",
            "book_id": book.id,
            "analysis_summary": {
                "narrative_model": narrative_response.get('content', '')[:200] + "...",
                "character_model": character_response.get('content', '')[:200] + "...",
                "hooks_count": hook_response.get('content', '').count('技巧'),
            },
            "report_length": len(report),
        }

    except Exception as e:
        book.status = BookStatus.SPLIT_COMPLETED
        book.analysis_progress = 0
        db.commit()
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


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


# ========== 辅助函数 ==========

def read_file_content(file_path: str, source_type: str, max_chars: int = None) -> str:
    """
    读取文件内容

    Args:
        file_path: 文件路径
        source_type: 文件类型
        max_chars: 最大读取字符数（None表示读取全部）

    Returns:
        文件内容文本
    """
    content = ""

    try:
        if source_type == SourceType.TXT or source_type == "txt":
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read(max_chars) if max_chars else f.read()
                    break
                except UnicodeDecodeError:
                    continue

        elif source_type == SourceType.MD or source_type == "md":
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_chars) if max_chars else f.read()

        elif source_type == SourceType.EPUB or source_type == "epub":
            try:
                import ebooklib
                from ebooklib import epub
                book = epub.read_epub(file_path)
                texts = []
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        # 简单提取文本（去除HTML标签）
                        html = item.get_content().decode('utf-8', errors='ignore')
                        text = re.sub(r'<[^>]+>', '', html)
                        text = re.sub(r'\s+', '\n', text)
                        texts.append(text)
                content = '\n'.join(texts)
                if max_chars:
                    content = content[:max_chars]
            except Exception as e:
                print(f"EPUB读取失败: {e}")
                content = ""

        elif source_type == SourceType.DOCX or source_type == "docx":
            try:
                from docx import Document
                doc = Document(file_path)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                content = '\n'.join(paragraphs)
                if max_chars:
                    content = content[:max_chars]
            except Exception as e:
                print(f"DOCX读取失败: {e}")
                content = ""

        elif source_type == SourceType.PDF or source_type == "pdf":
            try:
                import PyPDF2
                texts = []
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        texts.append(page.extract_text() or "")
                content = '\n'.join(texts)
                if max_chars:
                    content = content[:max_chars]
            except Exception as e:
                print(f"PDF读取失败: {e}")
                content = ""

        # 清理内容
        content = clean_text(content)
        return content

    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return ""


def clean_text(text: str) -> str:
    """清理文本内容"""
    # 移除多余空白
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 移除特殊字符
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    return text.strip()


def smart_split_chapters(content: str, llm_analysis: str) -> List[tuple]:
    """
    智能分章

    Args:
        content: 完整文本内容
        llm_analysis: LLM 分析结果

    Returns:
        章节列表 [(title, content), ...]
    """
    chapters = []

    # 1. 尝试常见的章节标题模式
    patterns = [
        # 中文数字章节
        (r'(?:^|\n)\s*第[一二三四五六七八九十百千万零\d]+章[\s:：]*(.*?)(?=\n|$)', "第X章"),
        # 阿拉伯数字章节
        (r'(?:^|\n)\s*第\s*(\d+)\s*章[\s:：]*(.*?)(?=\n|$)', "第X章"),
        # Chapter X
        (r'(?:^|\n)\s*Chapter\s+(\d+)[\s:：]*(.*?)(?=\n|$)', "Chapter X"),
        # 章节X
        (r'(?:^|\n)\s*章节\s*(\d+)[\s:：]*(.*?)(?=\n|$)', "章节X"),
        # X. 标题
        (r'(?:^|\n)\s*(\d+)[\.\s]+([^\n]{1,30})(?=\n|$)', "X. 标题"),
        # 第X章 无标题
        (r'(?:^|\n)\s*第\s*(\d+)\s*章\s*(?=\n|$)', "第X章"),
    ]

    best_matches = []
    best_pattern = None

    for pattern, pattern_name in patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
        if len(matches) > len(best_matches) and len(matches) >= 3:
            best_matches = matches
            best_pattern = (pattern, pattern_name)

    if best_matches:
        # 使用最佳匹配模式分章
        for i, match in enumerate(best_matches):
            start = match.start()
            end = best_matches[i + 1].start() if i + 1 < len(best_matches) else len(content)

            # 提取标题
            groups = match.groups()
            if len(groups) >= 2:
                chapter_num = groups[0] if groups[0].isdigit() else str(i + 1)
                chapter_title = groups[1].strip() if groups[1] else f"第{chapter_num}章"
            else:
                chapter_num = str(i + 1)
                chapter_title = f"第{chapter_num}章"

            # 提取内容
            chapter_content = content[start:end].strip()

            chapters.append((chapter_title, chapter_content))

    # 如果没有找到章节，按固定长度分章
    if not chapters:
        chapter_size = 3000  # 每章约3000字符
        for i in range(0, len(content), chapter_size):
            chunk = content[i:i + chapter_size]
            chapter_num = (i // chapter_size) + 1
            # 尝试找到第一行的标题
            lines = chunk.split('\n', 1)
            if len(lines) > 1 and len(lines[0]) < 50:
                title = lines[0].strip()
                chapter_content = lines[1].strip()
            else:
                title = f"第{chapter_num}章"
                chapter_content = chunk
            chapters.append((title, chapter_content))

    return chapters
