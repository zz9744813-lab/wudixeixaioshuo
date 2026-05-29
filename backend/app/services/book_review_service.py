"""
Book Review Service - 成书复盘与技巧卡蒸馏服务 (C4)
从完成的书籍中提取经验、生成技巧卡、更新技巧库
"""

import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.models.project import Project
from app.models.chapter import Chapter, ChapterStatus
from app.models.technique import TechniqueCard, BookProfile
from app.models.memory import ChapterMemory, CharacterMemory
from app.models.feedback import Feedback
from app.services.skill_service import SkillSelectionService, BookProfileService

logger = logging.getLogger(__name__)


class BookReviewService:
    """成书复盘服务"""

    def __init__(self, db: Session):
        self.db = db
        self.skill_service = SkillSelectionService(db)
        self.profile_service = BookProfileService(db)

    # ========== 成书复盘 ==========

    def review_completed_book(
        self,
        project_id: int,
        include_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        对完成的书籍进行全面复盘

        Args:
            project_id: 项目ID
            include_analysis: 是否包含详细分析

        Returns:
            复盘报告
        """
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        # 获取所有已完成章节
        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status == ChapterStatus.COMPLETED
        ).order_by(Chapter.chapter_index).all()

        if not chapters:
            return {"error": "没有已完成的章节"}

        # 基础统计
        total_chapters = len(chapters)
        total_words = sum(c.word_count or 0 for c in chapters)
        avg_score = sum(c.total_score or 0 for c in chapters) / total_chapters if total_chapters > 0 else 0

        # 各维度平均分
        dimension_scores = self._aggregate_dimension_scores(chapters)

        # 高分章节和低分章节
        high_score_chapters = [c for c in chapters if (c.total_score or 0) >= 85]
        low_score_chapters = [c for c in chapters if (c.total_score or 0) < 60]

        # 技巧卡使用情况
        skill_usage = self._analyze_skill_usage(project_id, chapters)

        # 生成复盘报告
        review_report = {
            "project_id": project_id,
            "project_name": project.name,
            "review_time": datetime.now().isoformat(),
            "summary": {
                "total_chapters": total_chapters,
                "total_words": total_words,
                "avg_score": round(avg_score, 2),
                "high_score_count": len(high_score_chapters),
                "low_score_count": len(low_score_chapters),
            },
            "dimension_analysis": dimension_scores,
            "chapter_analysis": {
                "high_score_chapters": [
                    {"index": c.chapter_index, "title": c.title, "score": c.total_score}
                    for c in high_score_chapters[:10]
                ],
                "low_score_chapters": [
                    {"index": c.chapter_index, "title": c.title, "score": c.total_score}
                    for c in low_score_chapters[:10]
                ],
            },
            "skill_usage": skill_usage,
        }

        if include_analysis:
            # 生成详细分析
            review_report["strengths"] = self._identify_strengths(chapters, dimension_scores)
            review_report["weaknesses"] = self._identify_weaknesses(chapters, dimension_scores)
            review_report["patterns"] = self._analyze_patterns(chapters)

        logger.info(f"成书复盘完成: project_id={project_id}, chapters={total_chapters}")
        return review_report

    def _aggregate_dimension_scores(self, chapters: List[Chapter]) -> Dict[str, float]:
        """聚合各维度评分"""
        dimensions = defaultdict(list)

        for ch in chapters:
            if ch.dimension_scores:
                for dim, score in ch.dimension_scores.items():
                    dimensions[dim].append(score)

        return {
            dim: round(sum(scores) / len(scores), 2) if scores else 0
            for dim, scores in dimensions.items()
        }

    def _analyze_skill_usage(
        self,
        project_id: int,
        chapters: List[Chapter]
    ) -> Dict[str, Any]:
        """分析技巧卡使用情况"""
        # 统计使用的技巧卡
        skill_stats = defaultdict(lambda: {"count": 0, "avg_score": 0, "scores": []})

        for ch in chapters:
            # 从章节元数据中获取使用的技巧
            used_skills = ch.metadata.get("used_skills", []) if ch.metadata else []
            for skill_id in used_skills:
                skill_stats[skill_id]["count"] += 1
                skill_stats[skill_id]["scores"].append(ch.total_score or 0)

        # 计算平均效果
        for skill_id, stats in skill_stats.items():
            if stats["scores"]:
                stats["avg_score"] = round(sum(stats["scores"]) / len(stats["scores"]), 2)
            del stats["scores"]  # 移除原始分数列表

        # 获取技巧卡详情
        skill_details = []
        for skill_id in sorted(skill_stats.keys(), key=lambda x: skill_stats[x]["count"], reverse=True)[:20]:
            card = self.db.query(TechniqueCard).filter(
                TechniqueCard.id == skill_id
            ).first()
            if card:
                skill_details.append({
                    "id": card.id,
                    "title": card.title,
                    "category": card.category,
                    "usage_count": skill_stats[skill_id]["count"],
                    "avg_chapter_score": skill_stats[skill_id]["avg_score"],
                })

        return {
            "total_unique_skills": len(skill_stats),
            "top_skills": skill_details,
        }

    def _identify_strengths(
        self,
        chapters: List[Chapter],
        dimension_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """识别书籍的优势"""
        strengths = []

        # 基于维度评分识别优势
        strength_threshold = 80
        for dim, score in dimension_scores.items():
            if score >= strength_threshold:
                dim_names = {
                    "plot_progress": "剧情推进",
                    "character_consistency": "人物一致性",
                    "pacing": "节奏控制",
                    "dialogue_distinction": "对话辨识度",
                    "payoff_delivery": "爽点达成",
                    "ending_hook": "章末钩子",
                    "style_stability": "文风稳定",
                    "continuity": "连续性",
                    "commercial_readability": "商业可读性",
                }
                strengths.append({
                    "dimension": dim,
                    "name": dim_names.get(dim, dim),
                    "score": score,
                    "description": f"该维度表现优秀，平均分达到{score}分",
                })

        # 按分数排序
        strengths.sort(key=lambda x: x["score"], reverse=True)
        return strengths[:5]

    def _identify_weaknesses(
        self,
        chapters: List[Chapter],
        dimension_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """识别书籍的不足"""
        weaknesses = []

        # 基于维度评分识别不足
        weakness_threshold = 65
        for dim, score in dimension_scores.items():
            if score < weakness_threshold:
                dim_names = {
                    "plot_progress": "剧情推进",
                    "character_consistency": "人物一致性",
                    "pacing": "节奏控制",
                    "dialogue_distinction": "对话辨识度",
                    "payoff_delivery": "爽点达成",
                    "ending_hook": "章末钩子",
                    "style_stability": "文风稳定",
                    "continuity": "连续性",
                    "commercial_readability": "商业可读性",
                }
                weaknesses.append({
                    "dimension": dim,
                    "name": dim_names.get(dim, dim),
                    "score": score,
                    "description": f"该维度需要改进，平均分仅{score}分",
                    "suggestion": self._get_improvement_suggestion(dim),
                })

        # 按分数排序
        weaknesses.sort(key=lambda x: x["score"])
        return weaknesses[:5]

    def _get_improvement_suggestion(self, dimension: str) -> str:
        """获取改进建议"""
        suggestions = {
            "plot_progress": "加强主线推进，避免原地踏步",
            "character_consistency": "注意人设稳定，避免OOC",
            "pacing": "优化节奏控制，减少注水段落",
            "dialogue_distinction": "增强对话辨识度，突出角色个性",
            "payoff_delivery": "提升爽点设计，加强情绪回报",
            "ending_hook": "强化章末钩子，增强追更欲望",
            "style_stability": "保持文风一致，避免风格跳跃",
            "continuity": "注意设定连续，避免前后矛盾",
            "commercial_readability": "提升商业可读性，增强吸引力",
        }
        return suggestions.get(dimension, "需要针对性改进")

    def _analyze_patterns(self, chapters: List[Chapter]) -> Dict[str, Any]:
        """分析写作模式"""
        patterns = {
            "score_trend": self._analyze_score_trend(chapters),
            "word_count_pattern": self._analyze_word_count_pattern(chapters),
            "high_score_common": self._analyze_high_score_commonality(chapters),
        }
        return patterns

    def _analyze_score_trend(self, chapters: List[Chapter]) -> Dict[str, Any]:
        """分析分数趋势"""
        scores = [c.total_score or 0 for c in chapters]
        if len(scores) < 3:
            return {"trend": "insufficient_data"}

        # 分段计算平均分
        n = len(scores)
        first_third = sum(scores[:n//3]) / (n//3) if n//3 > 0 else 0
        last_third = sum(scores[-n//3:]) / (n//3) if n//3 > 0 else 0

        if last_third > first_third + 5:
            trend = "improving"
            description = "质量呈上升趋势，后期章节明显优于前期"
        elif last_third < first_third - 5:
            trend = "declining"
            description = "质量呈下降趋势，后期章节不如前期"
        else:
            trend = "stable"
            description = "质量保持稳定，前后水平相当"

        return {
            "trend": trend,
            "description": description,
            "first_third_avg": round(first_third, 2),
            "last_third_avg": round(last_third, 2),
        }

    def _analyze_word_count_pattern(self, chapters: List[Chapter]) -> Dict[str, Any]:
        """分析字数模式"""
        word_counts = [c.word_count or 0 for c in chapters if c.word_count]
        if not word_counts:
            return {"pattern": "no_data"}

        avg = sum(word_counts) / len(word_counts)
        variance = sum((w - avg) ** 2 for w in word_counts) / len(word_counts)
        std = variance ** 0.5

        if std / avg < 0.1:
            pattern = "consistent"
            description = "字数控制稳定，各章长度一致"
        elif std / avg < 0.2:
            pattern = "moderate"
            description = "字数波动适中，有合理的章节长度变化"
        else:
            pattern = "variable"
            description = "字数波动较大，建议加强字数控制"

        return {
            "pattern": pattern,
            "description": description,
            "avg_word_count": round(avg, 0),
            "std": round(std, 0),
        }

    def _analyze_high_score_commonality(self, chapters: List[Chapter]) -> List[Dict[str, Any]]:
        """分析高分章节的共同点"""
        high_score_chapters = [c for c in chapters if (c.total_score or 0) >= 85]

        if len(high_score_chapters) < 3:
            return []

        # 分析高分章节的共同特征
        common_features = []

        # 检查章节位置分布
        indices = [c.chapter_index for c in high_score_chapters]
        early = sum(1 for i in indices if i <= 10)
        middle = sum(1 for i in indices if 10 < i <= 50)
        late = sum(1 for i in indices if i > 50)

        if late > middle and late > early:
            common_features.append({
                "feature": "后期发力",
                "description": f"后期章节质量更高，{late}个高分章节集中在后半部分",
            })
        elif early > middle and early > late:
            common_features.append({
                "feature": "开篇强势",
                "description": f"开篇质量优秀，{early}个高分章节集中在前10章",
            })

        # 检查字数
        avg_words = sum(c.word_count or 0 for c in high_score_chapters) / len(high_score_chapters)
        common_features.append({
            "feature": "最佳字数范围",
            "description": f"高分章节平均字数{avg_words:.0f}字",
        })

        return common_features

    # ========== 技巧卡蒸馏 ==========

    def distill_techniques_from_book(
        self,
        project_id: int,
        min_chapter_score: int = 80,
        create_cards: bool = True
    ) -> Dict[str, Any]:
        """
        从完成的书籍中蒸馏技巧卡

        Args:
            project_id: 项目ID
            min_chapter_score: 最低章节分数（只分析高分章节）
            create_cards: 是否自动创建技巧卡

        Returns:
            蒸馏结果
        """
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        # 获取高分章节
        high_score_chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status == ChapterStatus.COMPLETED,
            Chapter.total_score >= min_chapter_score
        ).order_by(desc(Chapter.total_score)).limit(20).all()

        if not high_score_chapters:
            return {"error": f"没有评分高于{min_chapter_score}的章节"}

        # 获取章节记忆
        chapter_ids = [c.id for c in high_score_chapters]
        chapter_memories = self.db.query(ChapterMemory).filter(
            ChapterMemory.chapter_id.in_(chapter_ids)
        ).all()

        # 分析高分章节的成功因素
        success_factors = self._analyze_success_factors(
            high_score_chapters, chapter_memories
        )

        # 生成候选技巧卡
        candidate_cards = []
        if create_cards:
            for factor in success_factors[:10]:
                card = self._create_technique_card_from_factor(
                    project_id, factor, high_score_chapters
                )
                if card:
                    candidate_cards.append({
                        "id": card.id,
                        "title": card.title,
                        "category": card.category,
                        "confidence": factor.get("confidence", 0),
                    })

        result = {
            "project_id": project_id,
            "project_name": project.name,
            "analyzed_chapters": len(high_score_chapters),
            "success_factors": success_factors,
            "candidate_cards": candidate_cards,
            "created_cards_count": len(candidate_cards),
        }

        logger.info(f"技巧卡蒸馏完成: project_id={project_id}, cards={len(candidate_cards)}")
        return result

    def _analyze_success_factors(
        self,
        chapters: List[Chapter],
        memories: List[ChapterMemory]
    ) -> List[Dict[str, Any]]:
        """分析高分章节的成功因素"""
        factors = []

        # 1. 分析维度评分模式
        dimension_patterns = defaultdict(list)
        for ch in chapters:
            if ch.dimension_scores:
                for dim, score in ch.dimension_scores.items():
                    dimension_patterns[dim].append(score)

        for dim, scores in dimension_patterns.items():
            avg = sum(scores) / len(scores)
            if avg >= 85:
                factors.append({
                    "type": "dimension_strength",
                    "dimension": dim,
                    "name": self._get_dimension_name(dim),
                    "avg_score": round(avg, 2),
                    "confidence": min(avg, 95),
                    "description": f"该维度 consistently 表现优秀，是本书的核心优势",
                })

        # 2. 分析章节记忆中的关键事件
        key_events = []
        for mem in memories:
            if mem.key_events:
                key_events.extend(mem.key_events if isinstance(mem.key_events, list) else [mem.key_events])

        if key_events:
            # 统计高频事件类型
            event_types = defaultdict(int)
            for event in key_events:
                event_type = self._categorize_event(event)
                event_types[event_type] += 1

            for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                factors.append({
                    "type": "event_pattern",
                    "event_type": event_type,
                    "frequency": count,
                    "confidence": min(60 + count * 5, 90),
                    "description": f"'{event_type}'类型的事件出现{count}次，是本书的常用技巧",
                })

        # 3. 分析章节结构模式
        structure_patterns = self._analyze_chapter_structures(chapters)
        factors.extend(structure_patterns)

        # 按置信度排序
        factors.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return factors

    def _get_dimension_name(self, dimension: str) -> str:
        """获取维度中文名"""
        names = {
            "plot_progress": "剧情推进",
            "character_consistency": "人物一致性",
            "pacing": "节奏控制",
            "dialogue_distinction": "对话辨识度",
            "payoff_delivery": "爽点达成",
            "ending_hook": "章末钩子",
            "style_stability": "文风稳定",
            "continuity": "连续性",
            "commercial_readability": "商业可读性",
        }
        return names.get(dimension, dimension)

    def _categorize_event(self, event: str) -> str:
        """对事件进行分类"""
        event_lower = str(event).lower()

        categories = {
            "突破": ["突破", "进阶", "升级", "晋升"],
            "战斗": ["战斗", "对决", "pk", "打斗"],
            "收获": ["获得", "收获", "得到", "发现"],
            "打脸": ["打脸", "装逼", "震惊", "碾压"],
            "情感": ["表白", "心动", "感动", "误会"],
            "揭秘": ["揭秘", "揭晓", "真相", "发现"],
            "危机": ["危机", "危险", "困境", "追杀"],
        }

        for cat, keywords in categories.items():
            for kw in keywords:
                if kw in event_lower:
                    return cat

        return "其他"

    def _analyze_chapter_structures(self, chapters: List[Chapter]) -> List[Dict[str, Any]]:
        """分析章节结构模式"""
        patterns = []

        # 分析章节长度分布
        word_counts = [c.word_count or 0 for c in chapters if c.word_count]
        if word_counts:
            avg = sum(word_counts) / len(word_counts)
            if avg > 3000:
                patterns.append({
                    "type": "structure",
                    "feature": "长章节模式",
                    "avg_words": round(avg, 0),
                    "confidence": 75,
                    "description": f"章节平均字数{avg:.0f}字，属于长章节模式，适合复杂情节展开",
                })
            elif avg < 2000:
                patterns.append({
                    "type": "structure",
                    "feature": "短章节模式",
                    "avg_words": round(avg, 0),
                    "confidence": 75,
                    "description": f"章节平均字数{avg:.0f}字，属于短章节模式，适合快节奏叙事",
                })

        return patterns

    def _create_technique_card_from_factor(
        self,
        project_id: int,
        factor: Dict[str, Any],
        source_chapters: List[Chapter]
    ) -> Optional[TechniqueCard]:
        """从成功因素创建技巧卡"""

        # 根据因素类型生成技巧卡
        if factor["type"] == "dimension_strength":
            return self._create_dimension_technique(factor, source_chapters)
        elif factor["type"] == "event_pattern":
            return self._create_event_technique(factor, source_chapters)
        elif factor["type"] == "structure":
            return self._create_structure_technique(factor, source_chapters)

        return None

    def _create_dimension_technique(
        self,
        factor: Dict[str, Any],
        chapters: List[Chapter]
    ) -> Optional[TechniqueCard]:
        """基于维度优势创建技巧卡"""
        dim = factor.get("dimension", "")

        # 维度到技巧的映射
        dimension_techniques = {
            "plot_progress": {
                "title": "剧情推进法",
                "category": "structure",
                "description": "保持主线清晰推进，每章都有明确的信息增量",
                "principle": "读者需要持续获得新信息来维持阅读兴趣",
            },
            "payoff_delivery": {
                "title": "爽点释放技巧",
                "category": "emotion",
                "description": "精准把控爽点释放时机，确保情绪回报最大化",
                "principle": "爽点的价值取决于铺垫的充分性和释放的时机",
            },
            "ending_hook": {
                "title": "悬念断章法",
                "category": "hook",
                "description": "在章节结尾设置强烈悬念，引发追更欲望",
                "principle": "好奇心是驱动连续阅读的核心动力",
            },
            "dialogue_distinction": {
                "title": "角色对话个性化",
                "category": "character",
                "description": "为每个角色设计独特的语言风格和说话方式",
                "principle": "独特的对话风格是塑造角色个性的有效手段",
            },
        }

        if dim not in dimension_techniques:
            return None

        tech = dimension_techniques[dim]

        card = TechniqueCard(
            title=tech["title"],
            category=tech["category"],
            description=tech["description"],
            principle=tech["principle"],
            confidence_score=factor.get("confidence", 70),
            source_chapters=[c.chapter_index for c in chapters[:5]],
            applicable_genres=[],
            is_active=1,
        )

        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)

        return card

    def _create_event_technique(
        self,
        factor: Dict[str, Any],
        chapters: List[Chapter]
    ) -> Optional[TechniqueCard]:
        """基于事件模式创建技巧卡"""
        event_type = factor.get("event_type", "")

        event_techniques = {
            "突破": {
                "title": "升级突破描写法",
                "category": "commercial",
                "description": "详细描写突破过程，强化升级爽感",
                "principle": "升级过程的描写比结果更能激发读者爽感",
            },
            "战斗": {
                "title": "战斗节奏控制",
                "category": "pacing",
                "description": "控制战斗场景的节奏，张弛有度",
                "principle": "好的战斗戏需要紧张与喘息交替",
            },
            "收获": {
                "title": "宝物获得描写",
                "category": "commercial",
                "description": "渲染获得宝物/机缘时的情绪，放大满足感",
                "principle": "获得过程的期待感能放大最终收获的满足",
            },
            "打脸": {
                "title": "反差打脸技巧",
                "category": "commercial",
                "description": "通过前后反差制造打脸爽点",
                "principle": "打脸的效果来自于预期与结果的强烈反差",
            },
        }

        if event_type not in event_techniques:
            return None

        tech = event_techniques[event_type]

        card = TechniqueCard(
            title=tech["title"],
            category=tech["category"],
            description=tech["description"],
            principle=tech["principle"],
            confidence_score=factor.get("confidence", 70),
            source_chapters=[c.chapter_index for c in chapters[:5]],
            applicable_genres=[],
            is_active=1,
        )

        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)

        return card

    def _create_structure_technique(
        self,
        factor: Dict[str, Any],
        chapters: List[Chapter]
    ) -> Optional[TechniqueCard]:
        """基于结构模式创建技巧卡"""
        feature = factor.get("feature", "")

        if "长章节" in feature:
            card = TechniqueCard(
                title="长章节叙事法",
                category="structure",
                description=f"采用{factor.get('avg_words', 3000):.0f}字左右的长章节，充分展开复杂情节",
                principle="长章节适合多线并进、复杂冲突的展开",
                confidence_score=factor.get("confidence", 70),
                source_chapters=[c.chapter_index for c in chapters[:5]],
                applicable_genres=[],
                is_active=1,
            )
        elif "短章节" in feature:
            card = TechniqueCard(
                title="短章节快读法",
                category="structure",
                description=f"采用{factor.get('avg_words', 1500):.0f}字左右的短章节，保持阅读节奏",
                principle="短章节适合快节奏叙事，降低阅读压力",
                confidence_score=factor.get("confidence", 70),
                source_chapters=[c.chapter_index for c in chapters[:5]],
                applicable_genres=[],
                is_active=1,
            )
        else:
            return None

        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)

        return card

    # ========== 技巧库更新 ==========

    def update_technique_library(
        self,
        project_id: int,
        min_usage_count: int = 3
    ) -> Dict[str, Any]:
        """
        基于项目经验更新技巧库

        Args:
            project_id: 项目ID
            min_usage_count: 最低使用次数才考虑更新

        Returns:
            更新结果
        """
        # 获取项目中使用的技巧卡及其效果
        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status == ChapterStatus.COMPLETED
        ).all()

        # 统计技巧卡效果
        skill_effectiveness = defaultdict(lambda: {"count": 0, "total_score": 0})

        for ch in chapters:
            used_skills = ch.metadata.get("used_skills", []) if ch.metadata else []
            for skill_id in used_skills:
                skill_effectiveness[skill_id]["count"] += 1
                skill_effectiveness[skill_id]["total_score"] += (ch.total_score or 0)

        # 更新技巧卡效果评分
        updated_cards = []
        for skill_id, stats in skill_effectiveness.items():
            if stats["count"] >= min_usage_count:
                card = self.db.query(TechniqueCard).filter(
                    TechniqueCard.id == skill_id
                ).first()

                if card:
                    # 计算新的效果评分
                    avg_score = stats["total_score"] / stats["count"]

                    # 指数移动平均更新
                    alpha = 0.3
                    if card.effectiveness_score == 0:
                        new_score = avg_score
                    else:
                        new_score = card.effectiveness_score * (1 - alpha) + avg_score * alpha

                    card.effectiveness_score = round(new_score, 2)
                    card.usage_count = (card.usage_count or 0) + stats["count"]

                    updated_cards.append({
                        "id": card.id,
                        "title": card.title,
                        "new_score": card.effectiveness_score,
                        "usage_count": card.usage_count,
                    })

        self.db.commit()

        result = {
            "updated_cards": updated_cards,
            "updated_count": len(updated_cards),
        }

        logger.info(f"技巧库更新完成: project_id={project_id}, updated={len(updated_cards)}")
        return result
