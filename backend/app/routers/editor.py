"""
Editor / BookState API 路由 (P2/P8)
- 总编指令、书级状态、总编复盘
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.editor import BookState, EditorDirective
from app.services.book_state_service import BookStateService
from app.services.chief_editor_agent import ChiefEditorAgent
from app.services.editor_review_service import EditorReviewService

router = APIRouter()


class DirectiveRequest(BaseModel):
    chapter_index: int
    chapter_title: str = ""


class ReviewRequest(BaseModel):
    end_chapter_index: int
    window_size: int = 5


@router.post("/projects/{project_id}/chapters/{chapter_id}/directive")
async def build_directive(
    project_id: int, chapter_id: int, data: DirectiveRequest,
    db: Session = Depends(get_db),
):
    """生成/更新某章总编指令"""
    agent = ChiefEditorAgent(db)
    directive = await agent.build_chapter_directive(
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_index=data.chapter_index,
        chapter_title=data.chapter_title,
    )
    return {"chapter_id": chapter_id, "directive": directive}


@router.get("/projects/{project_id}/chapters/{chapter_id}/directive")
def get_directive(project_id: int, chapter_id: int, db: Session = Depends(get_db)):
    """查看某章最新总编指令"""
    record = db.query(EditorDirective).filter(
        EditorDirective.chapter_id == chapter_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="该章暂无总编指令")
    return {
        "chapter_id": chapter_id,
        "chapter_index": record.chapter_index,
        "directive": record.directive,
        "formatted_prompt": record.formatted_prompt,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


@router.get("/projects/{project_id}/book-state")
async def get_book_state(project_id: int, db: Session = Depends(get_db)):
    """查看全书状态"""
    service = BookStateService(db)
    state = await service.get_or_create_state(project_id)
    return _serialize_state(state)


@router.post("/projects/{project_id}/book-state/rebuild")
async def rebuild_book_state(project_id: int, db: Session = Depends(get_db)):
    """从全部已完成章节重建全书状态"""
    service = BookStateService(db)
    state = await service.rebuild_state(project_id)
    return _serialize_state(state)


@router.post("/projects/{project_id}/review")
async def run_review(project_id: int, data: ReviewRequest, db: Session = Depends(get_db)):
    """触发一次总编阶段性复盘"""
    service = EditorReviewService(db)
    review = await service.review_recent_chapters(
        project_id=project_id,
        end_chapter_index=data.end_chapter_index,
        window_size=data.window_size,
    )
    return review


def _serialize_state(state: BookState) -> dict:
    return {
        "project_id": state.project_id,
        "current_volume": state.current_volume,
        "current_arc": state.current_arc,
        "current_stage": state.current_stage,
        "tension_curve": state.tension_curve,
        "active_foreshadows": state.active_foreshadows,
        "unresolved_conflicts": state.unresolved_conflicts,
        "next_payoff_candidates": state.next_payoff_candidates,
        "last_analyzed_chapter_index": state.last_analyzed_chapter_index,
        "summary": state.summary,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }
