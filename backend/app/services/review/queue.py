"""
P6 Review Queue Service
- 章节完成后入队 reader_review 任务
- 用户/读者评论后入队 comment_triage
- 评论组裁决后入队 comment_discussion
- 定时入队 comment_cleanup
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.task import GenerationTask, TaskStatus, TaskPriority


def enqueue_task(
    db: Session,
    *,
    project_id: int,
    task_type: str,
    payload: Dict[str, Any],
    chapter_id: Optional[int] = None,
    priority: int = 50,
) -> GenerationTask:
    """通用入队 helper (复用 GenerationTask 表)."""
    import json
    task = GenerationTask(
        project_id=project_id,
        chapter_id=chapter_id,
        task_type=task_type,
        status=TaskStatus.PENDING,
        priority=priority,
        target_agent=task_type,
        max_attempts=3,
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.add(task)
    db.flush()
    return task


def enqueue_reader_review(
    db: Session,
    *,
    project_id: int,
    chapter_id: int,
    chapter_version_id: Optional[int] = None,
    trigger: str = "chapter_completed",
    priority: int = 60,
) -> GenerationTask:
    return enqueue_task(
        db,
        project_id=project_id,
        task_type="reader_review",
        chapter_id=chapter_id,
        payload={
            "project_id": project_id,
            "chapter_id": chapter_id,
            "chapter_version_id": chapter_version_id,
            "trigger": trigger,
        },
        priority=priority,
    )


def enqueue_comment_triage(
    db: Session,
    *,
    project_id: int,
    chapter_id: Optional[int] = None,
    trigger_comment_id: Optional[int] = None,
    priority: int = 70,
) -> GenerationTask:
    return enqueue_task(
        db,
        project_id=project_id,
        task_type="comment_triage",
        chapter_id=chapter_id,
        payload={
            "project_id": project_id,
            "chapter_id": chapter_id,
            "trigger_comment_id": trigger_comment_id,
        },
        priority=priority,
    )


def enqueue_comment_cleanup(
    db: Session,
    *,
    project_id: Optional[int] = None,
    retention_days: int = 7,
    priority: int = 10,
) -> GenerationTask:
    return enqueue_task(
        db,
        project_id=project_id or 0,
        task_type="comment_cleanup",
        payload={"retention_days": retention_days},
        priority=priority,
    )


def enqueue_comment_discussion(
    db: Session,
    *,
    project_id: int,
    group_id: int,
    chapter_id: Optional[int] = None,
    priority: int = 70,
) -> GenerationTask:
    return enqueue_task(
        db,
        project_id=project_id,
        task_type="comment_discussion",
        chapter_id=chapter_id,
        payload={
            "project_id": project_id,
            "group_id": group_id,
        },
        priority=priority,
    )
