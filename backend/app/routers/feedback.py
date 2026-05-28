"""
Feedback Router - 反馈路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback

router = APIRouter()


# Pydantic 模型
class FeedbackCreate(BaseModel):
    project_id: int
    chapter_id: Optional[int] = None
    source: str = "user"
    raw_text: str


class FeedbackResponse(BaseModel):
    id: int
    project_id: int
    chapter_id: Optional[int]
    source: str
    raw_text: str
    is_processed: bool
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[FeedbackResponse])
async def list_feedback(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取反馈列表"""
    query = db.query(Feedback)
    if project_id:
        query = query.filter(Feedback.project_id == project_id)
    if chapter_id:
        query = query.filter(Feedback.chapter_id == chapter_id)

    feedbacks = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": f.id,
            "project_id": f.project_id,
            "chapter_id": f.chapter_id,
            "source": f.source,
            "raw_text": f.raw_text[:200] + "..." if len(f.raw_text) > 200 else f.raw_text,
            "is_processed": f.is_processed == 1,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in feedbacks
    ]


@router.post("/")
async def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    """创建反馈"""
    db_feedback = Feedback(
        project_id=feedback.project_id,
        chapter_id=feedback.chapter_id,
        source=feedback.source,
        raw_text=feedback.raw_text,
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    return {
        "id": db_feedback.id,
        "message": "反馈已提交",
    }


@router.get("/{feedback_id}")
async def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """获取反馈详情"""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    return {
        "id": feedback.id,
        "project_id": feedback.project_id,
        "chapter_id": feedback.chapter_id,
        "source": feedback.source,
        "raw_text": feedback.raw_text,
        "parsed_category": feedback.parsed_category,
        "parsed_rule": feedback.parsed_rule,
        "priority": feedback.priority,
        "is_processed": feedback.is_processed == 1,
        "is_applied": feedback.is_applied == 1,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }
