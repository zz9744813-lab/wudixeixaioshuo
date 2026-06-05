"""
P6 Discussion Bridge
- 从 ReviewCommentGroup 创建 DiscussionSession
- 复用现有讨论区, 不另建新表
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.comment_review import ReviewComment, ReviewCommentGroup
from app.models.project import Project
from app.utils.time_utils import utc_now


# 默认参与者策略 (按评论类型)
PARTICIPANT_PRESETS = {
    "default": ["planner", "drafter", "critic", "continuity", "memory"],
    "emotion": ["planner", "drafter", "critic", "continuity"],
    "logic": ["planner", "critic", "continuity", "memory"],
    "commercial": ["planner", "drafter", "critic"],
    "toxic": ["drafter", "critic"],
    "structure": ["planner", "drafter", "critic", "continuity", "memory"],
}


def _detect_topic(tags: List[str]) -> str:
    """根据评论 tags 判断讨论类型."""
    if not tags:
        return "default"
    text = " ".join(tags).lower()
    if any(k in text for k in ["人物动机", "情绪", "感情", "关系"]):
        return "emotion"
    if any(k in text for k in ["设定", "伏笔", "逻辑"]):
        return "logic"
    if any(k in text for k in ["节奏", "留存", "爽点", "商业"]):
        return "commercial"
    if any(k in text for k in ["毒点", "解释腔", "工具人"]):
        return "toxic"
    if any(k in text for k in ["结构", "大纲", "整体"]):
        return "structure"
    return "default"


def _build_topic(
    db: Session,
    group: ReviewCommentGroup,
    comments: List[ReviewComment],
) -> Dict[str, Any]:
    """构造讨论议题."""
    project = db.query(Project).filter(Project.id == group.project_id).first()
    project_name = project.name if project else "项目"

    # 收集参与评论 (前 5 条)
    related = comments[:5]
    related_text = "\n".join(
        f"{i+1}. {c.author_label or c.author_type}: {c.content[:80]}..."
        for i, c in enumerate(related)
    )

    topic_tags = []
    for c in related:
        if isinstance(c.tags, list):
            topic_tags.extend(c.tags)
    topic = _detect_topic(topic_tags)
    participants = PARTICIPANT_PRESETS.get(topic, PARTICIPANT_PRESETS["default"])

    return {
        "title": f"{project_name} · 评论组合并议题",
        "source": "评论区自动生成",
        "target": f"{project_name} / 第 {group.chapter_id} 章",
        "summary": group.summary or group.title or "",
        "severity": group.severity,
        "related_comments": related_text,
        "questions": [
            "是否值得修改?",
            "是轻修、局部返工还是大返工?",
            "具体修改位置在哪里?",
            "修改后如何验证?",
        ],
        "participants": participants,
    }


def create_discussion_from_group(
    db: Session,
    *,
    group: ReviewCommentGroup,
    source_comment: ReviewComment,
) -> Optional[int]:
    """从评论组创建 DiscussionSession.

    简化: 直接 SQL INSERT (因为 discussion_sessions 表结构未知, 走 raw SQL 安全).
    """
    # 拉评论组所有评论
    related_ids = list(group.comment_ids or [])
    if source_comment.id not in related_ids:
        related_ids.append(source_comment.id)
    related = db.query(ReviewComment).filter(
        ReviewComment.id.in_(related_ids),
    ).all()

    topic = _build_topic(db, group, related)

    # 构造议题 JSON
    issue_text = (
        f"来源: {topic['source']}\n"
        f"对象: {topic['target']}\n\n"
        f"摘要: {topic['summary']}\n"
        f"严重度: {topic['severity']}\n\n"
        f"关联评论:\n{topic['related_comments']}\n\n"
        f"请讨论:\n"
        + "\n".join(f"- {q}" for q in topic["questions"])
    )

    # 尝试插入 discussion_sessions
    try:
        result = db.execute(
            text(
                """
                INSERT INTO discussion_sessions
                (project_id, chapter_id, title, issue, status, participants_json, created_at, updated_at)
                VALUES (:project_id, :chapter_id, :title, :issue, :status, :participants, :now, :now)
                """
            ),
            {
                "project_id": group.project_id,
                "chapter_id": group.chapter_id,
                "title": topic["title"][:200],
                "issue": issue_text,
                "status": "running",
                "participants": __import__("json").dumps(topic["participants"], ensure_ascii=False),
                "now": utc_now(),
            },
        )
        session_id = result.lastrowid
        db.commit()
        return session_id
    except Exception as exc:
        # 讨论表可能不存在 — 优雅降级
        print(f"[DiscussionBridge] discussion_sessions 表可能不存在, 跳过: {exc}")
        db.rollback()
        return None
