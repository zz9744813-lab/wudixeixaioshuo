"""
P6 Weight Service
- 评论被采纳 → reader weight +0.08, adopted_count + 1
- 评论被驳回 → reader weight -0.03, rejected_count + 1
- 上下限: [0.5, 2.5]
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.comment_review import ReaderAgentProfile, ReviewComment


WEIGHT_MIN = 0.5
WEIGHT_MAX = 2.5
WEIGHT_BUMP_ACCEPT = 0.08
WEIGHT_BUMP_REJECT = -0.03


def bump_for_comment(
    db: Session,
    *,
    comment: ReviewComment,
    decision: str,
) -> Optional[ReaderAgentProfile]:
    """根据裁决调整 reader 权重. 用户评论不影响任何 reader."""
    if comment.author_type != "reader_agent":
        return None
    if not comment.agent_role_id:
        return None
    profile = db.query(ReaderAgentProfile).filter(
        ReaderAgentProfile.agent_role_id == comment.agent_role_id,
    ).first()
    if not profile:
        return None

    if decision == "accepted":
        profile.weight = min(WEIGHT_MAX, (profile.weight or 1.0) + WEIGHT_BUMP_ACCEPT)
        profile.adopted_count = (profile.adopted_count or 0) + 1
    elif decision == "rejected":
        profile.weight = max(WEIGHT_MIN, (profile.weight or 1.0) + WEIGHT_BUMP_REJECT)
        profile.rejected_count = (profile.rejected_count or 0) + 1
    return profile
