"""
Feedback Service - 反馈收集与分析
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.feedback import Feedback, FeedbackCategory, FeedbackSeverity
from app.models.project import Project

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    反馈服务

    功能：
    - 收集多维度评分和反馈
    - 分析反馈模式
    - 生成改进建议
    - 追踪问题解决进度
    """

    def __init__(self, db: Session):
        self.db = db

    def create_feedback(
        self,
        project_id: int,
        chapter_id: Optional[int],
        category: FeedbackCategory,
        severity: FeedbackSeverity,
        content: str,
        dimension_scores: Optional[dict] = None,
        created_by: Optional[str] = "system"
    ) -> Feedback:
        """
        创建反馈

        Args:
            project_id: 项目ID
            chapter_id: 章节ID（可选）
            category: 反馈类别
            severity: 严重程度
            content: 反馈内容
            dimension_scores: 各维度评分
            created_by: 创建者
        """
        feedback = Feedback(
            project_id=project_id,
            chapter_id=chapter_id,
            category=category,
            severity=severity,
            content=content,
            dimension_scores=dimension_scores or {},
            created_by=created_by,
            metadata={
                "created_at": datetime.now().isoformat(),
                "status": "open"
            }
        )

        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        logger.info(f"反馈已创建: {feedback.id}")
        return feedback

    def analyze_chapter(
        self,
        chapter_id: int,
        content: str,
        chapter_metadata: Optional[dict] = None
    ) -> dict:
        """
        AI 分析章节并生成反馈

        分析维度：
        - 剧情连贯性
        - 人物一致性
        - 节奏把控
        - 文笔质量
        - 吸引力
        """
        # 这里后续集成真实 AI 分析
        # 当前使用模拟评分
        import random

        dimensions = {
            "plot_coherence": random.uniform(6, 9),
            "character_consistency": random.uniform(6, 9),
            "pacing": random.uniform(6, 9),
            "writing_quality": random.uniform(6, 9),
            "engagement": random.uniform(6, 9),
        }

        avg_score = sum(dimensions.values()) / len(dimensions)

        # 根据分数生成反馈
        issues = []
        if dimensions["plot_coherence"] < 7:
            issues.append("剧情连贯性需要改进，建议检查伏笔回收")
        if dimensions["character_consistency"] < 7:
            issues.append("人物行为一致性欠佳，建议核对人物设定")
        if dimensions["pacing"] < 7:
            issues.append("节奏把控需要优化，部分段落过于拖沓")
        if dimensions["writing_quality"] < 7:
            issues.append("文笔质量有待提升，建议增加描写细节")
        if dimensions["engagement"] < 7:
            issues.append("章节吸引力不足，建议加强悬念设置")

        feedback_content = "\n".join(issues) if issues else "整体质量良好，继续保持"

        # 确定严重程度和类别
        severity = (
            FeedbackSeverity.HIGH if avg_score < 6
            else FeedbackSeverity.MEDIUM if avg_score < 7.5
            else FeedbackSeverity.LOW
        )

        category = (
            FeedbackCategory.CONTENT if avg_score < 7
            else FeedbackCategory.STYLE
        )

        return {
            "overall_score": round(avg_score, 1),
            "dimension_scores": {k: round(v, 1) for k, v in dimensions.items()},
            "feedback": feedback_content,
            "severity": severity.value,
            "category": category.value,
            "suggestions": self._generate_suggestions(dimensions, issues)
        }

    def _generate_suggestions(
        self,
        dimensions: dict,
        issues: List[str]
    ) -> List[dict]:
        """生成改进建议"""
        suggestions = []

        improvement_tips = {
            "plot_coherence": {
                "technique": "伏笔回收检查",
                "prompt_template": "检查本章伏笔是否在前后文中有呼应，补充缺失的衔接"
            },
            "character_consistency": {
                "technique": "人物一致性校验",
                "prompt_template": "核对人物行为是否符合其性格设定和经历"
            },
            "pacing": {
                "technique": "节奏优化",
                "prompt_template": "调整叙事节奏，删减冗余描述，突出关键情节"
            },
            "writing_quality": {
                "technique": "描写增强",
                "prompt_template": "增加感官描写，丰富场景细节"
            },
            "engagement": {
                "technique": "悬念设置",
                "prompt_template": "在章节结尾设置悬念或冲突，增强吸引力"
            }
        }

        for dim, score in dimensions.items():
            if score < 7.5 and dim in improvement_tips:
                suggestions.append({
                    "dimension": dim,
                    "score": score,
                    **improvement_tips[dim]
                })

        return suggestions

    def get_feedback_stats(self, project_id: Optional[int] = None) -> dict:
        """获取反馈统计"""
        query = self.db.query(Feedback)

        if project_id:
            query = query.filter(Feedback.project_id == project_id)

        total = query.count()
        resolved = query.filter(Feedback.resolved_at.isnot(None)).count()

        # 按类别统计
        by_category = {}
        for cat in FeedbackCategory:
            count = query.filter(Feedback.category == cat).count()
            by_category[cat.value] = count

        # 按严重程度统计
        by_severity = {}
        for sev in FeedbackSeverity:
            count = query.filter(Feedback.severity == sev).count()
            by_severity[sev.value] = count

        # 计算平均分
        all_feedback = query.all()
        avg_scores = {}
        if all_feedback:
            for dim in ["plot_coherence", "character_consistency", "pacing", "writing_quality", "engagement"]:
                scores = [
                    f.dimension_scores.get(dim, 0)
                    for f in all_feedback
                    if f.dimension_scores
                ]
                if scores:
                    avg_scores[dim] = round(sum(scores) / len(scores), 2)

        return {
            "total": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0,
            "by_category": by_category,
            "by_severity": by_severity,
            "average_scores": avg_scores
        }

    def get_feedback_trend(
        self,
        project_id: int,
        days: int = 30
    ) -> List[dict]:
        """获取反馈趋势"""
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days)

        feedbacks = self.db.query(Feedback).filter(
            Feedback.project_id == project_id,
            Feedback.created_at >= cutoff
        ).order_by(Feedback.created_at.asc()).all()

        # 按日期聚合
        daily_scores = {}
        for fb in feedbacks:
            date = fb.created_at.strftime("%Y-%m-%d")
            if date not in daily_scores:
                daily_scores[date] = []

            if fb.dimension_scores:
                avg = sum(fb.dimension_scores.values()) / len(fb.dimension_scores)
                daily_scores[date].append(avg)

        trend = [
            {
                "date": date,
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
                "count": len(scores)
            }
            for date, scores in sorted(daily_scores.items())
        ]

        return trend

    def resolve_feedback(self, feedback_id: int, resolution: str) -> bool:
        """解决反馈"""
        feedback = self.db.query(Feedback).filter(
            Feedback.id == feedback_id
        ).first()

        if not feedback:
            return False

        feedback.resolved_at = datetime.now()
        feedback.metadata = feedback.metadata or {}
        feedback.metadata["resolution"] = resolution
        feedback.metadata["resolved_at"] = datetime.now().isoformat()

        self.db.commit()
        return True

    def get_common_issues(
        self,
        project_id: Optional[int] = None,
        limit: int = 10
    ) -> List[dict]:
        """获取常见问题模式"""
        query = self.db.query(Feedback)

        if project_id:
            query = query.filter(Feedback.project_id == project_id)

        # 未解决的高优先级问题
        issues = query.filter(
            Feedback.resolved_at.is_(None),
            Feedback.severity.in_([FeedbackSeverity.HIGH, FeedbackSeverity.CRITICAL])
        ).order_by(Feedback.created_at.desc()).limit(limit).all()

        return [
            {
                "id": issue.id,
                "category": issue.category.value,
                "severity": issue.severity.value,
                "content": issue.content[:100] + "..." if len(issue.content) > 100 else issue.content,
                "created_at": issue.created_at.isoformat() if issue.created_at else None
            }
            for issue in issues
        ]
