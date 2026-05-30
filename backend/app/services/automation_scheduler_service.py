"""AutomationSchedulerService - 项目级自动化调度 (P8)
按 AutomationPolicy 决定是否触发总编复盘 / 联网研究 / Prompt 进化 / 真人训练营批处理。
每个子任务失败不影响其它。
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.automation import AutomationPolicy
from app.models.chapter import Chapter, ChapterStatus
from app.models.feedback import Feedback
from app.services.reader_training_service import ReaderTrainingService
from app.services.event_bus import event_bus
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class AutomationSchedulerService:
    """自动化调度服务"""

    def __init__(self, db: Session):
        self.db = db
        self.reader_training_service = ReaderTrainingService(db)

    def _get_policy(self, project_id: int) -> Optional[AutomationPolicy]:
        return self.db.query(AutomationPolicy).filter(
            AutomationPolicy.project_id == project_id
        ).first()

    def _latest_completed_index(self, project_id: int) -> int:
        row = self.db.query(Chapter.chapter_index).filter(
            Chapter.project_id == project_id,
            Chapter.status == ChapterStatus.COMPLETED,
        ).order_by(Chapter.chapter_index.desc()).first()
        return row[0] if row and row[0] else 0

    async def scan_project_automations(self, project_id: int) -> dict:
        policy = self._get_policy(project_id)
        if not policy:
            return {"project_id": project_id, "skipped": "无自动化策略"}

        result = {"project_id": project_id}
        try:
            result["editor_review"] = await self.maybe_run_editor_review(project_id)
        except Exception as e:
            logger.warning(f"[Automation] 总编复盘失败: {e}")
            result["editor_review"] = {"error": str(e)}
        try:
            result["research"] = await self.maybe_run_research(project_id)
        except Exception as e:
            logger.warning(f"[Automation] 联网研究失败: {e}")
            result["research"] = {"error": str(e)}
        try:
            result["evolution"] = await self.maybe_run_evolution(project_id)
        except Exception as e:
            logger.warning(f"[Automation] Prompt 进化失败: {e}")
            result["evolution"] = {"error": str(e)}
        try:
            result["reader_training"] = await self.maybe_process_reader_training(
                project_id
            )
        except Exception as e:
            logger.warning(f"[Automation] 真人训练营批处理失败: {e}")
            result["reader_training"] = {"error": str(e)}
        return result

    async def maybe_run_editor_review(self, project_id: int) -> dict:
        policy = self._get_policy(project_id)
        if not policy or not policy.enable_editor_review:
            return {"triggered": False, "reason": "未启用"}

        latest = self._latest_completed_index(project_id)
        every = max(1, policy.editor_review_every_n_chapters)
        if latest < every or latest % every != 0:
            return {"triggered": False, "reason": f"未到复盘点（latest={latest}）"}
        if latest <= (policy.last_editor_review_chapter or 0):
            return {"triggered": False, "reason": "该区间已复盘"}

        from app.services.editor_review_service import EditorReviewService
        review = await EditorReviewService(self.db).review_recent_chapters(
            project_id=project_id, end_chapter_index=latest, window_size=every,
        )
        policy.last_editor_review_chapter = latest
        policy.updated_at = utc_now()
        self.db.commit()
        return {"triggered": True, "end_chapter": latest, "review": review}

    async def maybe_run_research(self, project_id: int) -> dict:
        policy = self._get_policy(project_id)
        if not policy or not policy.enable_research:
            return {"triggered": False, "reason": "未启用"}

        now = utc_now()
        if policy.last_research_at:
            elapsed_h = (now - policy.last_research_at).total_seconds() / 3600
            if elapsed_h < policy.research_interval_hours:
                return {"triggered": False, "reason": "未到研究间隔"}

        policy.last_research_at = now
        self.db.commit()
        return {"triggered": True, "scheduled_at": now.isoformat()}

    async def maybe_run_evolution(self, project_id: int) -> dict:
        policy = self._get_policy(project_id)
        if not policy or not policy.enable_evolution:
            return {"triggered": False, "reason": "未启用"}

        latest = self._latest_completed_index(project_id)
        every = max(1, policy.evolution_check_every_n_chapters)
        if latest < every or latest % every != 0:
            return {"triggered": False, "reason": f"未到进化检查点（latest={latest}）"}
        if latest <= (policy.last_evolution_chapter or 0):
            return {"triggered": False, "reason": "该区间已检查"}

        policy.last_evolution_chapter = latest
        self.db.commit()
        return {
            "triggered": True,
            "end_chapter": latest,
            "min_samples": policy.min_samples_for_evolution,
        }

    # ========== P5: 真人训练营异步批处理 ==========

    async def maybe_process_reader_training(self, project_id: int) -> dict:
        """按 AutomationPolicy 周期跑读取 feedback batch。"""
        policy = self._get_policy(project_id)
        if not policy or not policy.enable_reader_training:
            return {"triggered": False, "reason": "未启用"}

        # 节流：距离上次处理至少 interval_minutes
        now = utc_now()
        last_at = policy.last_reader_training_at
        if last_at is not None:
            elapsed_m = (now - last_at).total_seconds() / 60
            if elapsed_m < policy.reader_training_interval_minutes:
                return {
                    "triggered": False,
                    "reason": f"未到间隔（{elapsed_m:.0f}m/{policy.reader_training_interval_minutes}m）",
                }

        pending_count = (
            self.db.query(Feedback)
            .filter(
                Feedback.status == "queued",
                Feedback.source == "reader",
                Feedback.project_id == project_id,
            )
            .count()
        )
        if pending_count < policy.reader_training_min_batch:
            return {
                "triggered": False,
                "reason": f"待处理{pending_count} < min_batch{policy.reader_training_min_batch}",
            }

        result = await self.reader_training_service.process_pending_batch(
            project_id=project_id,
            min_batch=policy.reader_training_min_batch,
        )
        if result.get("status") == "processed":
            policy.last_reader_training_at = now
            policy.last_reader_training_batch_id = (
                result.get("batch_id", 0) or 0
            )
            self.db.commit()
        return result
