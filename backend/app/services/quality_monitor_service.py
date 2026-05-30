"""Quality Monitor Service - 质量监控与触发条件。"""

import json
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.evolution_auto import PromptEvolutionPolicy
from app.models.feedback import Feedback
from app.models.review import ReviewResult
from app.utils.time_utils import utc_now


class QualityMonitorService:
    """监控质量指标，判断是否需要触发 Prompt 进化。"""

    def __init__(self, db: Session):
        self.db = db

    def should_trigger_evolution(self, policy: PromptEvolutionPolicy) -> bool:
        """检查该角色是否满足进化触发条件。"""
        if not policy.enabled:
            return False

        window_start = utc_now() - timedelta(days=policy.trigger_window_days)

        # 条件1：平均分低于阈值
        avg_score = self._get_average_score(policy.role, window_start)
        if avg_score is not None and avg_score < policy.min_average_score:
            return True

        # 条件2：重写率过高
        rewrite_rate = self._get_rewrite_rate(policy.role, window_start)
        if rewrite_rate > policy.max_rewrite_rate:
            return True

        # 条件3：用户连续退回
        reject_rate = self._get_user_reject_rate(policy.role, window_start)
        if reject_rate > 0.3:
            return True

        return False

    def collect_failure_samples(self, role: str, window_days: int = 7) -> List[Dict[str, Any]]:
        """收集该角色的失败/低分样本。"""
        window_start = utc_now() - timedelta(days=window_days)

        samples = []
        reviews = (
            self.db.query(ReviewResult)
            .filter(
                ReviewResult.reviewer_role == role,
                ReviewResult.created_at >= window_start,
            )
            .order_by(ReviewResult.created_at.desc())
            .limit(50)
            .all()
        )

        for review in reviews:
            score = review.total_score or 0
            if score < 80:
                samples.append({
                    "id": review.id,
                    "chapter_id": review.chapter_id,
                    "score": score,
                    "details": review.score_breakdown,
                    "created_at": review.created_at.isoformat() if review.created_at else None,
                })

        return samples

    def diagnose(self, role: str, samples: List[Dict[str, Any]]) -> str:
        """用 LLM 总结失败共性（本地兜底版本）。"""
        if not samples:
            return f"{role} 角色暂无低分样本。"

        scores = [s.get("score", 0) for s in samples]
        avg = sum(scores) / len(scores) if scores else 0

        diagnoses = []
        if avg < 60:
            diagnoses.append("整体质量严重不足")
        elif avg < 70:
            diagnoses.append("质量偏低")
        elif avg < 80:
            diagnoses.append("质量有提升空间")

        diagnoses.append(f"共 {len(samples)} 个低分样本，平均分 {avg:.1f}")
        diagnoses.append("建议：优化 Prompt 指令、调整评分维度权重、增加样例参考")

        return "；".join(diagnoses)

    def get_quality_metrics(self, role: Optional[str] = None) -> Dict[str, Any]:
        """获取质量指标概览。"""
        window = utc_now() - timedelta(days=7)
        query = self.db.query(ReviewResult)
        if role:
            query = query.filter(ReviewResult.reviewer_role == role)

        reviews = query.filter(ReviewResult.created_at >= window).all()
        scores = [r.total_score or 0 for r in reviews]

        return {
            "role": role or "all",
            "window_days": 7,
            "total_reviews": len(reviews),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "below_80_count": len([s for s in scores if s < 80]),
            "below_60_count": len([s for s in scores if s < 60]),
        }

    def _get_average_score(self, role: str, since) -> Optional[float]:
        """获取指定角色的平均分。"""
        result = (
            self.db.query(func.avg(ReviewResult.total_score))
            .filter(ReviewResult.reviewer_role == role, ReviewResult.created_at >= since)
            .scalar()
        )
        return float(result) if result else None

    def _get_rewrite_rate(self, role: str, since) -> float:
        """获取重写率。"""
        from app.models.chapter import Chapter, ChapterStatus

        total = (
            self.db.query(Chapter)
            .join(ReviewResult, ReviewResult.chapter_id == Chapter.id)
            .filter(ReviewResult.reviewer_role == role, ReviewResult.created_at >= since)
            .count()
        )
        if total == 0:
            return 0.0

        rewritten = (
            self.db.query(Chapter)
            .join(ReviewResult, ReviewResult.chapter_id == Chapter.id)
            .filter(
                ReviewResult.reviewer_role == role,
                ReviewResult.created_at >= since,
                Chapter.status == ChapterStatus.REWRITING,
            )
            .count()
        )
        return rewritten / total

    def _get_user_reject_rate(self, role: str, since) -> float:
        """获取用户手动退回率。"""
        total = (
            self.db.query(Feedback)
            .filter(Feedback.created_at >= since)
            .count()
        )
        if total == 0:
            return 0.0

        rejected = (
            self.db.query(Feedback)
            .filter(
                Feedback.created_at >= since,
                Feedback.rating <= 2,
            )
            .count()
        )
        return rejected / total
