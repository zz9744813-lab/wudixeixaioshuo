"""
Task Service - 任务系统核心服务
支持：任务领取、锁、心跳、僵尸恢复、重试退避
核心优化：使用单条 UPDATE ... RETURNING 实现真正原子 claim
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.models.task import GenerationTask, TaskStatus
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

# 配置
ZOMBIE_TIMEOUT_MINUTES = 10  # 僵尸任务超时时间
MAX_CLAIM_ATTEMPTS = 3  # 最大领取尝试次数


class TaskService:
    """任务服务 - 负责任务系统的核心操作"""

    def __init__(self, db: Session, worker_id: Optional[str] = None):
        self.db = db
        self.worker_id = worker_id or self._generate_worker_id()

    def _generate_worker_id(self) -> str:
        """生成唯一的 Worker ID"""
        return f"worker-{uuid.uuid4().hex[:8]}"

    # ========== P2-2: 真原子任务 Claim ==========

    def claim_task(self) -> Optional[GenerationTask]:
        """
        真正原子领取任务 - 使用单条 UPDATE ... RETURNING

        只领取满足以下条件的任务：
        - status = PENDING
        - next_run_at <= now
        - attempts < max_attempts

        领取时原子性设置：
        - status = RUNNING
        - locked_by = 当前 worker_id
        - locked_at = now
        - heartbeat_at = now
        - attempts += 1
        - started_at = now

        Returns:
            领取到的任务，如果没有可领取任务则返回 None
        """
        now = utc_now()

        try:
            # 使用单条 UPDATE ... RETURNING 实现真正的原子 claim
            # 这是 SQLite 3.35+ 支持的语法
            result = self.db.execute(text("""
                UPDATE generation_tasks
                SET
                    status = :running_status,
                    locked_by = :worker_id,
                    locked_at = :now,
                    heartbeat_at = :now,
                    attempts = attempts + 1,
                    started_at = :now
                WHERE id = (
                    SELECT id FROM generation_tasks
                    WHERE status = :pending_status
                        AND next_run_at <= :now
                        AND attempts < max_attempts
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                )
                AND status = :pending_status
                RETURNING id
            """), {
                "running_status": TaskStatus.RUNNING.value,
                "pending_status": TaskStatus.PENDING.value,
                "worker_id": self.worker_id,
                "now": now.isoformat(),
            })

            # 获取返回的任务 ID
            row = result.fetchone()
            if not row:
                return None

            task_id = row[0]

            # 提交事务
            self.db.commit()

            # 重新查询完整的任务对象
            task = self.db.query(GenerationTask).filter(
                GenerationTask.id == task_id
            ).first()

            if task:
                logger.info(f"[TaskService] Worker {self.worker_id} 领取任务 {task.id} (第{task.attempts}次尝试)")

            return task

        except Exception as e:
            self.db.rollback()
            logger.error(f"[TaskService] 领取任务失败: {e}")
            return None

    def claim_task_safe(self) -> Optional[GenerationTask]:
        """安全领取任务（带重试）"""
        for attempt in range(MAX_CLAIM_ATTEMPTS):
            task = self.claim_task()
            if task:
                return task
        return None

    # ========== P2-2: 心跳更新 ==========

    def update_heartbeat(self, task_id: int) -> bool:
        """更新任务心跳时间"""
        try:
            task = self.db.query(GenerationTask).filter(
                GenerationTask.id == task_id,
                GenerationTask.locked_by == self.worker_id
            ).first()

            if not task:
                logger.warning(f"[TaskService] 无法更新心跳: 任务 {task_id} 不存在或不由当前Worker持有")
                return False

            task.heartbeat_at = utc_now()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[TaskService] 更新心跳失败: {e}")
            return False

    # ========== P2-2: 僵尸任务恢复 ==========

    def recover_zombie_tasks(self) -> int:
        """
        恢复僵尸任务

        把 heartbeat_at 超过阈值仍为 RUNNING 的任务重置为 PENDING：
        - RUNNING + heartbeat_at < now - 10min → PENDING

        Returns:
            恢复的任务数量
        """
        now = utc_now()
        threshold = now - timedelta(minutes=ZOMBIE_TIMEOUT_MINUTES)

        try:
            # 查询僵尸任务
            zombie_tasks = self.db.query(GenerationTask).filter(
                and_(
                    GenerationTask.status == TaskStatus.RUNNING,
                    or_(
                        GenerationTask.heartbeat_at < threshold,
                        GenerationTask.heartbeat_at == None  # noqa: E711
                    )
                )
            ).all()

            recovered_count = 0
            for task in zombie_tasks:
                logger.warning(
                    f"[TaskService] 发现僵尸任务 {task.id} "
                    f"(Worker: {task.locked_by}, 心跳: {task.heartbeat_at})"
                )

                # 增加尝试次数（因为任务已经claim过）
                task.attempts += 1

                # 判断是否超过最大尝试次数
                if task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"任务超时，Worker {task.locked_by} 失去响应"
                    task.finished_at = now
                else:
                    # 重置为 PENDING
                    task.status = TaskStatus.PENDING
                    task.locked_by = None
                    task.locked_at = None
                    task.heartbeat_at = None

                recovered_count += 1

            self.db.commit()

            if recovered_count > 0:
                logger.info(f"[TaskService] 恢复了 {recovered_count} 个僵尸任务")

            return recovered_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"[TaskService] 恢复僵尸任务失败: {e}")
            return 0

    # ========== P2-3: 失败重试与退避 ==========

    def handle_task_failure(
        self,
        task_id: int,
        error_message: str,
        is_retryable: bool = True
    ) -> bool:
        """
        处理任务失败

        - 增加 attempts 计数
        - 如果可重试且 attempts < max_attempts：
          - status = PENDING
          - next_run_at = now + backoff
          - error_message = last_error
        - 否则：
          - status = FAILED
          - finished_at = now

        Args:
            task_id: 任务ID
            error_message: 错误信息
            is_retryable: 是否可重试（API Key错误不可重试，网络超时等可重试）

        Returns:
            True: 任务已重试，False: 任务标记为失败
        """
        now = utc_now()

        try:
            task = self.db.query(GenerationTask).filter(
                GenerationTask.id == task_id
            ).first()

            if not task:
                logger.error(f"[TaskService] 任务 {task_id} 不存在")
                return False

            task.error_message = error_message
            # 注意：attempts 只在 claim_task 时 +1（代表"已启动次数"）。
            # 这里不再重复 +1，否则一次真实失败会消耗两次配额。

            # 判断是否可以重试（claim 时已把本次计入 attempts）
            if is_retryable and task.attempts < task.max_attempts:
                # 计算退避时间
                backoff_seconds = self._calculate_backoff(task.attempts)
                task.next_run_at = now + timedelta(seconds=backoff_seconds)
                task.status = TaskStatus.PENDING
                task.locked_by = None
                task.locked_at = None
                task.heartbeat_at = None

                self.db.commit()
                logger.info(
                    f"[TaskService] 任务 {task_id} 将在 {backoff_seconds}s 后重试 "
                    f"(第{task.attempts}/{task.max_attempts}次)"
                )
                return True
            else:
                # 不可重试或超过最大尝试次数
                task.status = TaskStatus.FAILED
                task.finished_at = now
                task.locked_by = None
                task.locked_at = None
                task.heartbeat_at = None

                self.db.commit()
                logger.info(f"[TaskService] 任务 {task_id} 标记为失败: {error_message}")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"[TaskService] 处理任务失败出错: {e}")
            return False

    def _calculate_backoff(self, attempts: int) -> int:
        """
        计算指数退避时间

        delay_seconds = min(300, 2 ** attempts * 10)
        """
        delay = min(300, (2 ** attempts) * 10)
        return delay

    def handle_task_success(self, task_id: int) -> bool:
        """
        处理任务成功

        - status = COMPLETED
        - finished_at = now
        - 释放锁
        """
        now = utc_now()

        try:
            task = self.db.query(GenerationTask).filter(
                GenerationTask.id == task_id
            ).first()

            if not task:
                logger.error(f"[TaskService] 任务 {task_id} 不存在")
                return False

            task.status = TaskStatus.COMPLETED
            task.finished_at = now
            task.locked_by = None
            task.locked_at = None
            task.heartbeat_at = None
            task.error_message = None

            self.db.commit()
            logger.info(f"[TaskService] 任务 {task_id} 完成")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[TaskService] 处理任务成功出错: {e}")
            return False

    # ========== 查询方法 ==========

    def get_task_by_id(self, task_id: int) -> Optional[GenerationTask]:
        """获取任务详情"""
        return self.db.query(GenerationTask).filter(
            GenerationTask.id == task_id
        ).first()

    def get_pending_tasks(self, limit: int = 100) -> List[GenerationTask]:
        """获取待处理任务列表"""
        return self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PENDING
        ).order_by(
            GenerationTask.priority.desc(),
            GenerationTask.created_at.asc()
        ).limit(limit).all()

    def get_running_tasks(self, limit: int = 100) -> List[GenerationTask]:
        """获取运行中任务列表"""
        return self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.RUNNING
        ).limit(limit).all()

    def get_failed_tasks(self, limit: int = 100) -> List[GenerationTask]:
        """获取失败任务列表"""
        return self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.FAILED
        ).order_by(
            GenerationTask.finished_at.desc()
        ).limit(limit).all()

    def get_tasks_by_project(
        self,
        project_id: int,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[GenerationTask]:
        """获取项目的任务列表"""
        query = self.db.query(GenerationTask).filter(
            GenerationTask.project_id == project_id
        )

        if status:
            query = query.filter(GenerationTask.status == status)

        return query.order_by(
            GenerationTask.created_at.desc()
        ).limit(limit).all()

    # ========== Worker 启动时调用 ==========

    @staticmethod
    def recover_zombies_on_startup(db: Session) -> int:
        """
        Worker 启动时恢复僵尸任务

        静态方法，用于在 Worker 启动时调用
        """
        service = TaskService(db)
        return service.recover_zombie_tasks()
