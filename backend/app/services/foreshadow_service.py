"""
Foreshadow Service - 伏笔管理服务
P4 Phase 3: 伏笔埋设、推进、回收全生命周期
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.foreshadow import Foreshadow, ForeshadowPlan, ForeshadowReview
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class ForeshadowService:
    """伏笔管理服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== CRUD Operations ==========

    def create_foreshadow(
        self,
        project_id: int,
        title: str,
        foreshadow_type: str = "item",
        setup_chapter: int = None,
        expected_payoff_chapter: int = None,
        setup_content: str = "",
        payoff_plan: str = "",
        related_characters: List[str] = None,
        related_items: List[str] = None,
        importance_score: float = 0.5
    ) -> Foreshadow:
        """创建伏笔"""
        foreshadow = Foreshadow(
            project_id=project_id,
            title=title,
            foreshadow_type=foreshadow_type,
            setup_chapter=setup_chapter,
            expected_payoff_chapter=expected_payoff_chapter,
            setup_content=setup_content,
            payoff_plan=payoff_plan,
            related_characters=related_characters or [],
            related_items=related_items or [],
            importance_score=importance_score,
            status="planned"
        )
        self.db.add(foreshadow)
        self.db.commit()
        self.db.refresh(foreshadow)
        logger.info(f"[Foreshadow] 创建伏笔: {title} (project={project_id})")
        return foreshadow

    def get_foreshadow(self, foreshadow_id: int) -> Optional[Foreshadow]:
        """获取单个伏笔"""
        return self.db.query(Foreshadow).filter(
            Foreshadow.id == foreshadow_id
        ).first()

    def list_foreshadows(
        self,
        project_id: int,
        status: str = None,
        foreshadow_type: str = None,
        min_importance: float = 0.0
    ) -> List[Foreshadow]:
        """列示伏笔"""
        query = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.importance_score >= min_importance
        )
        if status:
            query = query.filter(Foreshadow.status == status)
        if foreshadow_type:
            query = query.filter(Foreshadow.foreshadow_type == foreshadow_type)

        return query.order_by(desc(Foreshadow.importance_score)).all()

    def update_foreshadow(
        self,
        foreshadow_id: int,
        **kwargs
    ) -> Optional[Foreshadow]:
        """更新伏笔"""
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None

        for key, value in kwargs.items():
            if hasattr(foreshadow, key):
                setattr(foreshadow, key, value)

        foreshadow.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(foreshadow)
        return foreshadow

    # ========== Lifecycle Operations ==========

    def mark_as_planted(
        self,
        foreshadow_id: int,
        setup_chapter: int,
        setup_content: str
    ) -> Optional[Foreshadow]:
        """标记伏笔已埋设"""
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None

        foreshadow.status = "planted"
        foreshadow.setup_chapter = setup_chapter
        foreshadow.setup_content = setup_content
        foreshadow.updated_at = utc_now()

        self.db.commit()
        logger.info(f"[Foreshadow] 伏笔已埋设: {foreshadow.title} @ 第{setup_chapter}章")
        return foreshadow

    def mark_as_developed(
        self,
        foreshadow_id: int,
        chapter_index: int,
        development_note: str
    ) -> Optional[Foreshadow]:
        """标记伏笔已推进"""
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None

        foreshadow.status = "developed"

        notes = foreshadow.development_notes or []
        notes.append({
            "chapter": chapter_index,
            "note": development_note,
            "timestamp": utc_now().isoformat()
        })
        foreshadow.development_notes = notes
        foreshadow.updated_at = utc_now()

        self.db.commit()
        logger.info(f"[Foreshadow] 伏笔已推进: {foreshadow.title} @ 第{chapter_index}章")
        return foreshadow

    def mark_as_ready_to_payoff(
        self,
        foreshadow_id: int
    ) -> Optional[Foreshadow]:
        """标记伏笔准备回收"""
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None

        foreshadow.status = "ready_to_payoff"
        foreshadow.updated_at = utc_now()

        self.db.commit()
        logger.info(f"[Foreshadow] 伏笔准备回收: {foreshadow.title}")
        return foreshadow

    def mark_as_paid_off(
        self,
        foreshadow_id: int,
        payoff_chapter: int,
        payoff_content: str
    ) -> Optional[Foreshadow]:
        """标记伏笔已回收"""
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None

        foreshadow.status = "paid_off"
        foreshadow.actual_payoff_chapter = payoff_chapter
        foreshadow.payoff_content = payoff_content
        foreshadow.updated_at = utc_now()

        self.db.commit()
        logger.info(f"[Foreshadow] 伏笔已回收: {foreshadow.title} @ 第{payoff_chapter}章")
        return foreshadow

    def mark_as_abandoned(
        self,
        foreshadow_id: int,
        reason: str = ""
    ) -> Optional[Foreshadow]:
        """标记伏笔废弃"""
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None

        foreshadow.status = "abandoned"
        foreshadow.updated_at = utc_now()

        self.db.commit()
        logger.info(f"[Foreshadow] 伏笔已废弃: {foreshadow.title}, reason={reason}")
        return foreshadow

    def calculate_risk_scores(self, project_id: int, current_chapter: int):
        """
        计算所有活跃伏笔的遗忘风险

        风险因素:
        - 已埋设但未回收的时间越长，风险越高
        - 重要性越高的伏笔，风险越高
        - 已超过预期回收章节的，风险剧增
        """
        foreshadows = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status.in_(["planted", "developed", "ready_to_payoff"])
        ).all()

        for f in foreshadows:
            risk = 0.0

            if f.setup_chapter:
                # 基础风险：每章增加2%
                chapters_passed = current_chapter - f.setup_chapter
                risk += min(chapters_passed * 0.02, 0.5)

                # 超出预期回收时间
                if f.expected_payoff_chapter and current_chapter > f.expected_payoff_chapter:
                    overdue = current_chapter - f.expected_payoff_chapter
                    risk += min(overdue * 0.1, 0.4)

            # 重要性加权
            risk *= (0.5 + f.importance_score)

            # 读者期待越高，风险越高
            risk *= (0.5 + f.reader_expectation)

            f.risk_score = min(risk, 1.0)

            # 高风险自动标记
            if f.risk_score > 0.7:
                f.status = "risky"

        self.db.commit()
        logger.info(f"[Foreshadow] 已计算 {len(foreshadows)} 个伏笔的风险分数")

    # ========== Plan Operations ==========

    def create_chapter_plan(
        self,
        project_id: int,
        chapter_id: int,
        chapter_index: int
    ) -> ForeshadowPlan:
        """
        为章节创建伏笔计划

        根据当前状态自动生成:
        - 本章要新增的伏笔
        - 要推进的伏笔
        - 要回收的伏笔
        - 风险伏笔提醒
        """
        plan = ForeshadowPlan(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_index=chapter_index
        )

        # 计算风险分数
        self.calculate_risk_scores(project_id, chapter_index)

        # 1. 风险伏笔（必须处理）
        risky = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.risk_score > 0.6,
            Foreshadow.status.in_(["planted", "developed", "risky"])
        ).order_by(desc(Foreshadow.risk_score)).limit(3).all()
        plan.risky_foreshadow_ids = [f.id for f in risky]

        # 2. 应该回收的伏笔（到达或超过预期章节）
        ready_to_payoff = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status == "ready_to_payoff"
        ).all()

        should_payoff = []
        for f in ready_to_payoff:
            if f.expected_payoff_chapter and chapter_index >= f.expected_payoff_chapter:
                should_payoff.append(f.id)

        plan.payoff_foreshadow_ids = should_payoff[:3]  # 最多3个

        # 3. 需要推进的伏笔
        need_development = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status == "planted"
        ).order_by(desc(Foreshadow.importance_score)).limit(5).all()
        plan.develop_foreshadow_ids = [f.id for f in need_development]

        # 4. 新伏笔计划（基于章节阶段）
        new_foreshadows = self._suggest_new_foreshadows(project_id, chapter_index)
        plan.new_foreshadows = new_foreshadows

        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        return plan

    def _suggest_new_foreshadows(
        self,
        project_id: int,
        chapter_index: int
    ) -> List[Dict]:
        """根据章节阶段建议新伏笔"""
        suggestions = []

        # 开篇阶段：埋设核心伏笔
        if chapter_index <= 3:
            suggestions.append({
                "title": "主线核心伏笔",
                "type": "prophecy",
                "suggested_chapter": chapter_index,
                "expected_payoff": chapter_index + 30,
                "importance": 0.9
            })

        # 每10章埋设中期伏笔
        if chapter_index % 10 == 5:
            suggestions.append({
                "title": f"第{chapter_index}章关键伏笔",
                "type": "item",
                "suggested_chapter": chapter_index,
                "expected_payoff": chapter_index + 15,
                "importance": 0.7
            })

        return suggestions

    def get_chapter_plan(
        self,
        project_id: int,
        chapter_id: int = None,
        chapter_index: int = None
    ) -> Optional[ForeshadowPlan]:
        """获取章节伏笔计划"""
        query = self.db.query(ForeshadowPlan).filter(
            ForeshadowPlan.project_id == project_id
        )
        if chapter_id:
            query = query.filter(ForeshadowPlan.chapter_id == chapter_id)
        if chapter_index:
            query = query.filter(ForeshadowPlan.chapter_index == chapter_index)

        return query.order_by(desc(ForeshadowPlan.created_at)).first()

    def format_plan_for_prompt(self, plan: ForeshadowPlan) -> str:
        """将伏笔计划格式化为Prompt文本"""
        sections = ["## 本章伏笔任务\n"]

        # 新伏笔
        if plan.new_foreshadows:
            sections.append("### 计划埋设的新伏笔")
            for i, f in enumerate(plan.new_foreshadows[:3], 1):
                sections.append(f"{i}. {f.get('title')} ({f.get('type')}) - 重要性:{f.get('importance', 0.5)}")
                if f.get('expected_payoff'):
                    sections.append(f"   预期回收: 第{f['expected_payoff']}章")
            sections.append("")

        # 推进的伏笔
        if plan.develop_foreshadow_ids:
            sections.append("### 需要推进的伏笔")
            for fid in plan.develop_foreshadow_ids[:3]:
                f = self.get_foreshadow(fid)
                if f:
                    sections.append(f"- {f.title} (第{f.setup_chapter}章埋设)")
            sections.append("")

        # 回收的伏笔
        if plan.payoff_foreshadow_ids:
            sections.append("### 本章必须回收的伏笔")
            for fid in plan.payoff_foreshadow_ids:
                f = self.get_foreshadow(fid)
                if f:
                    sections.append(f"- **{f.title}** (第{f.setup_chapter}章埋设)")
                    if f.payoff_plan:
                        sections.append(f"  回收计划: {f.payoff_plan[:100]}...")
            sections.append("")

        # 风险提醒
        if plan.risky_foreshadow_ids:
            sections.append("### ⚠️ 高风险伏笔（即将被遗忘）")
            for fid in plan.risky_foreshadow_ids[:3]:
                f = self.get_foreshadow(fid)
                if f:
                    sections.append(f"- {f.title} (风险分数: {f.risk_score:.2f})")
            sections.append("")

        return "\n".join(sections)

    # ========== Review Operations ==========

    def create_review(
        self,
        project_id: int,
        chapter_id: int,
        forgotten: List[Dict] = None,
        premature: List[Dict] = None,
        delayed: List[Dict] = None,
        quality_issues: List[Dict] = None,
        contradictions: List[Dict] = None,
        foreshadow_score: float = 0.0,
        suggestions: List[str] = None
    ) -> ForeshadowReview:
        """创建伏笔评审记录"""
        review = ForeshadowReview(
            project_id=project_id,
            chapter_id=chapter_id,
            forgotten_foreshadows=forgotten or [],
            premature_payoffs=premature or [],
            delayed_payoffs=delayed or [],
            payoff_quality_issues=quality_issues or [],
            contradictions=contradictions or [],
            foreshadow_score=foreshadow_score,
            suggestions=suggestions or []
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    # ========== Statistics ==========

    def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """获取项目伏笔统计"""
        total = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id
        ).count()

        by_status = {}
        for status in ["planned", "planted", "developed", "ready_to_payoff", "paid_off", "abandoned", "risky"]:
            count = self.db.query(Foreshadow).filter(
                Foreshadow.project_id == project_id,
                Foreshadow.status == status
            ).count()
            by_status[status] = count

        by_type = {}
        types = ["item", "dialogue", "prophecy", "secret", "identity", "relationship", "world_rule"]
        for t in types:
            count = self.db.query(Foreshadow).filter(
                Foreshadow.project_id == project_id,
                Foreshadow.foreshadow_type == t
            ).count()
            by_type[t] = count

        # 平均回收时间
        paid_off = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status == "paid_off"
        ).all()

        avg_payoff_distance = 0
        if paid_off:
            distances = [f.actual_payoff_chapter - f.setup_chapter for f in paid_off if f.setup_chapter]
            if distances:
                avg_payoff_distance = sum(distances) / len(distances)

        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "avg_payoff_distance": round(avg_payoff_distance, 1),
            "paid_off_count": len(paid_off)
        }
