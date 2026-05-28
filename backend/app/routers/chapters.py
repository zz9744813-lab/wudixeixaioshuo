"""
Chapters Router - 章节路由
处理章节生成流水线
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.services.writing_pipeline_service import WritingPipelineService

router = APIRouter()


class ChapterCreate(BaseModel):
    chapter_index: int
    title: str = ""


class ChapterGenerate(BaseModel):
    title: str = ""


@router.get("/projects/{project_id}/chapters")
async def list_chapters(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取章节列表"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    query = db.query(Chapter).filter(Chapter.project_id == project_id)
    if status:
        query = query.filter(Chapter.status == status)

    chapters = query.order_by(Chapter.chapter_index).offset(skip).limit(limit).all()

    return [
        {
            "id": c.id,
            "chapter_index": c.chapter_index,
            "title": c.title,
            "status": c.status,
            "total_score": c.total_score,
            "final_word_count": c.final_word_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        }
        for c in chapters
    ]


@router.post("/projects/{project_id}/chapters")
async def create_chapter(
    project_id: int,
    data: ChapterCreate,
    db: Session = Depends(get_db)
):
    """创建章节"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    chapter = Chapter(
        project_id=project_id,
        chapter_index=data.chapter_index,
        title=data.title or f"第{data.chapter_index}章",
        status=ChapterStatus.PLANNED,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    return {
        "id": chapter.id,
        "chapter_index": chapter.chapter_index,
        "title": chapter.title,
        "status": chapter.status,
        "message": "章节已创建",
    }


@router.get("/projects/{project_id}/chapters/{chapter_id}")
async def get_chapter(
    project_id: int,
    chapter_id: int,
    db: Session = Depends(get_db)
):
    """获取章节详情"""
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.project_id == project_id
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    return {
        "id": chapter.id,
        "project_id": chapter.project_id,
        "chapter_index": chapter.chapter_index,
        "title": chapter.title,
        "status": chapter.status,
        "final_content": chapter.final_content,
        "final_word_count": chapter.final_word_count,
        "total_score": chapter.total_score,
        "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
        "completed_at": chapter.completed_at.isoformat() if chapter.completed_at else None,
    }


@router.post("/projects/{project_id}/chapters/{chapter_id}/generate")
async def generate_chapter(
    project_id: int,
    chapter_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """生成章节（启动流水线）"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.project_id == project_id
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 在后台运行流水线
    async def run_pipeline():
        await WritingPipelineService.run_pipeline(db, chapter_id, project)

    background_tasks.add_task(run_pipeline)

    return {
        "message": "章节生成已启动",
        "chapter_id": chapter_id,
        "status": "running",
    }


@router.get("/projects/{project_id}/chapters/{chapter_id}/pipeline")
async def get_pipeline_status(
    project_id: int,
    chapter_id: int,
    db: Session = Depends(get_db)
):
    """获取流水线状态"""
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.project_id == project_id
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    status = WritingPipelineService.get_pipeline_status(db, chapter_id)
    return status


@router.get("/projects/{project_id}/chapters/{chapter_id}/content")
async def get_chapter_content(
    project_id: int,
    chapter_id: int,
    version: str = "final",
    db: Session = Depends(get_db)
):
    """获取章节内容"""
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.project_id == project_id
    ).first()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    content = chapter.final_content if version == "final" else chapter.draft_content

    return {
        "chapter_id": chapter_id,
        "title": chapter.title,
        "version": version,
        "content": content,
        "word_count": len(content) if content else 0,
    }


# ========== 独立章节路由 (用于E2E测试) ==========

@router.get("/chapters/{chapter_id}")
async def get_chapter_by_id(
    chapter_id: int,
    db: Session = Depends(get_db)
):
    """通过ID获取章节详情"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    return {
        "id": chapter.id,
        "project_id": chapter.project_id,
        "chapter_index": chapter.chapter_index,
        "title": chapter.title,
        "status": chapter.status,
        "final_content": chapter.final_content,
        "final_word_count": chapter.final_word_count,
        "total_score": chapter.total_score,
        "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
        "completed_at": chapter.completed_at.isoformat() if chapter.completed_at else None,
    }


@router.get("/chapters/{chapter_id}/versions")
async def get_chapter_versions(
    chapter_id: int,
    db: Session = Depends(get_db)
):
    """获取章节的所有版本"""
    from app.models.chapter import ChapterVersion

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    versions = db.query(ChapterVersion).filter(
        ChapterVersion.chapter_id == chapter_id
    ).order_by(ChapterVersion.version_number.desc()).all()

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "plan_content": v.plan_content,
            "draft_content": v.draft_content,
            "final_content": v.final_content,
            "total_score": v.total_score,
            "critic_report": v.critic_report,
            "continuity_report": v.continuity_report,
            "is_accepted": v.is_accepted,
            "acceptance_reason": v.acceptance_reason,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]
