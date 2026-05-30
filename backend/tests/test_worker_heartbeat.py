"""
Worker 心跳一致性测试 (P0-2)
验证 TaskService 使用外部固定 worker_id 时，claim 与 heartbeat 的 worker_id 一致。
"""

import logging

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.chapter import Chapter
from app.models.task import GenerationTask, TaskStatus
from app.services.task_service import TaskService


def _make_pending_task(db_session: Session) -> GenerationTask:
    project = Project(name="Test Project", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, chapter_index=1, title="Test", status="planned")
    db_session.add(chapter)
    db_session.commit()

    task = GenerationTask(
        project_id=project.id,
        chapter_id=chapter.id,
        task_type="draft",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    return task


def test_claim_sets_fixed_worker_id(db_session: Session):
    """claim 后 locked_by 等于 Worker 固定 worker_id"""
    _make_pending_task(db_session)

    fixed_worker_id = "worker-fixed01"
    service = TaskService(db_session, worker_id=fixed_worker_id)

    claimed = service.claim_task_safe()

    assert claimed is not None
    assert claimed.status == TaskStatus.RUNNING
    assert claimed.locked_by == fixed_worker_id


def test_heartbeat_succeeds_and_keeps_worker_id(db_session: Session, caplog):
    """心跳能成功更新，locked_by 不变，且不出现“不由当前 Worker 持有”的警告"""
    _make_pending_task(db_session)

    fixed_worker_id = "worker-fixed01"
    service = TaskService(db_session, worker_id=fixed_worker_id)

    claimed = service.claim_task_safe()
    assert claimed is not None
    task_id = claimed.id

    with caplog.at_level(logging.WARNING):
        result = service.update_heartbeat(task_id)

    assert result is True

    db_session.refresh(claimed)
    assert claimed.heartbeat_at is not None
    assert claimed.locked_by == fixed_worker_id

    assert "不由当前Worker持有" not in caplog.text
    assert "不由当前 Worker 持有" not in caplog.text
