"""
Task Queue Service - 写作任务队列管理
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project

logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    """队列状态"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskQueueService:
    """
    写作任务队列管理

    功能：
    - 批量添加章节到队列
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
        添加章节到写作队列

        Args:
            project_id: 项目ID
            chapter_ids: 指定章节ID列表，None 表示添加所有待写作章节

        Returns:
            添加结果统计
        """
        query = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status.in_([ChapterStatus.PENDING, ChapterStatus.FAILED])
        )

        if chapter_ids:
            query = query.filter(Chapter.id.in_(chapter_ids))

        chapters = query.order_by(Chapter.order_num.asc()).all()

        added_count = 0
        for chapter in chapters:
            chapter.status = ChapterStatus.PENDING
            chapter.metadata = chapter.metadata or {}
            chapter.metadata["queued_at"] = datetime.now().isoformat()
            chapter.metadata["queue_status"] = QueueStatus.QUEUED.value
            added_count += 1

        self.db.commit()

        logger.info(f"已添加 {added_count} 个章节到队列")

        return {
            "added_count": added_count,
            "chapter_ids": [c.id for c in chapters],
            "project_id": project_id,
        }

    def remove_from_queue(self, chapter_id: int) -> bool:
        """从队列中移除章节"""
        chapter = self.db.query(Chapter).filter(
            Chapter.id == chapter_id
        ).first()

        if not chapter:
            return False

        if chapter.status in [ChapterStatus.PENDING, ChapterStatus.FAILED]:
            chapter.status = ChapterStatus.PENDING
            if chapter.metadata:
                chapter.metadata["queue_status"] = QueueStatus.PENDING.value
                chapter.metadata["removed_at"] = datetime.now().isoformat()
            self.db.commit()
            return True

        return False

    def get_queue_status(self, project_id: Optional[int] = None) -> dict:
        """获取队列状态"""
        query = self.db.query(Chapter)

        if project_id:
            query = query.filter(Chapter.project_id == project_id)

        # 统计各状态数量
        pending = query.filter(Chapter.status == ChapterStatus.PENDING).count()
        writing = query.filter(Chapter.status == ChapterStatus.WRITING).count()
        review = query.filter(Chapter.status == ChapterStatus.REVIEW).count()
        completed = query.filter(Chapter.status == ChapterStatus.COMPLETED).count()
        failed = query.filter(Chapter.status == ChapterStatus.FAILED).count()

        total = pending + writing + review + completed + failed

        return {
            "total": total,
            "pending": pending,
            "writing": writing,
            "review": review,
            "completed": completed,
            "failed": failed,
            "progress": {
                "percentage": (completed / total * 100) if total > 0 else 0,
                "completed": completed,
                "total": total,
            }
        }

    def get_next_task(self, project_id: Optional[int] = None) -> Optional[Chapter]:
        """获取下一个待处理任务"""
        query = self.db.query(Chapter).filter(
            Chapter.status == ChapterStatus.PENDING
        )

        if project_id:
            query = query.filter(Chapter.project_id == project_id)

        return query.order_by(Chapter.order_num.asc()).first()

    def reorder_queue(
        self,
        chapter_ids: List[int]
    ) -> bool:
        """
        重新排序队列

        Args:
            chapter_ids: 按新顺序排列的章节ID列表
        """
        try:
            for index, chapter_id in enumerate(chapter_ids):
                chapter = self.db.query(Chapter).filter(
                    Chapter.id == chapter_id
                ).first()

                if chapter:
                    chapter.order_num = index + 1
                    if chapter.metadata:
                        chapter.metadata["reordered_at"] = datetime.now().isoformat()

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"重新排序失败: {e}")
            self.db.rollback()
            return False

    def pause_queue(self, project_id: Optional[int] = None) -> int:
        """暂停队列（将 pending 改为 paused）"""
        query = self.db.query(Chapter).filter(
            Chapter.status == ChapterStatus.PENDING
        )

        if project_id:
            query = query.filter(Chapter.project_id == project_id)

        chapters = query.all()
        count = len(chapters)

        for chapter in chapters:
            if chapter.metadata:
                chapter.metadata["paused_at"] = datetime.now().isoformat()
                chapter.metadata["queue_status"] = QueueStatus.PENDING.value

        self.db.commit()
        return count

    def clear_failed(self, project_id: Optional[int] = None) -> int:
        """清空失败的章节，重置为 pending"""
        query = self.db.query(Chapter).filter(
            Chapter.status == ChapterStatus.FAILED
        )

        if project_id:
            query = query.filter(Chapter.project_id == project_id)

        chapters = query.all()
        count = len(chapters)

        for chapter in chapters:
            chapter.status = ChapterStatus.PENDING
            if chapter.metadata:
                chapter.metadata["retried_at"] = datetime.now().isoformat()

        self.db.commit()
        return count

    def get_writing_plan(self, project_id: int) -> dict:
        """获取写作计划"""
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        ).order_by(Chapter.order_num.asc()).all()

        daily_goal = project.config.get("daily_word_goal", 10000)
        token_budget = project.config.get("daily_token_budget", 100000)

        # 估算总字数和天数
        total_words = sum(
            c.metadata.get("word_count", 3000) for c in chapters
        )
        estimated_days = total_words / daily_goal if daily_goal > 0 else 0

        return {
            "project_id": project_id,
            "total_chapters": len(chapters),
            "total_words": total_words,
            "daily_word_goal": daily_goal,
            "daily_token_budget": token_budget,
            "estimated_days": round(estimated_days, 1),
            "chapters": [
                {
                    "id": c.id,
                    "title": c.title,
                    "order_num": c.order_num,
                    "status": c.status.value,
                    "estimated_words": c.metadata.get("word_count", 3000),
                }
                for c in chapters
            ]
        }
