"""
Worker Service - 24小时自动写作后台任务调度器
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.services.writing_pipeline_service import WritingPipelineService

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Worker 状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 暂停
    STOPPED = "stopped"     # 停止


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class WritingWorker:
    """
    24小时自动写作 Worker

    功能：
    - 自动从队列获取待写作任务
    - 执行写作流水线
    - 监控每日字数/Token 预算
    - 自动触发下一章
    """

    def __init__(self):
        self.status = WorkerStatus.STOPPED
        self.current_task: Optional[dict] = None
        self.daily_stats = {
            "words_written": 0,
            "chapters_completed": 0,
            "tokens_used": 0,
            "start_time": None,
        }
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.pipeline_service = WritingPipelineService()

    async def start(self):
        """启动 Worker"""
        if self.status == WorkerStatus.RUNNING:
            logger.info("Worker 已在运行中")
            return

        self.status = WorkerStatus.RUNNING
        self._stop_event.clear()
        self.daily_stats["start_time"] = datetime.now()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Worker 已启动")

    async def stop(self):
        """停止 Worker"""
        self.status = WorkerStatus.STOPPED
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Worker 已停止")

    async def pause(self):
        """暂停 Worker"""
        self.status = WorkerStatus.PAUSED
        logger.info("Worker 已暂停")

    async def resume(self):
        """恢复 Worker"""
        if self.status == WorkerStatus.PAUSED:
            self.status = WorkerStatus.RUNNING
            logger.info("Worker 已恢复")

    async def _run_loop(self):
        """主循环"""
        while not self._stop_event.is_set():
            try:
                if self.status == WorkerStatus.RUNNING:
                    await self._process_next_task()

                # 等待一段时间再检查
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=5.0  # 每5秒检查一次
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker 循环出错: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒

    async def _process_next_task(self):
        """处理下一个任务"""
        db = SessionLocal()
        try:
            # 查找待写作的章节
            chapter = db.query(Chapter).filter(
                Chapter.status == ChapterStatus.PENDING
            ).order_by(Chapter.order_num.asc()).first()

            if not chapter:
                return

            # 获取项目配置
            project = db.query(Project).filter(
                Project.id == chapter.project_id
            ).first()

            if not project:
                logger.error(f"章节 {chapter.id} 所属项目不存在")
                return

            # 检查预算限制
            if not self._check_budget(project):
                logger.info("已达到每日预算限制，暂停写作")
                await self.pause()
                return

            # 设置当前任务
            self.current_task = {
                "chapter_id": chapter.id,
                "project_id": project.id,
                "chapter_title": chapter.title,
                "start_time": datetime.now().isoformat(),
            }

            logger.info(f"开始写作章节: {chapter.title}")

            # 执行写作流水线
            result = await self._run_writing_pipeline(db, chapter, project)

            # 更新统计
            if result["success"]:
                self.daily_stats["chapters_completed"] += 1
                self.daily_stats["words_written"] += result.get("word_count", 0)
                self.daily_stats["tokens_used"] += result.get("tokens_used", 0)

            self.current_task = None

        finally:
            db.close()

    async def _run_writing_pipeline(
        self,
        db: Session,
        chapter: Chapter,
        project: Project
    ) -> dict:
        """执行写作流水线"""
        try:
            # 更新章节状态为写作中
            chapter.status = ChapterStatus.WRITING
            db.commit()

            # 调用流水线服务
            result = await self.pipeline_service.run_pipeline(
                db=db,
                chapter_id=chapter.id,
                project_id=project.id
            )

            return result

        except Exception as e:
            logger.error(f"写作流水线执行失败: {e}")
            chapter.status = ChapterStatus.FAILED
            db.commit()
            return {
                "success": False,
                "error": str(e)
            }

    def _check_budget(self, project: Project) -> bool:
        """检查预算限制"""
        # 检查每日字数限制
        daily_word_goal = project.config.get("daily_word_goal", 10000)
        if self.daily_stats["words_written"] >= daily_word_goal:
            return False

        # 检查 Token 预算
        token_budget = project.config.get("daily_token_budget", 100000)
        if self.daily_stats["tokens_used"] >= token_budget:
            return False

        return True

    def get_status(self) -> dict:
        """获取 Worker 状态"""
        return {
            "status": self.status.value,
            "current_task": self.current_task,
            "daily_stats": self.daily_stats,
            "uptime": (
                (datetime.now() - self.daily_stats["start_time"]).total_seconds()
                if self.daily_stats["start_time"]
                else 0
            ),
        }

    def reset_daily_stats(self):
        """重置每日统计"""
        self.daily_stats = {
            "words_written": 0,
            "chapters_completed": 0,
            "tokens_used": 0,
            "start_time": datetime.now(),
        }


# 全局 Worker 实例
worker = WritingWorker()
