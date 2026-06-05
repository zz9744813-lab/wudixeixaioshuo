"""
P6 Comment Cleanup Service
- 7 天前的普通评论自动硬删除
- 不动讨论记录 (DiscussionSession / DiscussionTurn)
- 不影响读者权重统计
"""

from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.models.comment_review import ReviewComment
from app.utils.time_utils import utc_now


def run_cleanup(db: Session, *, retention_days: int = 7) -> Dict[str, Any]:
    """清理 retention_days 天前的已过期评论.

    保留:
    - 状态为 discussing 的评论 (讨论室还在跑, 不删)
    - 状态为 accepted/rejected 的评论 (历史决策)
    - chief_agent / system 的 (系统消息)

    删除:
    - user / reader_agent 评论且 expires_at < now()
    """
    now = utc_now()
    # 找出可删除的评论
    candidates = db.query(ReviewComment).filter(
        ReviewComment.expires_at != None,
        ReviewComment.expires_at < now,
    ).all()

    deleted_user = 0
    deleted_reader = 0
    skipped_discussing = 0
    skipped_decided = 0

    for c in candidates:
        if c.status in ("discussing", "accepted", "rejected"):
            skipped_discussed = "discussing" if c.status == "discussing" else "decided"
            if skipped_discussed == "discussing":
                skipped_discussing += 1
            else:
                skipped_decided += 1
            continue
        if c.author_type not in ("user", "reader_agent"):
            continue
        if c.author_type == "user":
            deleted_user += 1
        else:
            deleted_reader += 1
        db.delete(c)

    db.commit()
    return {
        "deleted_user": deleted_user,
        "deleted_reader": deleted_reader,
        "skipped_discussing": skipped_discussing,
        "skipped_decided": skipped_decided,
        "ran_at": now.isoformat(),
    }
