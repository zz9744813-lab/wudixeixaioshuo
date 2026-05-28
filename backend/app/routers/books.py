"""
Books Router - 书籍/拆书路由
"""

import json
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

from app.models.technique import TechniqueCard, TechniqueCategory

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
                "chapter_index": c.chapter_index,
                "title": c.title,
                "word_count": c.word_count,
                "summary": c.summary,
                "structure_analysis": c.structure_analysis,
                "character_mentions": c.character_mentions,
                "plot_points": c.plot_points,
                "emotional_beats": c.emotional_beats,
                "hooks": c.hooks,
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
    """开始拆书分析 - 使用真实 LLM 分析书籍，并将章节级分析写回数据库"""
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

        book.analysis_progress = 70
        db.commit()

        # 3. 逐个章节分析 - 写回章节字段
        all_chapters = db.query(BookChapter).filter(
            BookChapter.book_id == book_id
        ).order_by(BookChapter.chapter_index).all()

        for idx, chapter in enumerate(all_chapters):
            # 章节级分析
            chapter_prompt = f"""请分析以下章节的内容，提取关键信息：

章节标题：{chapter.title}
章节内容（前3000字）：
{chapter.content[:3000]}

请用JSON格式返回：
{{
    "summary": "章节摘要（200字以内）",
    "structure_analysis": {{"opening": "开头手法", "development": "发展方式", "climax": "高潮/转折", "ending": "结尾设计"}},
    "character_mentions": ["人物A", "人物B"],
    "plot_points": ["剧情点1", "剧情点2"],
    "emotional_beats": [{{"position": "开头/中间/结尾", "emotion": "情绪类型", "intensity": 1-10}}],
    "hooks": [{{"type": "悬念类型", "description": "钩子描述", "position": "位置"}}]
}}

只返回JSON，不要其他内容。"""

            try:
                chapter_response = await llm_manager.generate(
                    prompt=chapter_prompt,
                    role="analyze",
                    temperature=0.3,
                    max_tokens=1500
                )

                import json
                content = chapter_response.get('content', '{}')
                # 尝试提取JSON
                try:
                    # 查找JSON块
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        chapter_analysis = json.loads(json_match.group())
                    else:
                        chapter_analysis = json.loads(content)

                    # 写回章节字段
                    chapter.summary = chapter_analysis.get('summary', '')
                    chapter.structure_analysis = chapter_analysis.get('structure_analysis')
                    chapter.character_mentions = chapter_analysis.get('character_mentions', [])
                    chapter.plot_points = chapter_analysis.get('plot_points', [])
                    chapter.emotional_beats = chapter_analysis.get('emotional_beats', [])
                    chapter.hooks = chapter_analysis.get('hooks', [])

                except json.JSONDecodeError:
                    print(f"章节 {chapter.chapter_index} JSON解析失败")
                    chapter.summary = content[:500] if content else ""

            except Exception as e:
                print(f"章节 {chapter.chapter_index} 分析失败: {e}")

            # 每10章提交一次，避免长时间锁定
            if idx % 10 == 0:
                db.commit()
                book.analysis_progress = 70 + (idx / len(all_chapters)) * 20
                db.commit()

        db.commit()
        book.analysis_progress = 90
        db.commit()

        # 4. 分析爽点机制
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

## 四、章节分析统计

- 总章节数：{len(all_chapters)}
- 已分析章节：{len([c for c in all_chapters if c.summary])}
- 提取人物：{sum(len(c.character_mentions or []) for c in all_chapters)}
- 识别剧情点：{sum(len(c.plot_points or []) for c in all_chapters)}

---
分析完成时间：{datetime.utcnow().isoformat()}
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
                "chapters_analyzed": len([c for c in all_chapters if c.summary]),
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
        "structure_analysis": chapter.structure_analysis,
        "character_mentions": chapter.character_mentions,
        "plot_points": chapter.plot_points,
        "emotional_beats": chapter.emotional_beats,
        "hooks": chapter.hooks,
    }


@router.post("/{book_id}/extract-techniques")
async def extract_techniques(book_id: int, db: Session = Depends(get_db)):
    """
    从拆书分析结果中提取技巧卡。

    流程：
    1. 读取 BookChapter 的章节分析字段
    2. 调用 study/analyze 模型提取可迁移写作技巧
    3. 解析为 TechniqueCard
    4. 至少保证落库 3 张技巧卡
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    chapters = (
        db.query(BookChapter)
        .filter(BookChapter.book_id == book_id)
        .order_by(BookChapter.chapter_index.asc())
        .all()
    )

    if not chapters:
        raise HTTPException(status_code=400, detail="请先进行分章处理")

    analyzed_chapters = [
        ch for ch in chapters
        if ch.summary or ch.structure_analysis or ch.hooks or ch.plot_points or ch.emotional_beats
    ]

    if not analyzed_chapters:
        raise HTTPException(
            status_code=400,
            detail="请先执行拆书分析，确保章节 summary / structure_analysis / hooks 等字段已写入"
        )

    # 避免重复生成太多：如果已有技巧卡，先返回已有结果
    existing = (
        db.query(TechniqueCard)
        .filter(TechniqueCard.book_id == book_id)
        .order_by(TechniqueCard.created_at.desc())
        .all()
    )

    if len(existing) >= 3:
        return {
            "message": f"已存在 {len(existing)} 张技巧卡",
            "book_id": book_id,
            "techniques": [_technique_to_response(t) for t in existing],
        }

    # 取前 12 章做技巧提取样本，避免一次 prompt 过长
    sample_chapters = analyzed_chapters[:12]

    chapter_blocks = []
    for ch in sample_chapters:
        chapter_blocks.append({
            "chapter_index": ch.chapter_index,
            "title": ch.title,
            "summary": ch.summary,
            "structure_analysis": ch.structure_analysis,
            "character_mentions": ch.character_mentions,
            "plot_points": ch.plot_points,
            "emotional_beats": ch.emotional_beats,
            "hooks": ch.hooks,
            "content_excerpt": (ch.content or "")[:1200],
        })

    prompt = f"""
你是一个专业网文拆书教练。请从以下小说拆书数据中提取"可迁移的写作技巧卡"。

重要要求：
1. 不是复刻原文，不是总结剧情，而是提取可迁移的写作方法。
2. 每张技巧卡必须能指导另一本小说的写作。
3. 必须包含技巧原理、适用场景、使用方法、反模式和 prompt 指令。
4. 至少输出 3 张，最多输出 8 张。
5. 只返回 JSON，不要解释，不要 Markdown。

书籍信息：
- 标题：{book.title}
- 题材：{book.genre or "未知"}

章节拆书数据：
{json.dumps(chapter_blocks, ensure_ascii=False, indent=2)}

请严格返回如下 JSON 格式：

{{
  "techniques": [
    {{
      "category": "structure|character|pacing|hook|emotion|style|readability|commercial",
      "title": "技巧名称",
      "observation": "你从原书中观察到的现象，不能大段引用原文",
      "description": "技巧描述",
      "principle": "为什么这个技巧有效",
      "transfer_rule": "这个技巧适合迁移到什么场景",
      "usage_instruction": "写作时具体怎么用",
      "anti_pattern": "错误使用方式或容易翻车的地方",
      "prevention_rule": "避免翻车的规则",
      "prompt_instruction": "给写作 Agent 的直接指令",
      "applicable_genres": ["玄幻", "都市", "悬疑"],
      "tags": ["钩子", "节奏", "人物"],
      "source_chapters": [1, 2],
      "confidence_score": 0.85
    }}
  ]
}}
"""

    llm_result = None
    try:
        llm_manager.init_from_db(db)
        llm_result = await llm_manager.generate(
            prompt=prompt,
            role="study",
            temperature=0.3,
            max_tokens=4000,
        )
    except Exception as e:
        # 没有配置真实模型时，不直接失败，使用规则兜底生成
        print(f"extract-techniques LLM 调用失败，使用兜底生成: {e}")

    techniques_data = []

    if llm_result and llm_result.get("content"):
        techniques_data = _parse_technique_json(llm_result.get("content", ""))

    # 如果 LLM 解析失败或返回不足 3 张，使用兜底技巧生成
    if len(techniques_data) < 3:
        fallback = _build_fallback_techniques(book, analyzed_chapters)
        techniques_data.extend(fallback)

    # 去重并限制数量
    seen_titles = set()
    cleaned = []
    for item in techniques_data:
        title = str(item.get("title") or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        cleaned.append(item)
        if len(cleaned) >= 8:
            break

    if len(cleaned) < 3:
        raise HTTPException(status_code=500, detail="技巧卡生成失败：有效技巧不足 3 张")

    created_cards = []

    for item in cleaned:
        category = _normalize_technique_category(item.get("category"))

        card = TechniqueCard(
            book_id=book_id,
            category=category,
            title=str(item.get("title") or "未命名技巧")[:200],
            observation=item.get("observation") or "",
            source_chapters=item.get("source_chapters") or [],
            description=item.get("description") or "",
            principle=item.get("principle") or "",
            transfer_rule=item.get("transfer_rule") or "",
            usage_instruction=item.get("usage_instruction") or "",
            anti_pattern=item.get("anti_pattern") or "",
            prevention_rule=item.get("prevention_rule") or "",
            prompt_instruction=item.get("prompt_instruction") or "",
            applicable_genres=item.get("applicable_genres") or ([book.genre] if book.genre else []),
            tags=item.get("tags") or [],
            confidence_score=float(item.get("confidence_score") or item.get("confidence") or 0.75),
            success_rate=0.0,
            usage_count=0,
            is_active=1,
            is_verified=0,
        )

        db.add(card)
        created_cards.append(card)

    db.commit()

    for card in created_cards:
        db.refresh(card)

    return {
        "message": f"成功提取 {len(created_cards)} 个技巧卡片",
        "book_id": book_id,
        "techniques": [_technique_to_response(card) for card in created_cards],
    }


def _parse_technique_json(content: str) -> list:
    """
    从 LLM 返回内容中解析 techniques 数组。
    兼容：
    1. 纯 JSON
    2. Markdown ```json 包裹
    3. 前后夹杂说明文字
    """
    if not content:
        return []

    text = content.strip()

    # 去掉 Markdown code fence
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    candidates = []

    # 优先匹配完整 JSON 对象
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        candidates.append(obj_match.group())

    # 再尝试匹配 JSON 数组
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        candidates.append(arr_match.group())

    # 最后尝试原文
    candidates.append(text)

    for candidate in candidates:
        try:
            data = json.loads(candidate)

            if isinstance(data, dict):
                techniques = data.get("techniques") or data.get("cards") or data.get("items") or []
                if isinstance(techniques, list):
                    return techniques

            if isinstance(data, list):
                return data

        except Exception:
            continue

    return []


def _normalize_technique_category(category: str) -> str:
    """
    规范化技巧分类，避免 LLM 返回中文或乱写字段。
    """
    if not category:
        return TechniqueCategory.STRUCTURE.value

    raw = str(category).strip().lower()

    mapping = {
        "结构": TechniqueCategory.STRUCTURE.value,
        "structure": TechniqueCategory.STRUCTURE.value,

        "人物": TechniqueCategory.CHARACTER.value,
        "角色": TechniqueCategory.CHARACTER.value,
        "character": TechniqueCategory.CHARACTER.value,

        "节奏": TechniqueCategory.PACING.value,
        "pacing": TechniqueCategory.PACING.value,

        "钩子": TechniqueCategory.HOOK.value,
        "悬念": TechniqueCategory.HOOK.value,
        "hook": TechniqueCategory.HOOK.value,

        "情绪": TechniqueCategory.EMOTION.value,
        "emotion": TechniqueCategory.EMOTION.value,

        "文风": TechniqueCategory.STYLE.value,
        "风格": TechniqueCategory.STYLE.value,
        "style": TechniqueCategory.STYLE.value,

        "可读性": TechniqueCategory.READABILITY.value,
        "readability": TechniqueCategory.READABILITY.value,

        "商业性": TechniqueCategory.COMMERCIAL.value,
        "爽点": TechniqueCategory.COMMERCIAL.value,
        "commercial": TechniqueCategory.COMMERCIAL.value,
    }

    if raw in mapping:
        return mapping[raw]

    allowed = {
        TechniqueCategory.STRUCTURE.value,
        TechniqueCategory.CHARACTER.value,
        TechniqueCategory.PACING.value,
        TechniqueCategory.HOOK.value,
        TechniqueCategory.EMOTION.value,
        TechniqueCategory.STYLE.value,
        TechniqueCategory.READABILITY.value,
        TechniqueCategory.COMMERCIAL.value,
    }

    return raw if raw in allowed else TechniqueCategory.STRUCTURE.value


def _build_fallback_techniques(book: Book, chapters: list) -> list:
    """
    没有真实 LLM 或 LLM 返回格式不稳定时的兜底技巧卡。
    兜底卡仍然基于章节分析字段生成，不直接复刻原文。
    """
    source_indexes = [ch.chapter_index for ch in chapters[:5]]
    genre = book.genre or "通用题材"

    hooks = []
    emotional_beats = []
    plot_points = []

    for ch in chapters[:8]:
        if ch.hooks:
            hooks.extend(ch.hooks if isinstance(ch.hooks, list) else [])
        if ch.emotional_beats:
            emotional_beats.extend(ch.emotional_beats if isinstance(ch.emotional_beats, list) else [])
        if ch.plot_points:
            plot_points.extend(ch.plot_points if isinstance(ch.plot_points, list) else [])

    return [
        {
            "category": TechniqueCategory.HOOK.value,
            "title": "章节末尾钩子保留法",
            "observation": "样本章节中多次通过未解决问题、身份压力或下一步考验制造继续阅读动力。",
            "description": "在章节结尾保留一个明确但未解决的问题，让读者产生追读冲动。",
            "principle": "读者对未闭合信息天然敏感，章节结尾的悬而未决能提高下一章点击率。",
            "transfer_rule": "适合升级流、悬疑流、冒险流、都市逆袭等需要连续追读的题材。",
            "usage_instruction": "每章结尾至少保留一个未解决问题：新敌人、新目标、新危机、新线索或新奖励。",
            "anti_pattern": "只制造谜语但不给阶段性回报，会让读者觉得故弄玄虚。",
            "prevention_rule": "每 2-3 个钩子必须兑现一次，不能长期只埋不收。",
            "prompt_instruction": "本章结尾必须设置一个清晰的下一章钩子，同时给出本章的小回报，避免只有悬念没有爽点。",
            "applicable_genres": [genre],
            "tags": ["钩子", "追读", "章节结尾"],
            "source_chapters": source_indexes,
            "confidence_score": 0.78,
        },
        {
            "category": TechniqueCategory.PACING.value,
            "title": "压迫—反应—目标三段节奏",
            "observation": "章节推进通常由外部压力触发，主角给出反应，再形成下一阶段目标。",
            "description": "用压力推动行动，用行动暴露人物，用目标承接下一段剧情。",
            "principle": "压力让剧情动起来，反应让人物立起来，目标让读者知道接下来要看什么。",
            "transfer_rule": "适合成长型主角、考核副本、宗门升级、职场逆袭、末世求生等剧情。",
            "usage_instruction": "写章节时按"压力事件 → 主角反应 → 明确目标"组织关键段落。",
            "anti_pattern": "只有设定解释，没有外部压力，会导致章节像资料说明书。",
            "prevention_rule": "每章至少安排一个外部压力源，并让主角做出可见选择。",
            "prompt_instruction": "本章必须包含一个外部压力事件，主角必须做出选择，并在结尾形成下一步目标。",
            "applicable_genres": [genre],
            "tags": ["节奏", "压力", "目标"],
            "source_chapters": source_indexes,
            "confidence_score": 0.76,
        },
        {
            "category": TechniqueCategory.CHARACTER.value,
            "title": "羞辱记忆驱动人物成长",
            "observation": "样本章节中人物动机常由挫折、轻视、羞辱或未完成执念触发。",
            "description": "用具体负面事件强化主角目标，让成长线更有情绪燃料。",
            "principle": "抽象目标不如具体伤害有记忆点，羞辱和挫折能让读者期待反击和兑现。",
            "transfer_rule": "适合废柴流、逆袭流、复仇流、升级流、女强成长线等。",
            "usage_instruction": "给主角设置一个具体可回忆的挫折事件，并让后续行动持续回应这个事件。",
            "anti_pattern": "羞辱过度但主角长期无反击，会让读者憋屈。",
            "prevention_rule": "羞辱之后必须安排阶段性反击或能力增长信号。",
            "prompt_instruction": "本章如果出现压制或羞辱，必须同时埋下主角未来反击的能力线索或目标承诺。",
            "applicable_genres": [genre],
            "tags": ["人物动机", "逆袭", "成长"],
            "source_chapters": source_indexes,
            "confidence_score": 0.74,
        },
    ]


def _technique_to_response(card: TechniqueCard) -> dict:
    return {
        "id": card.id,
        "book_id": card.book_id,
        "category": card.category,
        "title": card.title,
        "observation": card.observation,
        "description": card.description,
        "principle": card.principle,
        "transfer_rule": card.transfer_rule,
        "usage_instruction": card.usage_instruction,
        "anti_pattern": card.anti_pattern,
        "prevention_rule": card.prevention_rule,
        "prompt_instruction": card.prompt_instruction,
        "applicable_genres": card.applicable_genres or [],
        "tags": card.tags or [],
        "source_chapters": card.source_chapters or [],
        "confidence": card.confidence_score,
        "confidence_score": card.confidence_score,
        "created_at": card.created_at.isoformat() if card.created_at else None,
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
