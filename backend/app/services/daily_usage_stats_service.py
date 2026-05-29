"""
Daily Usage Stats Service - 每日成本统计服务
P2-5: 成本统计持久化，支持预算硬上限
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.usage_stats import DailyUsageStats
from app.utils.time_utils import utc_now


class DailyUsageStatsService:
    """每日使用统计服务"""

    def __init__(self, db: Session):
        self.db = db

    def record_usage(
        self,
        *,
        project_id: Optional[int] = None,
        provider: str = "",
        model_name: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        chapter_count: int = 0,
        task_count: int = 0,
        word_count: int = 0,
        success: bool = True,
    ) -> DailyUsageStats:
        """
        记录使用统计

        Args:
            project_id: 项目ID，None表示全局统计
            provider: 提供商名称
            model_name: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            cost: 成本（美元）
            chapter_count: 生成章节数
            task_count: 任务数
            word_count: 生成字数
            success: 是否成功

        Returns:
            DailyUsageStats 记录
        """
        today = date.today()

        # 查找或创建统计记录
        stats = self.db.query(DailyUsageStats).filter(
            and_(
                DailyUsageStats.date == today,
                DailyUsageStats.project_id == project_id,
                DailyUsageStats.provider == provider,
                DailyUsageStats.model_name == model_name,
            )
        ).first()

        if not stats:
            stats = DailyUsageStats(
                date=today,
                project_id=project_id,
                provider=provider,
                model_name=model_name,
            )
            self.db.add(stats)

        # 更新统计
        stats.input_tokens += input_tokens
        stats.output_tokens += output_tokens
        stats.total_tokens += input_tokens + output_tokens
        stats.cost += cost
        stats.chapter_count += chapter_count
        stats.task_count += task_count
        stats.word_count += word_count

        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1

        stats.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(stats)

        return stats

    def get_today_stats(
        self,
        project_id: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        获取今日统计

        Args:
            project_id: 项目ID，None表示全局

        Returns:
            统计字典
        """
        today = date.today()

        query = self.db.query(DailyUsageStats).filter(
            DailyUsageStats.date == today
        )

        if project_id is not None:
            query = query.filter(DailyUsageStats.project_id == project_id)

        stats_list = query.all()

        # 汇总统计
        total = {
            "input_tokens": sum(s.input_tokens for s in stats_list),
            "output_tokens": sum(s.output_tokens for s in stats_list),
            "total_tokens": sum(s.total_tokens for s in stats_list),
            "cost": sum(s.cost for s in stats_list),
            "chapter_count": sum(s.chapter_count for s in stats_list),
            "task_count": sum(s.task_count for s in stats_list),
            "word_count": sum(s.word_count for s in stats_list),
            "success_count": sum(s.success_count for s in stats_list),
            "failure_count": sum(s.failure_count for s in stats_list),
        }

        return total

    def check_budget(self, project_id: int) -> Dict[str, any]:
        """
        检查项目预算

        Returns:
            {
                "within_budget": True/False,
                "current_cost": float,
                "daily_budget": float,
                "remaining": float,
                "usage_percent": float,
            }
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {
                "within_budget": False,
                "error": "项目不存在",
            }

        daily_budget = project.daily_budget or 10.0

        # 获取今日成本
        today_stats = self.get_today_stats(project_id=project_id)
        current_cost = today_stats.get("cost", 0.0)

        remaining = daily_budget - current_cost
        usage_percent = (current_cost / daily_budget * 100) if daily_budget > 0 else 0

        return {
            "within_budget": current_cost < daily_budget,
            "current_cost": round(current_cost, 4),
            "daily_budget": daily_budget,
            "remaining": round(remaining, 4),
            "usage_percent": round(usage_percent, 2),
        }

    def get_project_stats(
        self,
        project_id: int,
        days: int = 7,
    ) -> List[Dict]:
        """
        获取项目最近N天统计

        Args:
            project_id: 项目ID
            days: 天数

        Returns:
            统计列表
        """
        start_date = date.today() - timedelta(days=days)

        stats = self.db.query(DailyUsageStats).filter(
            and_(
                DailyUsageStats.project_id == project_id,
                DailyUsageStats.date >= start_date,
            )
        ).order_by(DailyUsageStats.date.desc()).all()

        return [
            {
                "date": s.date.isoformat(),
                "provider": s.provider,
                "model_name": s.model_name,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "total_tokens": s.total_tokens,
                "cost": s.cost,
                "chapter_count": s.chapter_count,
                "task_count": s.task_count,
                "word_count": s.word_count,
            }
            for s in stats
        ]

    def get_global_stats(self, days: int = 7) -> Dict:
        """
        获取全局统计

        Args:
            days: 天数

        Returns:
            统计字典
        """
        start_date = date.today() - timedelta(days=days)

        # 按天汇总
        daily_stats = self.db.query(
            DailyUsageStats.date,
            func.sum(DailyUsageStats.total_tokens).label("total_tokens"),
            func.sum(DailyUsageStats.cost).label("total_cost"),
            func.sum(DailyUsageStats.chapter_count).label("total_chapters"),
            func.sum(DailyUsageStats.word_count).label("total_words"),
        ).filter(
            DailyUsageStats.date >= start_date
        ).group_by(DailyUsageStats.date).all()

        return {
            "period_days": days,
            "daily": [
                {
                    "date": s.date.isoformat(),
                    "total_tokens": s.total_tokens or 0,
                    "cost": s.total_cost or 0.0,
                    "chapters": s.total_chapters or 0,
                    "words": s.total_words or 0,
                }
                for s in daily_stats
            ],
            "summary": {
                "total_tokens": sum(s.total_tokens or 0 for s in daily_stats),
                "total_cost": sum(s.total_cost or 0.0 for s in daily_stats),
                "total_chapters": sum(s.total_chapters or 0 for s in daily_stats),
                "total_words": sum(s.total_words or 0 for s in daily_stats),
            }
        }

    @staticmethod
    def should_stop_for_budget(db: Session, project_id: int) -> bool:
        """
        检查是否应因预算超支停止

        Args:
            db: 数据库会话
            project_id: 项目ID

        Returns:
            True: 应停止，False: 可继续
        """
        service = DailyUsageStatsService(db)
        budget_info = service.check_budget(project_id)

        if "error" in budget_info:
            return True

        return not budget_info["within_budget"]
