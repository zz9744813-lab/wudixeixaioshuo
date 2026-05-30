"""
Dashboard Router - 仪表盘路由
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.task import GenerationTask, TaskStatus
from app.utils.time_utils import utc_now

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表盘统计数据"""

    # 项目统计
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.status == "active").count()
    completed_projects = db.query(Project).filter(Project.status == "completed").count()

    # 章节统计
    total_chapters = db.query(Chapter).count()
    completed_chapters = db.query(Chapter).filter(Chapter.status == "completed").count()
    total_words = db.query(func.sum(Chapter.final_word_count)).scalar() or 0

    # 今日统计
    from datetime import datetime, timedelta
    today = utc_now().date()
    today_start = datetime.combine(today, datetime.min.time())

    today_chapters = db.query(Chapter).filter(
        Chapter.created_at >= today_start
    ).count()

    today_words = db.query(func.sum(Chapter.final_word_count)).filter(
        Chapter.created_at >= today_start
    ).scalar() or 0

    # 任务统计
    total_tasks = db.query(GenerationTask).count()
    running_tasks = db.query(GenerationTask).filter(
        GenerationTask.status == TaskStatus.RUNNING
    ).count()
    pending_tasks = db.query(GenerationTask).filter(
        GenerationTask.status == TaskStatus.PENDING
    ).count()

    # 书籍统计
    total_books = db.query(Book).count()
    analyzed_books = db.query(Book).filter(Book.status == "completed").count()

    return {
        "projects": {
            "total": total_projects,
            "active": active_projects,
            "completed": completed_projects,
        },
        "chapters": {
            "total": total_chapters,
            "completed": completed_chapters,
            "total_words": total_words,
            "today_chapters": today_chapters,
            "today_words": today_words,
        },
        "tasks": {
            "total": total_tasks,
            "running": running_tasks,
            "pending": pending_tasks,
        },
        "books": {
            "total": total_books,
            "analyzed": analyzed_books,
        },
    }


@router.get("/recent-activity")
async def get_recent_activity(limit: int = 10, db: Session = Depends(get_db)):
    """获取最近活动"""

    recent_tasks = db.query(GenerationTask).order_by(
        GenerationTask.created_at.desc()
    ).limit(limit).all()

    activity_list = []
    for task in recent_tasks:
        activity_list.append({
            "id": task.id,
            "type": task.task_type,
            "status": task.status,
            "project_id": task.project_id,
            "chapter_id": task.chapter_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        })

    return {"activities": activity_list}


@router.get("/automation-status")
async def get_automation_status(db: Session = Depends(get_db)):
    """生产控制台聚合状态 (P9-4)"""
    # 生产循环状态
    try:
        from app.services.production_loop_service import production_loop
        loop_status = production_loop.get_status()
    except Exception:
        loop_status = {"status": "stopped"}

    # Worker 状态
    worker_status = {}
    try:
        from app.services.worker_service import worker
        worker_status = worker.get_status()
    except Exception:
        pass

    # 最近总编复盘
    last_review = None
    try:
        from app.models.editor import EditorDirective
        ed = db.query(EditorDirective).order_by(
            EditorDirective.updated_at.desc()
        ).first()
        if ed:
            last_review = {
                "chapter_index": ed.chapter_index,
                "updated_at": ed.updated_at.isoformat() if ed.updated_at else None,
            }
    except Exception:
        pass

    # 最近 Prompt 进化
    last_evolution = None
    try:
        from app.models.evolution_auto import PromptEvolutionRun
        run = db.query(PromptEvolutionRun).order_by(
            PromptEvolutionRun.created_at.desc()
        ).first()
        if run:
            last_evolution = {
                "id": run.id,
                "role": run.role,
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
    except Exception:
        pass

    # 最近记忆固化
    last_consolidation = None
    try:
        from app.models.memory import ConsolidatedMemory
        cm = db.query(ConsolidatedMemory).order_by(
            ConsolidatedMemory.created_at.desc()
        ).first()
        if cm:
            last_consolidation = {
                "id": cm.id,
                "title": cm.title,
                "scope": [cm.scope_start_chapter, cm.scope_end_chapter],
                "created_at": cm.created_at.isoformat() if cm.created_at else None,
            }
    except Exception:
        pass

    return {
        "production_loop": loop_status,
        "worker": worker_status,
        "last_editor_review": last_review,
        "last_evolution": last_evolution,
        "last_consolidation": last_consolidation,
    }
