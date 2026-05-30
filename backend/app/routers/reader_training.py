"""Reader Training Router - 异步真人训练营 API (P9)"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback
from app.models.feedback import FeedbackBatch
from app.services.reader_training_service import ReaderTrainingService
from app.services.event_bus import event_bus
from app.utils.time_utils import utc_now

router = APIRouter()


# ============== 请求模型 ==============

class FeedbackSubmitRequest(BaseModel):
    project_id: int
    chapter_id: Optional[int] = None
    reader_score: Optional[float] = None
    dimension_scores: Optional[dict] = None
    anchor: Optional[list[dict]] = None
    reaction: Optional[str] = None
    raw_comment: Optional[str] = None
    reader_id: Optional[str] = None


class ProcessBatchRequest(BaseModel):
    project_id: Optional[int] = None
    chapter_id: Optional[int] = None
    min_batch: int = 5


# ============== API 接口 ==============

@router.post("/feedback")
async def submit_feedback(req: FeedbackSubmitRequest, db: Session = Depends(get_db)):
    """提交真人读者反馈 — 同步快返，只入库，不阻塞Worker"""
    try:
        service = ReaderTrainingService(db)
        result = service.submit_feedback(
            project_id=req.project_id,
            chapter_id=req.chapter_id,
            reader_score=req.reader_score,
            dimension_scores=req.dimension_scores,
            anchor=req.anchor,
            reaction=req.reaction,
            raw_comment=req.raw_comment,
            reader_id=req.reader_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交反馈失败：{str(e)[:200]}")


@router.post("/process-batch")
async def process_batch(req: ProcessBatchRequest, db: Session = Depends(get_db)):
    """手动触发批处理（调试用）"""
    try:
        service = ReaderTrainingService(db)
        result = await service.process_pending_batch(
            project_id=req.project_id,
            chapter_id=req.chapter_id,
            min_batch=req.min_batch,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批处理失败：{str(e)[:200]}")


@router.get("/projects/{project_id}/pending")
async def get_pending(project_id: int, min_batch: int = 5, db: Session = Depends(get_db)):
    """查看项目待处理反馈数量"""
    pending_count = (
        db.query(Feedback)
        .filter(
            Feedback.status == "queued",
            Feedback.source == "reader",
            Feedback.project_id == project_id,
        )
        .count()
    )
    status = "waiting" if pending_count < min_batch else "ready"
    return {
        "project_id": project_id,
        "pending_count": pending_count,
        "min_batch": min_batch,
        "status": status,
        "message": f"已入队 {pending_count} 条反馈，需 {min_batch} 条才能批处理" if pending_count < min_batch else f"已就绪，可处理 {pending_count} 条反馈",
    }


@router.get("/projects/{project_id}/batches")
async def get_batches(project_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """查看项目的 FeedbackBatch 列表"""
    batches = (
        db.query(FeedbackBatch)
        .filter(FeedbackBatch.project_id == project_id)
        .order_by(FeedbackBatch.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": b.id,
                "project_id": b.project_id,
                "chapter_id": b.chapter_id,
                "feedback_count": b.feedback_count,
                "avg_reader_score": b.avg_reader_score,
                "avg_system_score": b.avg_system_score,
                "critic_gap": b.critic_gap,
                "derived_rules_count": len(b.derived_rules or []),
                "triggered_critic_calibration": b.triggered_critic_calibration,
                "status": b.status,
                "error_message": b.error_message,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "processed_at": b.processed_at.isoformat() if b.processed_at else None,
            }
            for b in batches
        ]
    }


@router.get("/projects/{project_id}/rules")
async def get_rules(
    project_id: int,
    role: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """查看项目已生成的真人规则"""
    batches = (
        db.query(FeedbackBatch)
        .filter(
            FeedbackBatch.project_id == project_id,
            FeedbackBatch.status == "processed",
            FeedbackBatch.derived_rules.isnot(None),
        )
        .all()
    )
    rules = []
    for batch in batches:
        for r in (batch.derived_rules or []):
            if role and r.get("role") != role:
                continue
            rules.append({
                "batch_id": batch.id,
                "role": r.get("role"),
                "rule": r.get("rule", ""),
                "priority": r.get("priority", 5),
                "evidence": r.get("evidence", []),
                "applied_from_chapter": r.get("applied_from_chapter"),
                "is_calibration": r.get("is_calibration", False),
            })
    # 按 priority 降序
    rules.sort(key=lambda x: x.get("priority", 0), reverse=True)
    rules = rules[:limit]
    return {"items": rules, "total": len(rules)}


@router.get("/chapters/{chapter_id}/feedback")
async def get_chapter_feedback(
    chapter_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """查看某章所有真人反馈"""
    feedbacks = (
        db.query(Feedback)
        .filter(
            Feedback.chapter_id == chapter_id,
            Feedback.source == "reader",
        )
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    total = db.query(Feedback).filter(
        Feedback.chapter_id == chapter_id,
        Feedback.source == "reader",
    ).count()
    return {
        "total": total,
        "items": [
            {
                "id": f.id,
                "reader_score": f.reader_score,
                "dimension_scores": f.dimension_scores or {},
                "anchor": f.anchor or [],
                "reaction": f.reaction,
                "raw_text": f.raw_text[:200] if f.raw_text else "",
                "batch_id": f.batch_id,
                "status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedbacks
        ],
    }


@router.get("/projects/{project_id}/stats")
async def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    """获取项目训练统计概览"""
    total_feedback = db.query(Feedback).filter(
        Feedback.project_id == project_id,
        Feedback.source == "reader",
    ).count()
    pending_count = db.query(Feedback).filter(
        Feedback.status == "queued",
        Feedback.source == "reader",
        Feedback.project_id == project_id,
    ).count()
    batched_count = db.query(Feedback).filter(
        Feedback.status == "batched",
        Feedback.source == "reader",
        Feedback.project_id == project_id,
    ).count()

    last_batch = (
        db.query(FeedbackBatch)
        .filter(FeedbackBatch.project_id == project_id, FeedbackBatch.status == "processed")
        .order_by(FeedbackBatch.created_at.desc())
        .first()
    )
    last_critic_gap = last_batch.critic_gap if last_batch else None
    last_batch_id = last_batch.id if last_batch else None
    derived_rules_count = len(last_batch.derived_rules or []) if last_batch else 0

    return {
        "project_id": project_id,
        "total_feedback": total_feedback,
        "pending_count": pending_count,
        "batched_count": batched_count,
        "last_batch_id": last_batch_id,
        "last_critic_gap": last_critic_gap,
        "derived_rules_count": derived_rules_count,
    }
