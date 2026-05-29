"""
Feedback Router - 反馈路由（简化修复版）
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback, FeedbackSource
from app.utils.time_utils import utc_now

router = APIRouter()


# ============== 请求模型 ==============

class FeedbackCreate(BaseModel):
    project_id: int
    chapter_id: Optional[int] = None
    source: str = "user"
    raw_text: str


# ============== 反馈管理 API ==============

@router.get("/")
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

    return {
        "total": query.count(),
        "items": [
            {
                "id": f.id,
                "project_id": f.project_id,
                "chapter_id": f.chapter_id,
                "source": f.source,
                "raw_text": f.raw_text[:200] + "..." if len(f.raw_text) > 200 else f.raw_text,
                "parsed_category": f.parsed_category,
                "priority": f.priority,
                "is_processed": f.is_processed == 1,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedbacks
        ]
    }


@router.post("/")
async def create_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db)
):
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
async def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db)
):
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
        "processed_at": feedback.processed_at.isoformat() if feedback.processed_at else None,
    }


@router.post("/{feedback_id}/process")
async def process_feedback(
    feedback_id: int,
    db: Session = Depends(get_db)
):
    """标记反馈为已处理"""
    from datetime import datetime

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    feedback.is_processed = 1
    feedback.processed_at = utc_now()
    db.commit()

    return {"message": "反馈已标记为处理"}
