"""Knowledge Service - 知识库写入/查询服务。"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.research import KnowledgePattern, ReaderInsight, TrendReport


class KnowledgeService:
    """知识库管理：写入、查询、去重、应用。"""

    def __init__(self, db: Session):
        self.db = db

    async def save_patterns(self, patterns: List[Dict[str, Any]], source_ids: Optional[List[int]] = None) -> List[KnowledgePattern]:
        """保存知识模式，自动去重。"""
        saved = []
        for p in patterns:
            existing = self.db.query(KnowledgePattern).filter(
                KnowledgePattern.pattern_name == p.get("pattern_name"),
                KnowledgePattern.pattern_type == p.get("pattern_type"),
                KnowledgePattern.genre == p.get("genre"),
            ).first()
            if existing:
                existing.confidence = max(existing.confidence, p.get("confidence", 0.5))
                if source_ids:
                    existing.source_ids = list(set((existing.source_ids or []) + source_ids))
                saved.append(existing)
            else:
                pattern = KnowledgePattern(
                    genre=p.get("genre"),
                    tag=p.get("tag"),
                    pattern_name=p.get("pattern_name", ""),
                    pattern_type=p.get("pattern_type", "hook"),
                    description=p.get("description", ""),
                    applicable_scene=p.get("applicable_scene"),
                    anti_patterns=p.get("anti_patterns"),
                    source_ids=source_ids,
                    confidence=p.get("confidence", 0.5),
                )
                self.db.add(pattern)
                saved.append(pattern)
        self.db.commit()
        return saved

    async def save_reader_insights(self, insights: List[Dict[str, Any]], source_ids: Optional[List[int]] = None) -> List[ReaderInsight]:
        """保存读者洞察，自动去重。"""
        saved = []
        for ins in insights:
            existing = self.db.query(ReaderInsight).filter(
                ReaderInsight.title == ins.get("title"),
                ReaderInsight.insight_type == ins.get("insight_type"),
                ReaderInsight.genre == ins.get("genre"),
            ).first()
            if existing:
                existing.confidence = max(existing.confidence, ins.get("confidence", 0.5))
                saved.append(existing)
            else:
                insight = ReaderInsight(
                    genre=ins.get("genre"),
                    insight_type=ins.get("insight_type", "like"),
                    title=ins.get("title", ""),
                    description=ins.get("description", ""),
                    evidence=ins.get("evidence"),
                    source_ids=source_ids,
                    confidence=ins.get("confidence", 0.5),
                )
                self.db.add(insight)
                saved.append(insight)
        self.db.commit()
        return saved

    async def save_trend_report(self, report: Dict[str, Any], source_ids: Optional[List[int]] = None) -> TrendReport:
        """保存趋势报告。"""
        trend = TrendReport(
            genre=report.get("genre"),
            platform=report.get("platform"),
            report_title=report.get("report_title", ""),
            report_body=report.get("report_body", ""),
            trend_tags=report.get("trend_tags"),
            source_ids=source_ids,
        )
        self.db.add(trend)
        self.db.commit()
        self.db.refresh(trend)
        return trend

    def get_patterns(self, genre: Optional[str] = None, pattern_type: Optional[str] = None, limit: int = 50) -> List[KnowledgePattern]:
        query = self.db.query(KnowledgePattern)
        if genre:
            query = query.filter(KnowledgePattern.genre == genre)
        if pattern_type:
            query = query.filter(KnowledgePattern.pattern_type == pattern_type)
        return query.order_by(KnowledgePattern.confidence.desc()).limit(limit).all()

    def get_reader_insights(self, genre: Optional[str] = None, insight_type: Optional[str] = None, limit: int = 50) -> List[ReaderInsight]:
        query = self.db.query(ReaderInsight)
        if genre:
            query = query.filter(ReaderInsight.genre == genre)
        if insight_type:
            query = query.filter(ReaderInsight.insight_type == insight_type)
        return query.order_by(ReaderInsight.confidence.desc()).limit(limit).all()

    def get_trend_reports(self, genre: Optional[str] = None, platform: Optional[str] = None, limit: int = 20) -> List[TrendReport]:
        query = self.db.query(TrendReport)
        if genre:
            query = query.filter(TrendReport.genre == genre)
        if platform:
            query = query.filter(TrendReport.platform == platform)
        return query.order_by(TrendReport.created_at.desc()).limit(limit).all()
