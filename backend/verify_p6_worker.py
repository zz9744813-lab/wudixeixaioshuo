"""
P6 Worker Dispatcher 端到端测试
- 5 种 task_type 都能被 dispatch
- chapter_pipeline / reader_review / comment_triage / comment_discussion / comment_cleanup
"""

import sys
import os
import asyncio
import json
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal
from app.models.task import GenerationTask, TaskStatus
from app.models.comment_review import ReviewComment, ReviewSettings
from app.workers.worker import dispatch_task, SUPPORTED_TASKS, tick
from app.services.review.queue import (
    enqueue_comment_cleanup,
    enqueue_comment_triage,
    enqueue_reader_review,
)


def setup_project(db):
    from app.models.project import Project
    from app.models.chapter import Chapter, ChapterVersion
    project = db.query(Project).filter(Project.id == 9999).first()
    if not project:
        project = Project(id=9999, name="Worker测试", genre="测试")
        db.add(project); db.flush()
    chapter = db.query(Chapter).filter(Chapter.id == 9998).first()
    if not chapter:
        chapter = Chapter(id=9998, project_id=9999, chapter_index=1, title="W章", status="completed")
        db.add(chapter); db.flush()
    ver = db.query(ChapterVersion).filter(ChapterVersion.id == 9997).first()
    if not ver:
        ver = ChapterVersion(id=9997, chapter_id=9998, version_number=1, final_content="测试正文。")
        db.add(ver); db.flush()
    db.commit()
    return project, chapter, ver


async def t1_supported_tasks():
    """5 种 task_type 都被支持."""
    expected = {
        "chapter_pipeline", "reader_review", "comment_triage",
        "comment_discussion", "comment_cleanup",
    }
    assert SUPPORTED_TASKS == expected, f"SUPPORTED_TASKS 不匹配: {SUPPORTED_TASKS ^ expected}"
    print(f"   ✓ SUPPORTED_TASKS 包含 5 种: {sorted(SUPPORTED_TASKS)}")


async def t2_dispatch_reader_review():
    """dispatch reader_review 任务."""
    db = SessionLocal()
    try:
        project, chapter, ver = setup_project(db)
        task = enqueue_reader_review(
            db,
            project_id=project.id,
            chapter_id=chapter.id,
            chapter_version_id=ver.id,
            trigger="worker_test",
        )
        db.commit()
        task_id = task.id
        success = await dispatch_task(db, task, "test-worker")
        assert success, "reader_review dispatch 失败"
        # 重新读 task 状态
        db.refresh(task)
        assert task.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING)
        print(f"   ✓ reader_review task #{task_id} dispatch 成功, status={task.status}")
    finally:
        db.close()


async def t3_dispatch_comment_triage():
    """dispatch comment_triage 任务."""
    db = SessionLocal()
    try:
        project, chapter, ver = setup_project(db)
        # 先创建一条新评论
        expires = __import__("datetime").datetime.utcnow() + timedelta(days=7)
        c = ReviewComment(
            project_id=project.id,
            chapter_id=chapter.id,
            author_type="user",
            author_label="dispatch测试",
            content="T3 测试评论",
            status="new",
            expires_at=expires,
        )
        db.add(c); db.flush()
        c_id = c.id
        # 入队
        task = enqueue_comment_triage(
            db,
            project_id=project.id,
            chapter_id=chapter.id,
            trigger_comment_id=c_id,
        )
        db.commit()
        task_id = task.id
        success = await dispatch_task(db, task, "test-worker")
        assert success, "comment_triage dispatch 失败"
        db.refresh(task)
        # 验证 comment status 变化
        db.refresh(c)
        assert c.status in ("replied", "grouped", "discussing")
        print(f"   ✓ comment_triage task #{task_id} dispatch 成功, comment #{c_id} status={c.status}")
    finally:
        db.close()


async def t4_dispatch_comment_cleanup():
    """dispatch comment_cleanup 任务."""
    db = SessionLocal()
    try:
        # 加一条过期评论
        expired = ReviewComment(
            project_id=9999,
            author_type="user",
            author_label="过期",
            content="这条快删",
            status="new",
            expires_at=__import__("datetime").datetime.utcnow() - timedelta(days=1),
        )
        db.add(expired); db.flush()
        e_id = expired.id
        db.commit()
        # 入队
        task = enqueue_comment_cleanup(db, project_id=9999, retention_days=7)
        db.commit()
        task_id = task.id
        success = await dispatch_task(db, task, "test-worker")
        assert success
        db.refresh(task)
        # 验证已删
        assert db.query(ReviewComment).filter(ReviewComment.id == e_id).first() is None
        print(f"   ✓ comment_cleanup task #{task_id} dispatch 成功, 过期评论 #{e_id} 已删")
    finally:
        db.close()


async def t5_dispatch_comment_discussion():
    """dispatch comment_discussion 任务."""
    db = SessionLocal()
    try:
        from app.models.comment_review import ReviewCommentGroup
        # 先建一个组
        group = ReviewCommentGroup(
            project_id=9999,
            chapter_id=9998,
            title="dispatch 测试组",
            summary="",
            comment_ids=[],
            severity="high",
            status="discussing",
        )
        db.add(group); db.flush()
        g_id = group.id
        db.commit()
        # 入队
        from app.services.review.queue import enqueue_comment_discussion
        task = enqueue_comment_discussion(
            db, project_id=9999, group_id=g_id, chapter_id=9998
        )
        db.commit()
        task_id = task.id
        success = await dispatch_task(db, task, "test-worker")
        assert success
        db.refresh(task)
        db.refresh(group)
        assert group.status == "decided"
        print(f"   ✓ comment_discussion task #{task_id} dispatch 成功, group #{g_id} status={group.status}")
    finally:
        db.close()


async def t6_dispatch_chapter_pipeline():
    """dispatch chapter_pipeline 任务 (stub)."""
    db = SessionLocal()
    try:
        task = GenerationTask(
            project_id=9999,
            chapter_id=9998,
            task_type="chapter_pipeline",
            status=TaskStatus.PENDING,
            priority=10,
        )
        db.add(task); db.flush()
        task_id = task.id
        db.commit()
        success = await dispatch_task(db, task, "test-worker")
        assert success
        db.refresh(task)
        assert task.status == TaskStatus.COMPLETED
        print(f"   ✓ chapter_pipeline task #{task_id} dispatch 成功 (stub)")
    finally:
        db.close()


async def t7_tick_picks_pending():
    """tick 自动 claim 1 条 pending 任务并执行."""
    db = SessionLocal()
    try:
        # 先清掉之前的 pending 任务 (避免被其他类型抢)
        from app.models.task import GenerationTask
        db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PENDING,
        ).delete()
        db.commit()
        # 再建一条 pending 任务
        task = GenerationTask(
            project_id=9999,
            chapter_id=9998,
            task_type="comment_cleanup",
            status=TaskStatus.PENDING,
            priority=5,
            payload=json.dumps({"retention_days": 7}),
        )
        db.add(task); db.commit()
        result = await tick("test-worker")
        assert result["dispatched"] == 1
        assert result["task_type"] == "comment_cleanup"
        print(f"   ✓ tick 自动 claim + dispatch: {result}")
    finally:
        db.close()


async def main():
    print("=" * 60)
    print("P6 Worker Dispatcher 端到端测试")
    print("=" * 60)
    print("\n[T1] SUPPORTED_TASKS 5 种")
    await t1_supported_tasks()
    print("\n[T2] dispatch reader_review")
    await t2_dispatch_reader_review()
    print("\n[T3] dispatch comment_triage")
    await t3_dispatch_comment_triage()
    print("\n[T4] dispatch comment_cleanup")
    await t4_dispatch_comment_cleanup()
    print("\n[T5] dispatch comment_discussion")
    await t5_dispatch_comment_discussion()
    print("\n[T6] dispatch chapter_pipeline (stub)")
    await t6_dispatch_chapter_pipeline()
    print("\n[T7] tick 自动 claim")
    await t7_tick_picks_pending()
    print("\n" + "=" * 60)
    print("P6 Worker 全部端到端测试通过 ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
