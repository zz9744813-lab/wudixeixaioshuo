"""
KnowledgeContextService - 联网研究知识上下文组装 (P1)
把 KnowledgePattern（套路）和 ReaderInsight（读者避坑）统一组装成写作可用上下文。
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.research import KnowledgePattern, ReaderInsight

logger = logging.getLogger(__name__)


class KnowledgeContextService:
    """联网研究知识上下文服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_context_for_chapter(
        self,
        project_id: int,
        chapter_title: str = "",
        chapter_index: int = 1,
        chapter_plan: Optional[dict] = None,
        role: str = "draft",
        limit_patterns: int = 8,
        limit_insights: int = 8,
    ) -> dict:
        """按项目题材拉取可用套路与读者避坑"""
        genre = None
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            genre = project.genre

        pattern_q = self.db.query(KnowledgePattern)
        if genre:
            pattern_q = pattern_q.filter(KnowledgePattern.genre == genre)
        patterns = pattern_q.order_by(
            KnowledgePattern.confidence.desc(),
            KnowledgePattern.created_at.desc(),
        ).limit(limit_patterns).all()

        insight_q = self.db.query(ReaderInsight)
        if genre:
            insight_q = insight_q.filter(ReaderInsight.genre == genre)
        insights = insight_q.order_by(
            ReaderInsight.confidence.desc(),
            ReaderInsight.created_at.desc(),
        ).limit(limit_insights).all()

        return {
            "genre": genre,
            "patterns": [
                {
                    "pattern_name": p.pattern_name,
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "applicable_scene": p.applicable_scene or "",
                    "anti_patterns": p.anti_patterns or "",
                    "confidence": p.confidence,
                }
                for p in patterns
            ],
            "reader_insights": [
                {
                    "insight_type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "evidence": i.evidence or "",
                    "confidence": i.confidence,
                }
                for i in insights
            ],
        }

    def format_for_prompt(self, context: dict, role: str = "draft") -> str:
        """把上下文格式化为可注入 Prompt 的 Markdown（实例方法委托静态实现）"""
        return self.format_context(context, role)

    @staticmethod
    def format_context(context: dict, role: str = "draft") -> str:
        """无状态格式化，供 PipelineService 直接调用"""
        patterns = context.get("patterns", [])
        insights = context.get("reader_insights", [])
        if not patterns and not insights:
            return ""

        heading = "## 联网研究审稿依据" if role == "critic" else "## 联网研究知识"
        lines = [heading, ""]

        if patterns:
            lines.append("### 可用套路")
            for p in patterns:
                lines.append(f"- [{p['pattern_type']}] {p['pattern_name']}：{p['description']}")
                if p.get("applicable_scene"):
                    lines.append(f"  - 适用场景：{p['applicable_scene']}")
                if p.get("anti_patterns"):
                    lines.append(f"  - 避坑：{p['anti_patterns']}")
            lines.append("")

        if insights:
            lines.append("### 读者避坑")
            for i in insights:
                lines.append(f"- [{i['insight_type']}] {i['title']}：{i['description']}")
                if i.get("evidence"):
                    lines.append(f"  - 依据：{i['evidence']}")
            lines.append("")

        return "\n".join(lines).strip()
