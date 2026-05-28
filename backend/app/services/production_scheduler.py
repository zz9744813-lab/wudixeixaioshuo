"""
Production Scheduler - 自动排产服务
P4 Phase 5: 24小时生产
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.production import ProductionPolicy, ProductionLog, ProductionStats
from app.models.project import Project
from app.models.chapter import Chapter, ChapterStatus
from app.models.task import GenerationTask, TaskStatus

logger = logging.getLogger(__name__)


class ProductionScheduler:
    """生产调度器"""

    def __init__(self, db: Session):
        self.db = db

    # ========== Policy Management ==========

    def create_policy(
        self,
        project_id: int,
        enabled: bool = False,
        target_daily_words: int = 10000,
        target_daily_chapters: int = 3,
        max_daily_cost: float = 5.0,
        max_daily_tokens: int = 500000,
        min_quality_score: float = 80.0,
        max_rewrite_rounds: int = 2,
        max_consecutive_failures: int = 3,
        auto_create_next_chapter: bool = True,
        auto_pause_on_failure: bool = True,
        auto_pause_on_budget: bool = True,
        active_hours: List[List[int]] = None,
        priority: int = 2
    ) -> ProductionPolicy:
        """创建生产策略"""
        # 检查是否已有策略
        existing = self.db.query(ProductionPolicy).filter(
            ProductionPolicy.project_id == project_id
        ).first()

        if existing:
            # 更新现有策略
            existing.enabled = 1 if enabled else 0
            existing.target_daily_words = target_daily_words
            existing.target_daily_chapters = target_daily_chapters
            existing.max_daily_cost = max_daily_cost
            existing.max_daily_tokens = max_daily_tokens
            existing.min_quality_score = min_quality_score
            existing.max_rewrite_rounds = max_rewrite_rounds
            existing.max_consecutive_failures = max_consecutive_failures
            existing.auto_create_next_chapter = 1 if auto_create_next_chapter else 0
            existing.auto_pause_on_failure = 1 if auto_pause_on_failure else 0
            existing.auto_pause_on_budget = 1 if auto_pause_on_budget else 0
            existing.active_hours = active_hours or []
            existing.priority = priority
            self.db.commit()
            self.db.refresh(existing)
            return existing

        policy = ProductionPolicy(
            project_id=project_id,
            enabled=1 if enabled else 0,
            target_daily_words=target_daily_words,
            target_daily_chapters=target_daily_chapters,
            max_daily_cost=max_daily_cost,
            max_daily_tokens=max_daily_tokens,
            min_quality_score=min_quality_score,
            max_rewrite_rounds=max_rewrite_rounds,
            max_consecutive_failures=max_consecutive_failures,
            auto_create_next_chapter=1 if auto_create_next_chapter else 0,
            auto_pause_on_failure=1 if auto_pause_on_failure else 0,
            auto_pause_on_budget=1 if auto_pause_on_budget else 0,
            active_hours=active_hours or [],
            priority=priority
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        logger.info(f"[Production] 创建生产策略: project={project_id}")
        return policy

    def get_policy(self, project_id: int) -> Optional[ProductionPolicy]:
        """获取项目生产策略"""
        return self.db.query(ProductionPolicy).filter(
            ProductionPolicy.project_id == project_id
        ).first()

    def toggle_production(self, project_id: int, enabled: bool) -> Optional[ProductionPolicy]:
        """开关自动生产"""
        policy = self.get_policy(project_id)
        if not policy:
            return None

        policy.enabled = 1 if enabled else 0
        self.db.commit()

        self._log_event(project_id, "resumed" if enabled else "paused", message=f"自动生产{'开启' if enabled else '暂停'}")
        return policy

    # ========== Scheduler Core ==========

    def scan_and_schedule(self) -> List[Dict[str, Any]]:
        """
        扫描并调度生产任务

        每1-5分钟运行一次
        """
        results = []

        # 1. 获取所有启用的生产策略
        policies = self.db.query(ProductionPolicy).filter(
            ProductionPolicy.enabled == 1
        ).order_by(desc(ProductionPolicy.priority)).all()

        for policy in policies:
            try:
                result = self._process_project(policy)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"[Production] 调度项目 {policy.project_id} 失败: {e}")
                continue

        return results

    def _process_project(self, policy: ProductionPolicy) -> Optional[Dict[str, Any]]:
        """处理单个项目的生产调度"""
        project_id = policy.project_id

        # 2. 检查今日统计
        today_stats = self._get_or_create_today_stats(project_id)

        # 3. 检查预算限制
        if self._check_budget_exceeded(policy, today_stats):
            if policy.auto_pause_on_budget:
                self.toggle_production(project_id, False)
                self._log_event(project_id, "paused", message="预算超限，自动暂停")
            return None

        # 4. 检查今日目标
        if today_stats.chapters_completed >= policy.target_daily_chapters:
            return None

        if today_stats.words_written >= policy.target_daily_words:
            return None

        # 5. 检查是否有pending/running任务
        has_pending = self.db.query(GenerationTask).filter(
            GenerationTask.project_id == project_id,
            GenerationTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
        ).first()

        if has_pending:
            return None

        # 6. 检查连续失败
        recent_failures = self._count_recent_failures(project_id)
        if recent_failures >= policy.max_consecutive_failures:
            if policy.auto_pause_on_failure:
                self.toggle_production(project_id, False)
                self._log_event(project_id, "paused", message=f"连续失败{recent_failures}次，自动暂停")
            return None

        # 7. 自动创建下一章
        if policy.auto_create_next_chapter:
            result = self._create_next_chapter(project_id)
            return result

        return None

    def _create_next_chapter(self, project_id: int) -> Optional[Dict[str, Any]]:
        """创建下一章"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        # 检查最后一章是否已完成
        last_chapter = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        ).order_by(desc(Chapter.chapter_index)).first()

        if last_chapter and last_chapter.status != ChapterStatus.COMPLETED:
            # 最后一章未完成，不创建新章
            return None

        # 检查必要条件
        if not self._check_prerequisites(project_id):
            return None

        # 创建新章节
        next_index = (last_chapter.chapter_index + 1) if last_chapter else 1

        chapter = Chapter(
            project_id=project_id,
            title=f"第{next_index}章",
            chapter_index=next_index,
            status=ChapterStatus.PENDING
        )
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)

        # 创建生成任务
        task = GenerationTask(
            project_id=project_id,
            chapter_id=chapter.id,
            task_type="chapter",
            status=TaskStatus.PENDING
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        self._log_event(
            project_id,
            "auto_created",
            chapter_id=chapter.id,
            task_id=task.id,
            message=f"自动创建第{next_index}章"
        )

        logger.info(f"[Production] 自动创建章节: project={project_id}, chapter={next_index}")

        return {
            "project_id": project_id,
            "chapter_id": chapter.id,
            "chapter_index": next_index,
            "task_id": task.id,
            "action": "auto_created"
        }

    def _check_prerequisites(self, project_id: int) -> bool:
        """检查创建下一章的必要条件"""
        # 检查Bible
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.bible:
            return False

        # 检查上一章是否处理完毕
        last_chapter = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        ).order_by(desc(Chapter.chapter_index)).first()

        if last_chapter:
            # 检查是否有记忆更新
            # (这里简化处理，实际应该检查MemoryUpdate)
            if not last_chapter.final_content:
                return False

        return True

    def _check_budget_exceeded(self, policy: ProductionPolicy, stats: ProductionStats) -> bool:
        """检查是否超出预算"""
        if stats.total_cost >= policy.max_daily_cost:
            return True
        if stats.tokens_used >= policy.max_daily_tokens:
            return True
        return False

    def _count_recent_failures(self, project_id: int, window: int = 5) -> int:
        """统计最近失败数"""
        recent_chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        ).order_by(desc(Chapter.chapter_index)).limit(window).all()

        failures = sum(1 for c in recent_chapters if c.status == ChapterStatus.FAILED)
        return failures

    # ========== Stats Management ==========

    def _get_or_create_today_stats(self, project_id: int) -> ProductionStats:
        """获取或创建今日统计"""
        today = date.today().isoformat()

        stats = self.db.query(ProductionStats).filter(
            ProductionStats.project_id == project_id,
            ProductionStats.date == today
        ).first()

        if not stats:
            stats = ProductionStats(
                project_id=project_id,
                date=today
            )
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)

        return stats

    def update_stats_from_chapter(
        self,
        project_id: int,
        chapter_id: int,
        word_count: int,
        tokens_used: int,
        cost: float,
        score: float,
        is_rewrite: bool = False,
        is_failure: bool = False
    ):
        """从章节完成更新统计"""
        stats = self._get_or_create_today_stats(project_id)

        stats.chapters_completed += 1
        stats.words_written += word_count
        stats.tokens_used += tokens_used
        stats.total_cost += cost

        if is_rewrite:
            stats.rewrite_count += 1
        if is_failure:
            stats.failure_count += 1

        # 更新平均分
        if stats.chapters_completed > 0:
            old_avg = stats.avg_score
            n = stats.chapters_completed
            stats.avg_score = (old_avg * (n - 1) + score) / n

        # 计算目标达成率
        policy = self.get_policy(project_id)
        if policy:
            stats.word_goal_achievement = min(stats.words_written / policy.target_daily_words, 1.0)
            stats.chapter_goal_achievement = min(stats.chapters_completed / policy.target_daily_chapters, 1.0)

        self.db.commit()

    # ========== Logging ==========

    def _log_event(
        self,
        project_id: int,
        log_type: str,
        chapter_id: int = None,
        task_id: int = None,
        message: str = "",
        details: Dict = None
    ):
        """记录生产日志"""
        log = ProductionLog(
            project_id=project_id,
            log_type=log_type,
            chapter_id=chapter_id,
            task_id=task_id,
            message=message,
            details=details or {}
        )
        self.db.add(log)
        self.db.commit()

    # ========== Stats Queries ==========

    def get_project_stats(self, project_id: int, days: int = 7) -> Dict[str, Any]:
        """获取项目生产统计"""
        # 今日统计
        today = date.today().isoformat()
        today_stats = self._get_or_create_today_stats(project_id)

        # 最近N天
        start_date = (date.today() - timedelta(days=days)).isoformat()
        recent_stats = self.db.query(ProductionStats).filter(
            ProductionStats.project_id == project_id,
            ProductionStats.date >= start_date
        ).order_by(ProductionStats.date.desc()).all()

        # 累计统计
        total_chapters = sum(s.chapters_completed for s in recent_stats)
        total_words = sum(s.words_written for s in recent_stats)
        total_cost = sum(s.total_cost for s in recent_stats)

        return {
            "today": {
                "chapters_completed": today_stats.chapters_completed,
                "words_written": today_stats.words_written,
                "tokens_used": today_stats.tokens_used,
                "total_cost": round(today_stats.total_cost, 2),
                "avg_score": round(today_stats.avg_score, 1),
                "word_goal_achievement": round(today_stats.word_goal_achievement * 100, 1),
                "chapter_goal_achievement": round(today_stats.chapter_goal_achievement * 100, 1)
            },
            "recent_days": days,
            "recent_total": {
                "chapters": total_chapters,
                "words": total_words,
                "cost": round(total_cost, 2)
            },
            "daily_history": [{
                "date": s.date,
                "chapters": s.chapters_completed,
                "words": s.words_written,
                "avg_score": round(s.avg_score, 1)
            } for s in recent_stats]
        }

    def get_queue_status(self) -> Dict[str, Any]:
        """获取生产队列状态"""
        # 活跃项目
        active_policies = self.db.query(ProductionPolicy).filter(
            ProductionPolicy.enabled == 1
        ).all()

        # 待处理任务
        pending_tasks = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.PENDING
        ).count()

        running_tasks = self.db.query(GenerationTask).filter(
            GenerationTask.status == TaskStatus.RUNNING
        ).count()

        return {
            "active_projects": len(active_policies),
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "projects": [{
                "project_id": p.project_id,
                "priority": p.priority,
                "target_daily_chapters": p.target_daily_chapters
            } for p in active_policies]
        }

    def get_recent_logs(self, project_id: int, limit: int = 20) -> List[Dict]:
        """获取最近生产日志"""
        logs = self.db.query(ProductionLog).filter(
            ProductionLog.project_id == project_id
        ).order_by(desc(ProductionLog.created_at)).limit(limit).all()

        return [{
            "id": log.id,
            "type": log.log_type,
            "message": log.message,
            "chapter_id": log.chapter_id,
            "created_at": log.created_at.isoformat() if log.created_at else None
        } for log in logs]
