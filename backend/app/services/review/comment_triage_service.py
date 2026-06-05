"""
P6 Comment Triage Service
- 拉 status=new 的评论
- chief_comment_moderator 自动分流
- 4 个动作: reply / group / discuss / ignore
- 失败隔离
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.comment_review import (
    ReaderAgentProfile,
    ReviewComment,
    ReviewCommentGroup,
    ReviewSettings,
)
from app.services.review.discussion_bridge import create_discussion_from_group
from app.services.review.queue import enqueue_comment_discussion
from app.services.review.reader_setup_service import get_chief_moderator_profile
from app.utils.time_utils import utc_now


def _reply_to_comment(
    db: Session,
    *,
    source: ReviewComment,
    reply_text: str,
    chief: ReaderAgentProfile,
) -> ReviewComment:
    expires = utc_now() + timedelta(days=7)
    return ReviewComment(
        project_id=source.project_id,
        chapter_id=source.chapter_id,
        chapter_version_id=source.chapter_version_id,
        parent_id=source.id,
        author_type="chief_agent",
        author_label="主 Agent",
        agent_role_id=chief.agent_role_id,
        content=reply_text[:200] if reply_text else "已接入。",
        status="replied",
        weight_at_created=1.0,
        expires_at=expires,
    )


def _create_or_join_group(
    db: Session,
    *,
    source: ReviewComment,
    group_spec: Dict[str, Any],
) -> ReviewCommentGroup:
    """建新组或加入最近的相关组 (idempotent)."""
    group = ReviewCommentGroup(
        project_id=source.project_id,
        chapter_id=source.chapter_id,
        chapter_version_id=source.chapter_version_id,
        title=group_spec.get("title", "未命名问题包")[:200],
        summary=group_spec.get("summary", "")[:1000],
        comment_ids=list({source.id, *group_spec.get("comment_ids", [])}),
        severity=group_spec.get("severity", "medium"),
        status="new",
    )
    db.add(group)
    db.flush()
    return group


def _severity_meets_threshold(severity: str, min_severity: str) -> bool:
    rank = {"low": 1, "medium": 2, "high": 3, "blocker": 4}
    return rank.get(severity, 0) >= rank.get(min_severity, 2)


def run_for_chapter(
    db: Session,
    *,
    project_id: int,
    chapter_id: Optional[int] = None,
    trigger_comment_id: Optional[int] = None,
) -> Dict[str, Any]:
    """主 Agent 自动处理评论, 失败隔离."""
    settings = db.query(ReviewSettings).filter(
        ReviewSettings.project_id == project_id,
    ).first()
    if settings and not settings.auto_chief_triage:
        return {"status": "skipped", "reason": "auto_chief_triage disabled"}

    chief = get_chief_moderator_profile(db)
    if not chief:
        return {"status": "failed", "reason": "no chief_comment_moderator profile"}

    # 拉取待处理评论
    q = db.query(ReviewComment).filter(
        ReviewComment.project_id == project_id,
        ReviewComment.status == "new",
    )
    if chapter_id is not None:
        q = q.filter(ReviewComment.chapter_id == chapter_id)
    if trigger_comment_id is not None:
        q = q.filter(ReviewComment.id == trigger_comment_id)
    pending = q.order_by(ReviewComment.priority.desc(), ReviewComment.id.asc()).limit(10).all()

    if not pending:
        return {"status": "noop", "handled": 0}

    handled = 0
    failures: List[Dict[str, Any]] = []

    for comment in pending:
        try:
            _process_one(db, comment, chief, settings)
            handled += 1
        except Exception as exc:
            failures.append({"comment_id": comment.id, "error": str(exc)})
            print(f"[CommentTriage] comment {comment.id} failed: {exc}")
            continue

    db.commit()
    return {
        "status": "ok",
        "handled": handled,
        "failures": failures,
    }


def _process_one(
    db: Session,
    comment: ReviewComment,
    chief: ReaderAgentProfile,
    settings: Optional[ReviewSettings],
) -> None:
    """对单条评论做分流决策 (简化: 启发式)."""
    # 简化决策: severity high + reader_agent 标签 → discuss
    # user 评论 + non-low → reply
    # 低严重度 → ignore
    severity_tag = "low"
    if isinstance(comment.rating, dict) and "score" in comment.rating:
        score = comment.rating.get("score") or 75
        if score < 50:
            severity_tag = "blocker"
        elif score < 65:
            severity_tag = "high"
        elif score < 80:
            severity_tag = "medium"
        else:
            severity_tag = "low"

    min_sev = settings.min_severity_for_discussion if settings else "medium"

    # Action 1: reply (总是给一条简短确认, 避免空操作)
    reply = _reply_to_comment(
        db,
        source=comment,
        reply_text=f"已接入, 谢谢反馈。",
        chief=chief,
    )
    db.add(reply)
    comment.status = "replied"

    # Action 2: group + discuss (如果严重)
    if _severity_meets_threshold(severity_tag, min_sev):
        group_spec = {
            "title": f"{comment.author_label} 反馈: {comment.content[:30]}...",
            "summary": comment.content,
            "comment_ids": [comment.id],
            "severity": severity_tag,
        }
        group = _create_or_join_group(
            db, source=comment, group_spec=group_spec
        )
        comment.related_group_id = group.id
        comment.status = "grouped"

        # 决定是否建讨论
        if (
            settings is None
            or settings.auto_discussion
        ) and _severity_meets_threshold(severity_tag, "high"):
            session_id = create_discussion_from_group(
                db, group=group, source_comment=comment
            )
            group.discussion_session_id = session_id
            group.status = "discussing"
            comment.status = "discussing"
            enqueue_comment_discussion(
                db, project_id=comment.project_id, group_id=group.id,
                chapter_id=comment.chapter_id,
            )
    # 严重度低 — 只 reply, 不 group
