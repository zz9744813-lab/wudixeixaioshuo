"""
Worker Task System Tests
Worker 任务系统测试
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.chapter import Chapter
from app.models.task import GenerationTask, TaskStatus
from app.services.task_service import TaskService


def test_claim_task_atomic(db_session: Session):
    """测试原子领取任务"""
    # 创建项目和章节
    project = Project(name="Test Project", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, chapter_index=1, title="Test", status="planned")
    db_session.add(chapter)
    db_session.commit()

    # 创建待处理任务
    task = GenerationTask(
        project_id=project.id,
        chapter_id=chapter.id,
        task_type="draft",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 使用 TaskService 领取任务
    service = TaskService(db_session)
    claimed = service.claim_task_safe()

    assert claimed is not None
    assert claimed.id == task_id
    assert claimed.status == TaskStatus.RUNNING
    assert claimed.locked_by is not None
    assert claimed.locked_at is not None


def test_claim_no_pending_task_returns_none(db_session: Session):
    """无待处理任务时应返回 None"""
    service = TaskService(db_session)
    claimed = service.claim_task_safe()
    assert claimed is None


def test_task_heartbeat_update(db_session: Session):
    """测试任务心跳更新"""
    # 创建任务
    project = Project(name="Test Project", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, chapter_index=1, title="Test", status="planned")
    db_session.add(chapter)
    db_session.commit()

    # 先创建 service 获取 worker_id
    service = TaskService(db_session)
    worker_id = service.worker_id

    task = GenerationTask(
        project_id=project.id,
        chapter_id=chapter.id,
        task_type="draft",
        status=TaskStatus.RUNNING,
        locked_by=worker_id,  # 使用相同的 worker_id
        locked_at=datetime.utcnow(),
    )
    db_session.add(task)
    db_session.commit()

    # 更新心跳
    result = service.update_heartbeat(task.id)

    # 验证心跳已更新
    assert result is True
    db_session.refresh(task)
    assert task.heartbeat_at is not None


def test_zombie_task_recovery(db_session: Session):
    """测试僵尸任务恢复"""
    # 创建一个过期的运行中任务（模拟僵尸）
    project = Project(name="Test Project", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, chapter_index=1, title="Test", status="planned")
    db_session.add(chapter)
    db_session.commit()

    old_time = datetime.utcnow() - timedelta(minutes=20)

    task = GenerationTask(
        project_id=project.id,
        chapter_id=chapter.id,
        task_type="draft",
        status=TaskStatus.RUNNING,
        locked_by="dead-worker",
        locked_at=old_time,
        heartbeat_at=old_time,
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 恢复僵尸任务
    recovered = TaskService.recover_zombies_on_startup(db_session)

    assert recovered == 1

    # 验证任务已重置为 pending
    db_session.refresh(task)
    assert task.status == TaskStatus.PENDING
    assert task.locked_by is None
    assert task.attempts == 1  # 尝试次数增加


def test_task_failure_with_retry(db_session: Session):
    """测试任务失败重试"""
    # 创建任务
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
        status=TaskStatus.RUNNING,
        locked_by="test-worker",
        locked_at=datetime.utcnow(),
        attempts=0,
        max_attempts=3,
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 处理失败（可重试）
    service = TaskService(db_session)
    service.handle_task_failure(task_id, "Network error", is_retryable=True)

    # 验证任务状态
    db_session.refresh(task)
    assert task.status == TaskStatus.PENDING  # 回到 pending 等待重试
    assert task.attempts == 1
    assert task.error_message == "Network error"
    assert task.next_run_at is not None  # 设置了下次运行时间


def test_task_failure_non_retryable(db_session: Session):
    """测试不可重试的失败"""
    # 创建任务
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
        status=TaskStatus.RUNNING,
        locked_by="test-worker",
        attempts=0,
        max_attempts=3,
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 处理失败（不可重试）
    service = TaskService(db_session)
    service.handle_task_failure(task_id, "Invalid API key", is_retryable=False)

    # 验证任务状态
    db_session.refresh(task)
    assert task.status == TaskStatus.FAILED  # 直接失败
    assert task.attempts == 1


def test_task_failure_max_attempts(db_session: Session):
    """测试达到最大尝试次数"""
    # 创建任务
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
        status=TaskStatus.RUNNING,
        locked_by="test-worker",
        attempts=2,  # 已经尝试2次
        max_attempts=3,
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 第3次失败
    service = TaskService(db_session)
    service.handle_task_failure(task_id, "Still failing", is_retryable=True)

    # 验证任务状态
    db_session.refresh(task)
    assert task.status == TaskStatus.FAILED  # 达到最大次数，失败
    assert task.attempts == 3


def test_task_success_completion(db_session: Session):
    """测试任务成功完成"""
    # 创建任务
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
        status=TaskStatus.RUNNING,
        locked_by="test-worker",
        locked_at=datetime.utcnow(),
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 处理成功
    service = TaskService(db_session)
    service.handle_task_success(task_id)

    # 验证任务状态
    db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
    assert task.finished_at is not None
