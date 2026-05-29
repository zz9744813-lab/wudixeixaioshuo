"""
Worker Service - 24小时自动写作后台任务调度器 (WORKER-002 重构版)
基于 GenerationTask 的调度，支持 Darwin 进化
重构: 抽离 PipelineService，移除 self.daily_stats，使用短事务架构
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.models.task import GenerationTask, TaskStatus
from app.services.task_service import TaskService
from app.services.openai_llm_service import llm_manager
from app.services.pipeline_service import PipelineService
from app.services.daily_usage_stats_service import DailyUsageStatsService
from app.services.event_bus import event_bus
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Worker 状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 暂停
    STOPPED = "stopped"     # 停止


class WritingWorker:
    """
    24小时自动写作 Worker (WORKER-002 重构版)

    职责：
    - 任务生命周期管理（领取、心跳、完成/失败处理）
    - 调用 PipelineService 执行写作流水线
    - 预算检查和每日统计（通过 DailyUsageStatsService）

    设计原则：
    1. 无长会话：每个操作使用独立数据库 session
    2. 无内存状态：统计通过 DailyUsageStatsService 持久化
    3. 单一职责：只负责任务调度，流水线执行交给 PipelineService
    """

    def __init__(self):
        self.status = WorkerStatus.STOPPED
        self.current_task: Optional[dict] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.task_service: Optional[TaskService] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        # WORKER-002: PipelineService 实例
        self.pipeline_service = PipelineService()

    async def start(self):
        """启动 Worker"""
        if self.status == WorkerStatus.RUNNING:
            logger.info("Worker 已在运行中")
            return

        self.status = WorkerStatus.RUNNING
        self._stop_event.clear()

        # 恢复僵尸任务
        self._recover_zombies_on_startup()

        self._task = asyncio.create_task(self._run_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("Worker 已启动")
        await event_bus.publish("worker.status", {
            "status": "running",
            "message": "Worker 已启动"
        })

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
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        self.current_task = None
        logger.info("Worker 已停止")

    async def pause(self):
        """暂停 Worker"""
        if self.status == WorkerStatus.RUNNING:
            self.status = WorkerStatus.PAUSED
            logger.info("Worker 已暂停")
            await event_bus.publish("worker.status", {
                "status": "paused",
                "message": "Worker 已暂停"
            })

    async def resume(self):
        """恢复 Worker"""
        if self.status == WorkerStatus.PAUSED:
            self.status = WorkerStatus.RUNNING
            logger.info("Worker 已恢复")

    def _recover_zombies_on_startup(self):
        """Worker 启动时恢复僵尸任务"""
        db = SessionLocal()
        try:
            recovered = TaskService.recover_zombies_on_startup(db)
            if recovered > 0:
                logger.info(f"Worker 启动时恢复了 {recovered} 个僵尸任务")
        finally:
            db.close()

    async def _heartbeat_loop(self):
        """心跳循环 - 每30秒更新一次"""
        while not self._stop_event.is_set():
            try:
                if self.current_task and self.task_service:
                    task_id = self.current_task.get("task_id")
                    if task_id:
                        self.task_service.update_heartbeat(task_id)
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"心跳更新失败: {e}")

    async def _run_loop(self):
        """主循环 - 使用 TaskService 领取任务"""
        while not self._stop_event.is_set():
            try:
                if self.status == WorkerStatus.RUNNING:
                    await self._process_next_task()

                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker 循环出错: {e}")
                await asyncio.sleep(10)

    async def _process_next_task(self):
        """处理下一个任务"""
        db = SessionLocal()
        self.task_service = TaskService(db)

        try:
            # 原子领取任务
            gen_task = self.task_service.claim_task_safe()

            if not gen_task:
                return

            # 有任务才初始化 LLM
            await llm_manager.init_from_db(db)

            # 获取关联的章节和项目
            chapter = db.query(Chapter).filter(
                Chapter.id == gen_task.chapter_id
            ).first()

            project = db.query(Project).filter(
                Project.id == gen_task.project_id
            ).first()

            if not chapter or not project:
                logger.error(f"任务 {gen_task.id} 关联的章节或项目不存在")
                self.task_service.handle_task_failure(
                    gen_task.id,
                    "关联的章节或项目不存在",
                    is_retryable=False
                )
                return

            # 检查预算限制
            if not self._check_budget(db, project):
                logger.info("已达到每日预算限制，暂停写作")
                await self.pause()
                return

            # 设置当前任务
            self.current_task = {
                "task_id": gen_task.id,
                "chapter_id": chapter.id,
                "project_id": project.id,
                "chapter_title": chapter.title,
                "task_type": gen_task.task_type,
                "start_time": datetime.now().isoformat(),
            }

            logger.info(f"开始处理任务 {gen_task.id}: {chapter.title} "
                       f"(Worker: {self.task_service.worker_id})")

            # 发布任务开始事件
            await event_bus.publish("task.started", {
                "task_id": gen_task.id,
                "chapter_id": chapter.id,
                "chapter_index": chapter.chapter_index,
                "chapter_title": chapter.title,
            })

            # WORKER-002: 调用 PipelineService 执行流水线
            result = await self.pipeline_service.run(gen_task.id)

            # 处理任务结果
            if result["success"]:
                self.task_service.handle_task_success(gen_task.id)
                await event_bus.publish("task.completed", {
                    "task_id": gen_task.id,
                    "chapter_id": chapter.id,
                    "word_count": result.get("word_count", 0),
                    "final_score": result.get("final_score", 0),
                })
            else:
                is_retryable = self._is_error_retryable(result.get("error", ""))
                self.task_service.handle_task_failure(
                    gen_task.id,
                    result.get("error", "未知错误"),
                    is_retryable=is_retryable
                )
                await event_bus.publish("task.failed", {
                    "task_id": gen_task.id,
                    "error": result.get("error", "未知错误"),
                    "retryable": is_retryable,
                })

            self.current_task = None

        finally:
            db.close()
            self.task_service = None

    def _is_error_retryable(self, error: str) -> bool:
        """判断错误是否可重试"""
        non_retryable_patterns = [
            "API key",
            "认证失败",
            "权限不足",
            "不存在",
            "配置错误",
        ]

        error_lower = error.lower()
        for pattern in non_retryable_patterns:
            if pattern.lower() in error_lower:
                return False

        return True

    def _check_budget(self, db: Session, project: Project) -> bool:
        """
        检查预算限制 - 使用 DailyUsageStatsService
        """
        if DailyUsageStatsService.should_stop_for_budget(db, project.id):
            budget_info = DailyUsageStatsService(db).check_budget(project.id)
            logger.warning(
                f"项目 {project.id} 预算已超支: "
                f"当前 ${budget_info.get('current_cost', 0)} / "
                f"上限 ${budget_info.get('daily_budget', 0)}"
            )
            return False

        daily_word_goal = project.daily_word_goal or 10000
        today_stats = DailyUsageStatsService(db).get_today_stats(project_id=project.id)
        if today_stats.get("word_count", 0) >= daily_word_goal:
            logger.info(f"项目 {project.id} 已达到每日字数目标: {daily_word_goal}")
            return False

        return True

    def get_status(self) -> dict:
        """获取 Worker 状态"""
        # WORKER-002: 从 DailyUsageStatsService 获取今日统计
        db = SessionLocal()
        try:
            stats_service = DailyUsageStatsService(db)
            today_stats = stats_service.get_today_stats()
            return {
                "status": self.status.value,
                "current_task": self.current_task,
                "today_stats": today_stats,
            }
        finally:
            db.close()


# 全局 Worker 实例
worker = WritingWorker()
