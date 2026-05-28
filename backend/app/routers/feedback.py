"""
Feedback Router - 反馈路由（完整版）
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback, FeedbackCategory, FeedbackSeverity
from app.services.feedback_service import FeedbackService

router = APIRouter()


# ============== 请求模型 ==============

class FeedbackCreate(BaseModel):
    project_id: int
    chapter_id: Optional[int] = None
    category: str = "content"  # content, style, grammar, continuity, engagement
    severity: str = "medium"   # low, medium, high, critical
    content: str
    dimension_scores: Optional[dict] = None


class FeedbackResolve(BaseModel):
    resolution: str


class ChapterAnalysisRequest(BaseModel):
    chapter_id: int
    chapter_content: str


# ============== 反馈管理 API ==============

@router.get("/")
async def list_feedback(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取反馈列表"""
    query = db.query(Feedback)

    if project_id:
        query = query.filter(Feedback.project_id == project_id)
    if chapter_id:
        query = query.filter(Feedback.chapter_id == chapter_id)
    if category:
        query = query.filter(Feedback.category == category)
    if severity:
        query = query.filter(Feedback.severity == severity)
    if resolved is not None:
        if resolved:
            query = query.filter(Feedback.resolved_at.isnot(None))
        else:
            query = query.filter(Feedback.resolved_at.is_(None))

    feedbacks = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": query.count(),
        "items": [
            {
                "id": f.id,
                "project_id": f.project_id,
                "chapter_id": f.chapter_id,
                "category": f.category.value if f.category else None,
                "severity": f.severity.value if f.severity else None,
                "content": f.content[:200] + "..." if len(f.content) > 200 else f.content,
                "dimension_scores": f.dimension_scores,
                "created_by": f.created_by,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
                "is_resolved": f.resolved_at is not None,
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
    service = FeedbackService(db)

    try:
        category = FeedbackCategory(feedback.category)
        severity = FeedbackSeverity(feedback.severity)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的类别或严重程度")

    fb = service.create_feedback(
        project_id=feedback.project_id,
        chapter_id=feedback.chapter_id,
        category=category,
        severity=severity,
        content=feedback.content,
        dimension_scores=feedback.dimension_scores,
        created_by="user"
    )

    return {
        "id": fb.id,
        "message": "反馈已提交",
        "category": fb.category.value,
        "severity": fb.severity.value,
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
        "category": feedback.category.value if feedback.category else None,
        "severity": feedback.severity.value if feedback.severity else None,
        "content": feedback.content,
        "dimension_scores": feedback.dimension_scores,
        "metadata": feedback.metadata,
        "created_by": feedback.created_by,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "resolved_at": feedback.resolved_at.isoformat() if feedback.resolved_at else None,
        "is_resolved": feedback.resolved_at is not None,
    }


@router.post("/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: int,
    request: FeedbackResolve,
    db: Session = Depends(get_db)
):
    """解决反馈"""
    service = FeedbackService(db)
    success = service.resolve_feedback(feedback_id, request.resolution)

    if not success:
        raise HTTPException(status_code=404, detail="反馈不存在")

    return {"message": "反馈已解决"}


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db)
):
    """删除反馈"""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    db.delete(feedback)
    db.commit()

    return {"message": "反馈已删除"}


# ============== AI 分析 API ==============

@router.post("/analyze")
async def analyze_chapter(
    request: ChapterAnalysisRequest,
    db: Session = Depends(get_db)
):
    """AI 分析章节并生成反馈"""
    service = FeedbackService(db)

    analysis = service.analyze_chapter(
        chapter_id=request.chapter_id,
        content=request.chapter_content
    )

    # 可选：自动保存反馈
    # service.create_feedback(...)

    return analysis


# ============== 统计 API ==============

@router.get("/stats/overview")
async def get_feedback_stats(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取反馈统计概览"""
    service = FeedbackService(db)
    stats = service.get_feedback_stats(project_id)

    return stats


@router.get("/stats/trend/{project_id}")
async def get_feedback_trend(
    project_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """获取反馈趋势"""
    service = FeedbackService(db)
    trend = service.get_feedback_trend(project_id, days)

    return {
        "project_id": project_id,
        "days": days,
        "trend": trend
    }


@router.get("/issues/common")
async def get_common_issues(
    project_id: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取常见问题"""
    service = FeedbackService(db)
    issues = service.get_common_issues(project_id, limit)

    return {
        "count": len(issues),
        "issues": issues
    }
