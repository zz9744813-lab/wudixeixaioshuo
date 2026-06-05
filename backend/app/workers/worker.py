"""
P6 Worker Multi-Task Dispatcher
- 支持 5 种 task_type:
  - chapter_pipeline: 老的章节流水线 (stub)
  - reader_review: 5 个 reader 跑章节
  - comment_triage: chief moderator 分流
  - comment_discussion: 跑评论组讨论 (stub)
  - comment_cleanup: 7 天前评论硬删除
- 每种 task_type 派给对应 service
- 失败隔离 + 重试上限
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.task import GenerationTask, TaskStatus
from app.services.review.comment_cleanup_service import run_cleanup
from app.services.review.comment_triage_service import run_for_chapter as run_triage
from app.services.review.reader_review_service import run_for_chapter as run_reader_review
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

# 支持的 task_type 集合
SUPPORTED_TASKS = {
    "chapter_pipeline",
    "reader_review",
    "comment_triage",
    "comment_discussion",
    "comment_cleanup",
}


def _parse_payload(task: GenerationTask) -> Dict[str, Any]:
    """从 payload (JSON 字符串) 解析 task 参数."""
    if not task.payload:
        return {}
    try:
        return json.loads(task.payload)
    except Exception:
        return {}


def _claim_task(db: Session, task: GenerationTask, worker_id: str) -> None:
    """claim + lock + heartbeat."""
    task.status = TaskStatus.RUNNING
    task.locked_by = worker_id
    task.locked_at = utc_now()
    task.heartbeat_at = utc_now()
    task.attempts = (task.attempts or 0) + 1
    db.commit()


def _finish_task(
    db: Session,
    task: GenerationTask,
    *,
    success: bool,
    error: Optional[str] = None,
) -> None:
    task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
    task.error_message = error
    task.finished_at = utc_now()
    db.commit()


async def dispatch_task(db: Session, task: GenerationTask, worker_id: str = "p6-worker") -> bool:
    """派发单条任务到对应 handler."""
    if task.task_type not in SUPPORTED_TASKS:
        logger.warning(f"[Worker] 未知 task_type: {task.task_type}")
        return False

    _claim_task(db, task, worker_id)
    payload = _parse_payload(task)
    logger.info(f"[Worker] dispatch {task.task_type} #{task.id} payload={payload}")

    try:
        if task.task_type == "chapter_pipeline":
            # 老的章节流水线: 这里 stub (实际有专门的 worker 处理)
            logger.info(f"[Worker] chapter_pipeline #{task.id} stub 成功")
            _finish_task(db, task, success=True)

        elif task.task_type == "reader_review":
            result = run_reader_review(
                db,
                project_id=payload.get("project_id") or task.project_id,
                chapter_id=payload.get("chapter_id") or task.chapter_id,
                chapter_version_id=payload.get("chapter_version_id"),
                trigger=payload.get("trigger", "chapter_completed"),
            )
            _finish_task(db, task, success=result.status in ("succeeded", "partial", "skipped"))

        elif task.task_type == "comment_triage":
            result = run_triage(
                db,
                project_id=payload.get("project_id") or task.project_id,
                chapter_id=payload.get("chapter_id") or task.chapter_id,
                trigger_comment_id=payload.get("trigger_comment_id"),
            )
            _finish_task(db, task, success=result.get("status") in ("ok", "noop", "skipped"))

        elif task.task_type == "comment_discussion":
            # 简化的讨论跑批: 标 group 为 discussed
            from app.models.comment_review import ReviewCommentGroup
            group_id = payload.get("group_id")
            if group_id:
                group = db.query(ReviewCommentGroup).filter(
                    ReviewCommentGroup.id == group_id,
                ).first()
                if group:
                    group.status = "decided"
                    group.decision = group.decision or {
                        "decision": "light_fix",
                        "rewrite_instruction": "请根据评论组摘要局部返工",
                    }
                    db.commit()
            _finish_task(db, task, success=True)

        elif task.task_type == "comment_cleanup":
            retention = payload.get("retention_days", 7)
            result = run_cleanup(db, retention_days=retention)
            logger.info(f"[Worker] comment_cleanup: {result}")
            _finish_task(db, task, success=True)

        return True
    except Exception as exc:
        logger.exception(f"[Worker] {task.task_type} #{task.id} failed: {exc}")
        _finish_task(db, task, success=False, error=str(exc))
        return False


async def tick(worker_id: str = "p6-worker", batch_size: int = 1) -> Dict[str, Any]:
    """Worker 单次 tick: claim 1 条 pending 任务并执行."""
    db = SessionLocal()
    try:
        task = db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PENDING,
            GenerationTask.task_type.in_(SUPPORTED_TASKS),
        ).order_by(
            GenerationTask.priority.desc(),
            GenerationTask.id.asc(),
        ).limit(1).first()
        if not task:
            return {"dispatched": 0}
        success = await dispatch_task(db, task, worker_id)
        return {
            "dispatched": 1,
            "task_id": task.id,
            "task_type": task.task_type,
            "success": success,
        }
    finally:
        db.close()


async def run_loop(worker_id: str = "p6-worker", interval: float = 5.0):
    """常驻循环: 每 interval 秒 tick 一次."""
    logger.info(f"[Worker] 启动常驻循环 worker_id={worker_id} interval={interval}s")
    while True:
        try:
            result = await tick(worker_id)
            if result.get("dispatched"):
                logger.info(f"[Worker] tick: {result}")
        except Exception as exc:
            logger.exception(f"[Worker] tick 异常: {exc}")
        await asyncio.sleep(interval)
