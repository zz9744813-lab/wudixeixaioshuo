"""
Task Queue Service - 写作任务队列管理 (P3版本)
基于 GenerationTask 的队列管理
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.models.task import GenerationTask, TaskStatus, TaskPriority, TaskType

logger = logging.getLogger(__name__)


class TaskQueueService:
    """
    写作任务队列管理

    功能：
    - 批量创建 GenerationTask
    - 优先级管理
    - 自动排序
    - 进度追踪
    """

    def __init__(self, db: Session):
        self.db = db

    def add_chapters_to_queue(
        self,
        project_id: int,
        chapter_ids: Optional[List[int]] = None
    ) -> dict:
        """
        添加章节到写作队列 - 创建 GenerationTask
        """
        query = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status.in_([ChapterStatus.PLANNED, ChapterStatus.FAILED])
        )

        if chapter_ids:
            query = query.filter(Chapter.id.in_(chapter_ids))

        chapters = query.order_by(Chapter.chapter_index.asc()).all()

        created_tasks = []
        for chapter in chapters:
            # 检查是否已存在待处理的任务
            existing = self.db.query(GenerationTask).filter(
                GenerationTask.chapter_id == chapter.id,
                GenerationTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
            ).first()

            if existing:
                continue

            # 创建新的生成任务
            gen_task = GenerationTask(
                project_id=project_id,
                chapter_id=chapter.id,
                task_type=TaskType.DRAFT,
                status=TaskStatus.PENDING,
                priority=TaskPriority.NORMAL,
                target_agent="full_pipeline",
            )
            self.db.add(gen_task)
            created_tasks.append(gen_task)

            # 更新章节状态
            chapter.status = ChapterStatus.PLANNED

        self.db.commit()

        # 刷新获取ID
        for task in created_tasks:
            self.db.refresh(task)

        logger.info(f"已创建 {len(created_tasks)} 个 GenerationTask")

        return {
            "added_count": len(created_tasks),
            "task_ids": [t.id for t in created_tasks],
            "chapter_ids": [t.chapter_id for t in created_tasks],
            "project_id": project_id,
        }

    def remove_from_queue(self, chapter_id: int) -> bool:
        """从队列中移除章节 - 取消 GenerationTask"""
        # 查找并取消相关的待处理任务
        tasks = self.db.query(GenerationTask).filter(
            GenerationTask.chapter_id == chapter_id,
            GenerationTask.status.in_([TaskStatus.PENDING, TaskStatus.PAUSED])
        ).all()

        for task in tasks:
            task.status = TaskStatus.CANCELLED
            task.finished_at = datetime.utcnow()

        self.db.commit()
        return len(tasks) > 0

    def get_queue_status(self, project_id: Optional[int] = None) -> dict:
        """获取队列状态 - 基于 GenerationTask"""
        query = self.db.query(GenerationTask)

        if project_id:
            query = query.filter(GenerationTask.project_id == project_id)

        # 统计各状态数量
        pending = query.filter(GenerationTask.status == TaskStatus.PENDING).count()
        running = query.filter(GenerationTask.status == TaskStatus.RUNNING).count()
        paused = query.filter(GenerationTask.status == TaskStatus.PAUSED).count()
        completed = query.filter(GenerationTask.status == TaskStatus.COMPLETED).count()
        failed = query.filter(GenerationTask.status == TaskStatus.FAILED).count()
        cancelled = query.filter(GenerationTask.status == TaskStatus.CANCELLED).count()

        total = pending + running + paused + completed + failed

        # 获取今日统计
        today = datetime.utcnow().date()
        today_completed = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.COMPLETED,
            GenerationTask.finished_at >= today
        ).count()

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "paused": paused,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "today_completed": today_completed,
            "progress": {
                "percentage": (completed / total * 100) if total > 0 else 0,
                "completed": completed,
                "total": total,
            }
        }

    def get_next_task(self, project_id: Optional[int] = None) -> Optional[GenerationTask]:
        """获取下一个待处理任务 - 返回 GenerationTask"""
        query = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PENDING
        )

        if project_id:
            query = query.filter(GenerationTask.project_id == project_id)

        return query.order_by(
            GenerationTask.priority.desc(),
            GenerationTask.created_at.asc()
        ).first()

    def reorder_queue(
        self,
        task_ids: List[int]
    ) -> bool:
        """重新排序队列 - 通过调整优先级"""
        try:
            for index, task_id in enumerate(task_ids):
                task = self.db.query(GenerationTask).filter(
                    GenerationTask.id == task_id
                ).first()

                if task:
                    # 使用优先级表示顺序（数值越大优先级越高）
                    task.priority = len(task_ids) - index

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"重新排序失败: {e}")
            self.db.rollback()
            return False

    def pause_queue(self, project_id: Optional[int] = None) -> int:
        """暂停队列"""
        query = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PENDING
        )

        if project_id:
            query = query.filter(GenerationTask.project_id == project_id)

        tasks = query.all()
        count = len(tasks)

        for task in tasks:
            task.status = TaskStatus.PAUSED

        self.db.commit()
        return count

    def resume_queue(self, project_id: Optional[int] = None) -> int:
        """恢复队列"""
        query = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PAUSED
        )

        if project_id:
            query = query.filter(GenerationTask.project_id == project_id)

        tasks = query.all()
        count = len(tasks)

        for task in tasks:
            task.status = TaskStatus.PENDING

        self.db.commit()
        return count

    def clear_failed(self, project_id: Optional[int] = None) -> int:
        """清空失败的任务，重置为 pending"""
        query = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.FAILED
        )

        if project_id:
            query = query.filter(GenerationTask.project_id == project_id)

        tasks = query.all()
        count = len(tasks)

        for task in tasks:
            task.status = TaskStatus.PENDING
            task.retry_count = 0
            task.error_message = None

        self.db.commit()
        return count

    def get_writing_plan(self, project_id: int) -> dict:
        """获取写作计划"""
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        # 获取所有任务
        tasks = self.db.query(GenerationTask).filter(
            GenerationTask.project_id == project_id
        ).order_by(GenerationTask.created_at.asc()).all()

        # 获取关联的章节信息
        chapters_info = []
        for task in tasks:
            chapter = self.db.query(Chapter).filter(
                Chapter.id == task.chapter_id
            ).first()
            if chapter:
                chapters_info.append({
                    "task_id": task.id,
                    "chapter_id": chapter.id,
                    "title": chapter.title,
                    "chapter_index": chapter.chapter_index,
                    "status": task.status,
                    "priority": task.priority,
                })

        daily_goal = project.config.get("daily_word_goal", 10000) if project.config else 10000
        token_budget = project.config.get("daily_token_budget", 100000) if project.config else 100000

        # 估算总字数和天数
        total_chapters = len(chapters_info)
        estimated_words = total_chapters * 3000  # 平均每章3000字
        estimated_days = estimated_words / daily_goal if daily_goal > 0 else 0

        return {
            "project_id": project_id,
            "total_tasks": len(tasks),
            "total_chapters": total_chapters,
            "estimated_words": estimated_words,
            "daily_word_goal": daily_goal,
            "daily_token_budget": token_budget,
            "estimated_days": round(estimated_days, 1),
            "tasks": chapters_info,
        }

    def get_task_details(self, task_id: int) -> Optional[dict]:
        """获取任务详情"""
        task = self.db.query(GenerationTask).filter(
            GenerationTask.id == task_id
        ).first()

        if not task:
            return None

        chapter = self.db.query(Chapter).filter(
            Chapter.id == task.chapter_id
        ).first()

        return {
            "task_id": task.id,
            "project_id": task.project_id,
            "chapter_id": task.chapter_id,
            "chapter_title": chapter.title if chapter else None,
            "task_type": task.task_type,
            "status": task.status,
            "priority": task.priority,
            "progress": {
                "completed_steps": task.completed_steps,
                "total_steps": task.total_steps,
            },
            "cost": {
                "estimated": task.estimated_cost,
                "actual": task.actual_cost,
            },
            "tokens": task.token_used,
            "retry_count": task.retry_count,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        }
