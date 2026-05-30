"""
ProductionLoopService - 常驻生产循环 (P8)
周期性扫描排产、按需启动 Worker、触发项目级自动化调度。
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from app.database import SessionLocal
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class ProductionLoopStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class ProductionLoopService:
    """常驻生产循环"""

    def __init__(self):
        self.status = ProductionLoopStatus.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.interval_seconds = 60
        self.last_scan_at = None
        self.last_scheduled_count = 0
        self.last_error = None

    async def start(self):
        if self.status == ProductionLoopStatus.RUNNING:
            return
        try:
            from app.config import settings
            self.interval_seconds = int(
                getattr(settings, "PRODUCTION_SCAN_INTERVAL_SECONDS", 60)
            )
        except Exception:
            self.interval_seconds = 60
        self._stop_event = asyncio.Event()
        self.status = ProductionLoopStatus.RUNNING
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"[ProductionLoop] 启动，间隔 {self.interval_seconds}s")

    async def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        self.status = ProductionLoopStatus.STOPPED
        logger.info("[ProductionLoop] 已停止")

    async def pause(self):
        if self.status == ProductionLoopStatus.RUNNING:
            self.status = ProductionLoopStatus.PAUSED

    async def resume(self):
        if self.status == ProductionLoopStatus.PAUSED:
            self.status = ProductionLoopStatus.RUNNING

    async def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.status == ProductionLoopStatus.RUNNING:
                    await self._tick()
            except Exception as e:
                self.last_error = str(e)
                logger.warning(f"[ProductionLoop] tick 异常: {e}")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self.interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    async def _tick(self):
        from app.services.production_scheduler import ProductionScheduler
        db = SessionLocal()
        try:
            scheduler = ProductionScheduler(db)
            results = scheduler.scan_and_schedule()
            self.last_scan_at = utc_now()
            self.last_scheduled_count = len(results or [])
            self.last_error = None

            # 项目级自动化调度
            project_ids = {r.get("project_id") for r in (results or []) if r.get("project_id")}
            if project_ids:
                from app.services.automation_scheduler_service import (
                    AutomationSchedulerService,
                )
                auto = AutomationSchedulerService(db)
                for pid in project_ids:
                    try:
                        await auto.scan_project_automations(pid)
                    except Exception as e:
                        logger.warning(f"[ProductionLoop] 项目 {pid} 自动化失败: {e}")
        finally:
            db.close()

    def get_status(self) -> dict:
        return {
            "status": self.status.value,
            "interval_seconds": self.interval_seconds,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "last_scheduled_count": self.last_scheduled_count,
            "last_error": self.last_error,
        }


# 单例
production_loop = ProductionLoopService()
