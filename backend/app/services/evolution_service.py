"""
Evolution Service - Darwin 进化引擎（修复版）
使用 EvolutionRun / EvolutionLog / VersionHistory
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterVersion
from app.models.evolution import EvolutionDecision, EvolutionRun, EvolutionTarget, VersionHistory
from app.models.feedback import Feedback
from app.models.project import Project
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class EvolutionStatus(str, Enum):
    """进化状态"""
    EVALUATING = "evaluating"
    TESTING = "testing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class EvolutionStrategy(str, Enum):
    """进化策略"""
    AUTO = "auto"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    TARGETED = "targeted"


class EvolutionService:
    """
    Darwin 进化服务 - 修复版
    使用实际存在的模型：EvolutionRun, EvolutionLog, VersionHistory
    """

    def __init__(self, db: Session = None):
        self.db = db

    def create_evolution_round(
        self,
        project_id: int,
        target_dimension: str,
        strategy: EvolutionStrategy = EvolutionStrategy.AUTO,
        prompt_type: str = "writing"
    ) -> EvolutionRun:
        """创建新的进化轮次"""
        evolution = EvolutionRun(
            project_id=project_id,
            target_type=EvolutionTarget.PROMPT,  # 使用枚举
            target_name=f"{prompt_type}_{target_dimension}",
            decision=EvolutionDecision.PENDING,
            before_version="",
            after_version="",
            before_score=0.0,
            after_score=0.0,
            improvement=0.0,
            test_sample_count=0,
            judge_agents=[],
            reason=f"策略: {strategy.value}, 目标维度: {target_dimension}"
        )

        self.db.add(evolution)
        self.db.commit()
        self.db.refresh(evolution)

        logger.info(f"进化轮次已创建: {evolution.id}")
        return evolution

    def collect_feedback_for_evolution(
        self,
        evolution_id: int,
        min_feedback_count: int = 5
    ) -> List[Feedback]:
        """收集相关反馈用于进化分析"""
        evolution = self.db.query(EvolutionRun).filter(
            EvolutionRun.id == evolution_id
        ).first()

        if not evolution:
            return []

        # 获取项目的未解决反馈
        feedbacks = self.db.query(Feedback).filter(
            Feedback.project_id == evolution.project_id
        ).order_by(Feedback.created_at.desc()).all()

        return feedbacks[:min_feedback_count]

    def run_ab_test(
        self,
        evolution_id: int,
        old_version_id: int,
        new_version_id: int,
        test_chapter_id: int
    ) -> dict:
        """运行 A/B 测试 - 对比新旧版本"""
        # 获取版本
        old_version = self.db.query(VersionHistory).filter(
            VersionHistory.id == old_version_id
        ).first()

        new_version = self.db.query(VersionHistory).filter(
            VersionHistory.id == new_version_id
        ).first()

        if not old_version or not new_version:
            return {"error": "版本不存在"}

        # 获取章节评分 - 从 ChapterVersion 获取
        from app.models.chapter import ChapterVersion
        chapter_version = self.db.query(ChapterVersion).filter(
            ChapterVersion.chapter_id == test_chapter_id
        ).order_by(ChapterVersion.version_number.desc()).first()

        # 计算改进率 - 使用 VersionHistory.score
        old_score = old_version.score or 0
        new_score = new_version.score or 0

        improvement = 0.0
        if old_score > 0:
            improvement = (new_score - old_score) / old_score * 100

        # 更新进化记录
        evolution = self.db.query(EvolutionRun).filter(
            EvolutionRun.id == evolution_id
        ).first()

        if evolution:
            evolution.before_score = old_score
            evolution.after_score = new_score
            evolution.improvement = round(improvement, 2)
            evolution.test_sample_count = 1
            evolution.before_version_id = old_version_id
            evolution.after_version_id = new_version_id
            self.db.commit()

        # 判断是否通过（改进率 > 5%）
        passed = improvement > 5

        return {
            "evolution_id": evolution_id,
            "old_version_id": old_version_id,
            "new_version_id": new_version_id,
            "old_score": old_score,
            "new_score": new_score,
            "improvement_rate": round(improvement, 2),
            "passed": passed,
            "message": "测试通过" if passed else "改进不明显，建议回滚"
        }

    def apply_evolution(self, evolution_id: int, version_id: int) -> bool:
        """应用进化结果"""
        evolution = self.db.query(EvolutionRun).filter(
            EvolutionRun.id == evolution_id
        ).first()

        if not evolution:
            return False

        # 更新版本为当前版本
        version = self.db.query(VersionHistory).filter(
            VersionHistory.id == version_id
        ).first()

        if version:
            # 取消其他版本的当前状态
            self.db.query(VersionHistory).filter(
                VersionHistory.project_id == version.project_id,
                VersionHistory.asset_type == version.asset_type,
                VersionHistory.is_current == 1
            ).update({"is_current": 0})

            version.is_current = 1

        # 更新进化记录
        evolution.decision = EvolutionDecision.KEEP
        evolution.decided_at = utc_now()
        evolution.reason = f"已应用版本 {version_id}"

        self.db.commit()
        logger.info(f"进化已应用: evolution={evolution_id}, version={version_id}")
        return True

    def rollback_evolution(self, evolution_id: int) -> bool:
        """回滚进化"""
        evolution = self.db.query(EvolutionRun).filter(
            EvolutionRun.id == evolution_id
        ).first()

        if not evolution:
            return False

        evolution.decision = EvolutionDecision.REVERT
        evolution.decided_at = utc_now()
        evolution.reason = "改进效果不佳，已回滚"

        self.db.commit()
        logger.info(f"进化已回滚: {evolution_id}")
        return True

    def get_evolution_stats(self, project_id: Optional[int] = None) -> dict:
        """获取进化统计"""
        query = self.db.query(EvolutionRun)

        if project_id:
            query = query.filter(EvolutionRun.project_id == project_id)

        total = query.count()
        keep = query.filter(EvolutionRun.decision == EvolutionDecision.KEEP).count()
        revert = query.filter(EvolutionRun.decision == EvolutionDecision.REVERT).count()
        pending = query.filter(EvolutionRun.decision == EvolutionDecision.PENDING).count()

        success_rate = keep / (keep + revert) * 100 if (keep + revert) > 0 else 0

        return {
            "total_evolutions": total,
            "completed": keep,
            "rolled_back": revert,
            "pending": pending,
            "success_rate": round(success_rate, 1)
        }

    def get_best_practices(self, project_id: Optional[int] = None) -> List[dict]:
        """获取最佳实践"""
        query = self.db.query(EvolutionRun).filter(
            EvolutionRun.decision == EvolutionDecision.KEEP
        )

        if project_id:
            query = query.filter(EvolutionRun.project_id == project_id)

        successful = query.order_by(EvolutionRun.created_at.desc()).limit(10).all()

        return [
            {
                "id": e.id,
                "target_type": e.target_type,
                "target_name": e.target_name,
                "improvement": e.improvement,
                "reason": e.reason,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in successful
        ]

    async def evaluate_generation(
        self,
        db: Session,
        chapter_id: int,
        steps_data: List[dict],
        final_score: float
    ) -> dict:
        """
        Darwin 进化决策 - 评估是否保留当前生成结果

        策略：
        1. 如果分数 >= 85：保留
        2. 如果分数 < 60：回滚
        3. 如果 60 <= 分数 < 85：检查改进潜力

        Returns:
            {
                "keep": bool,
                "reason": str,
                "improvements": List[str]
            }
        """
        try:
            # 1. 简单阈值判断
            if final_score >= 85:
                return {
                    "keep": True,
                    "reason": f"评分优秀 ({final_score}/100)，保留结果",
                    "improvements": []
                }

            if final_score < 60:
                return {
                    "keep": False,
                    "reason": f"评分过低 ({final_score}/100)，需要重写",
                    "improvements": [
                        "整体情节需要重新设计",
                        "人物塑造需要加强",
                        "节奏控制需要调整"
                    ]
                }

            # 2. 分析步骤数据，提取改进点
            improvements = []

            for step in steps_data:
                agent = step.get("agent", "")
                score = step.get("score", 0)

                if agent == "Critic" and score < 80:
                    improvements.append("审稿发现较多问题，需要针对性改进")

                if agent == "Continuity" and score < 80:
                    improvements.append("连续性问题需要修复")

            # 3. 根据改进点数量决定
            if len(improvements) >= 2:
                return {
                    "keep": False,
                    "reason": f"评分 {final_score}，发现 {len(improvements)} 个主要问题",
                    "improvements": improvements
                }

            # 4. 默认保留
            return {
                "keep": True,
                "reason": f"评分可接受 ({final_score}/100)，改进点较少",
                "improvements": improvements if improvements else ["微调即可"]
            }

        except Exception as e:
            logger.error(f"Darwin 决策失败: {e}")
            return {
                "keep": True,
                "reason": f"评估过程出错，默认保留: {str(e)}",
                "improvements": []
            }
