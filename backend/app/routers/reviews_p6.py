"""
P6 评论区驱动评审系统 — 14 个 API 端点
挂载在 /api/reviews (P6 规范要求的路径)
"""
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.comment_review import (
    ReaderAgentProfile,
    ReaderReviewRun,
    ReviewComment,
    ReviewCommentGroup,
    ReviewSettings,
)
from app.utils.time_utils import utc_now

# 不用 prefix, 让 main.py 的 prefix="/api/reviews" 接管
router = APIRouter(tags=["Reviews (P6 评论)"])


# ========== Request/Response Models ==========

class CommentCreate(BaseModel):
    project_id: int
    chapter_id: Optional[int] = None
    chapter_version_id: Optional[int] = None
    target_type: str = "chapter"
    content: str
    tags: Optional[List[str]] = None


class GroupCreate(BaseModel):
    title: str
    summary: str
    comment_ids: List[int]
    severity: str = "medium"


class SettingsUpdate(BaseModel):
    auto_reader_review: Optional[bool] = None
    auto_chief_triage: Optional[bool] = None
    auto_discussion: Optional[bool] = None
    retention_days: Optional[int] = None
    max_comments_per_chapter: Optional[int] = None
    max_reader_comments_per_run: Optional[int] = None
    min_severity_for_discussion: Optional[str] = None


# ========== Helpers ==========

def _serialize_comment(c: ReviewComment, *, include_replies: bool = True) -> dict:
    out = {
        "id": c.id,
        "project_id": c.project_id,
        "chapter_id": c.chapter_id,
        "chapter_version_id": c.chapter_version_id,
        "parent_id": c.parent_id,
        "target_type": c.target_type,
        "author_type": c.author_type,
        "author_label": c.author_label,
        "agent_role_id": c.agent_role_id,
        "content": c.content,
        "evidence": c.evidence,
        "rating": c.rating,
        "tags": c.tags or [],
        "weight_at_created": c.weight_at_created,
        "status": c.status,
        "priority": c.priority,
        "related_group_id": c.related_group_id,
        "related_discussion_id": c.related_discussion_id,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
    if include_replies and getattr(c, "replies", None):
        out["replies"] = [_serialize_comment(r, include_replies=False) for r in c.replies]
    return out


def _get_or_create_settings(db: Session, project_id: int) -> ReviewSettings:
    s = db.query(ReviewSettings).filter(
        ReviewSettings.project_id == project_id,
    ).first()
    if s:
        return s
    s = ReviewSettings(project_id=project_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ========== 1. 评论列表 ==========

@router.get("/comments")
def list_review_comments(
    project_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    author_type: Optional[str] = None,
    include_replies: bool = True,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(ReviewComment)
    if project_id is not None:
        q = q.filter(ReviewComment.project_id == project_id)
    if chapter_id is not None:
        q = q.filter(ReviewComment.chapter_id == chapter_id)
    if status_filter:
        q = q.filter(ReviewComment.status == status_filter)
    if author_type:
        q = q.filter(ReviewComment.author_type == author_type)
    total = q.count()
    items = q.filter(ReviewComment.parent_id == None).order_by(
        ReviewComment.created_at.desc(),
    ).limit(limit).offset(offset).all()
    return {
        "items": [_serialize_comment(c, include_replies=include_replies) for c in items],
        "total": total,
    }


# ========== 2. 用户发表评论 ==========

@router.post("/comments")
def create_review_comment(data: CommentCreate, db: Session = Depends(get_db)):
    expires = utc_now() + timedelta(days=7)
    comment = ReviewComment(
        project_id=data.project_id,
        chapter_id=data.chapter_id,
        chapter_version_id=data.chapter_version_id,
        target_type=data.target_type,
        author_type="user",
        author_label="用户",
        content=data.content,
        tags=data.tags or [],
        weight_at_created=1.0,
        status="new",
        priority=50,
        expires_at=expires,
    )
    db.add(comment)
    db.flush()
    # 自动入队 triage
    from app.services.review.queue import enqueue_comment_triage
    enqueue_comment_triage(
        db,
        project_id=data.project_id,
        chapter_id=data.chapter_id,
        trigger_comment_id=comment.id,
    )
    db.commit()
    db.refresh(comment)
    return _serialize_comment(comment)


# ========== 3. 单条评论 ==========

@router.get("/comments/{comment_id}")
def get_review_comment(comment_id: int, db: Session = Depends(get_db)):
    c = db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="评论不存在")
    return _serialize_comment(c)


# ========== 4. 评论组列表 ==========

@router.get("/groups")
def list_review_groups(
    project_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(ReviewCommentGroup)
    if project_id is not None:
        q = q.filter(ReviewCommentGroup.project_id == project_id)
    if chapter_id is not None:
        q = q.filter(ReviewCommentGroup.chapter_id == chapter_id)
    if status_filter:
        q = q.filter(ReviewCommentGroup.status == status_filter)
    groups = q.order_by(ReviewCommentGroup.created_at.desc()).limit(limit).all()
    return [{
        "id": g.id,
        "project_id": g.project_id,
        "chapter_id": g.chapter_id,
        "title": g.title,
        "summary": g.summary,
        "comment_ids": g.comment_ids or [],
        "severity": g.severity,
        "status": g.status,
        "discussion_session_id": g.discussion_session_id,
        "decision": g.decision,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    } for g in groups]


# ========== 5. 单个评论组 ==========

@router.get("/groups/{group_id}")
def get_review_group(group_id: int, db: Session = Depends(get_db)):
    g = db.query(ReviewCommentGroup).filter(ReviewCommentGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="评论组不存在")
    return {
        "id": g.id,
        "project_id": g.project_id,
        "chapter_id": g.chapter_id,
        "title": g.title,
        "summary": g.summary,
        "comment_ids": g.comment_ids or [],
        "severity": g.severity,
        "status": g.status,
        "discussion_session_id": g.discussion_session_id,
        "decision": g.decision,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


# ========== 6. 手动合并评论组 ==========

@router.post("/groups")
def create_review_group(data: GroupCreate, db: Session = Depends(get_db)):
    first = db.query(ReviewComment).filter(ReviewComment.id == data.comment_ids[0]).first()
    if not first:
        raise HTTPException(status_code=400, detail="comment_ids[0] 不存在")
    group = ReviewCommentGroup(
        project_id=first.project_id,
        chapter_id=first.chapter_id,
        chapter_version_id=first.chapter_version_id,
        title=data.title[:200],
        summary=data.summary,
        comment_ids=data.comment_ids,
        severity=data.severity,
        status="new",
    )
    db.add(group)
    db.flush()
    db.query(ReviewComment).filter(
        ReviewComment.id.in_(data.comment_ids),
    ).update({"related_group_id": group.id, "status": "grouped"}, synchronize_session=False)
    db.commit()
    db.refresh(group)
    return {
        "id": group.id,
        "title": group.title,
        "summary": group.summary,
        "comment_ids": group.comment_ids,
        "severity": group.severity,
        "status": group.status,
    }


# ========== 7. Review Settings GET ==========

@router.get("/settings")
def get_review_settings_endpoint(project_id: int, db: Session = Depends(get_db)):
    s = _get_or_create_settings(db, project_id)
    return {
        "project_id": s.project_id,
        "auto_reader_review": s.auto_reader_review,
        "auto_chief_triage": s.auto_chief_triage,
        "auto_discussion": s.auto_discussion,
        "retention_days": s.retention_days,
        "max_comments_per_chapter": s.max_comments_per_chapter,
        "max_reader_comments_per_run": s.max_reader_comments_per_run,
        "min_severity_for_discussion": s.min_severity_for_discussion,
    }


# ========== 8. Review Settings PUT ==========

@router.put("/settings")
def update_review_settings_endpoint(
    project_id: int,
    data: SettingsUpdate,
    db: Session = Depends(get_db),
):
    s = _get_or_create_settings(db, project_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(s, field, value)
    s.updated_at = utc_now()
    db.commit()
    db.refresh(s)
    return {
        "project_id": s.project_id,
        "auto_reader_review": s.auto_reader_review,
        "auto_chief_triage": s.auto_chief_triage,
        "auto_discussion": s.auto_discussion,
        "retention_days": s.retention_days,
        "max_comments_per_chapter": s.max_comments_per_chapter,
        "max_reader_comments_per_run": s.max_reader_comments_per_run,
        "min_severity_for_discussion": s.min_severity_for_discussion,
    }


# ========== 9. 触发读者评审 (内部) ==========

@router.post("/runs")
def trigger_reader_review(
    project_id: int,
    chapter_id: int,
    chapter_version_id: Optional[int] = None,
    trigger: str = "manual_test",
    db: Session = Depends(get_db),
):
    from app.services.review.reader_review_service import run_for_chapter
    run = run_for_chapter(
        db,
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_version_id=chapter_version_id,
        trigger=trigger,
    )
    return {
        "id": run.id,
        "status": run.status,
        "reader_agent_keys": run.reader_agent_keys,
        "generated_comment_ids": run.generated_comment_ids,
        "error": run.error,
    }


# ========== 10. 触发清理 ==========

@router.post("/cleanup")
def trigger_cleanup_now(retention_days: int = 7, db: Session = Depends(get_db)):
    from app.services.review.comment_cleanup_service import run_cleanup
    return run_cleanup(db, retention_days=retention_days)


# ========== 11. 触发 triage ==========

@router.post("/triage")
def trigger_triage(
    project_id: int,
    chapter_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    from app.services.review.comment_triage_service import run_for_chapter as run_triage
    return run_triage(
        db,
        project_id=project_id,
        chapter_id=chapter_id,
    )


# ========== 12. Reader Agent Profiles ==========

@router.get("/reader-profiles")
def list_reader_profiles(db: Session = Depends(get_db)):
    profiles = db.query(ReaderAgentProfile).order_by(ReaderAgentProfile.id.asc()).all()
    return [{
        "id": p.id,
        "agent_role_id": p.agent_role_id,
        "reader_key": p.reader_key,
        "display_name": p.display_name,
        "dimension": p.dimension,
        "weight": p.weight,
        "adopted_count": p.adopted_count,
        "rejected_count": p.rejected_count,
        "generated_comment_count": p.generated_comment_count,
        "enabled": p.enabled,
        "last_used_at": p.last_used_at.isoformat() if p.last_used_at else None,
    } for p in profiles]


# ========== 13. Reader Review Runs 列表 ==========

@router.get("/runs-list")
def list_reader_runs(
    project_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(ReaderReviewRun)
    if project_id is not None:
        q = q.filter(ReaderReviewRun.project_id == project_id)
    if chapter_id is not None:
        q = q.filter(ReaderReviewRun.chapter_id == chapter_id)
    runs = q.order_by(ReaderReviewRun.created_at.desc()).limit(limit).all()
    return [{
        "id": r.id,
        "project_id": r.project_id,
        "chapter_id": r.chapter_id,
        "trigger": r.trigger,
        "status": r.status,
        "reader_agent_keys": r.reader_agent_keys,
        "generated_comment_ids": r.generated_comment_ids,
        "total_cost_usd": r.total_cost_usd,
        "error": r.error,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in runs]
