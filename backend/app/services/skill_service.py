"""
Skill Service - 技巧卡选择与效果追踪
P4 Phase 2: 技巧库分类与调用
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.technique import TechniqueCard, BookProfile
from app.models.chapter import Chapter

logger = logging.getLogger(__name__)


# 技巧分类体系定义
SKILL_TAXONOMY = {
    "structure": {
        "name": "结构技巧",
        "subcategories": ["three_act", "five_act", "hero_journey", "parallel_plots", "nested_structure"]
    },
    "character": {
        "name": "人物技巧",
        "subcategories": ["character_arc", "inner_conflict", "growth_moment", "reveal_secret", "transformation"]
    },
    "pacing": {
        "name": "节奏技巧",
        "subcategories": ["pressure_response_goal", "action_reaction", "tension_release", "cliffhanger_cycle", "rhythm_control"]
    },
    "hook": {
        "name": "钩子技巧",
        "subcategories": ["opening_hook", "chapter_end_hook", "mystery_hook", "danger_hook", "reward_hook", "identity_hook"]
    },
    "emotion": {
        "name": "情绪技巧",
        "subcategories": ["humiliation_payoff", "revenge_satisfaction", "romantic_tension", "fear_relief", "loss_recovery", "anticipation_building"]
    },
    "style": {
        "name": "文风技巧",
        "subcategories": ["voice_consistency", "description_balance", "dialogue_style", "narrative_distance", "language_rhythm"]
    },
    "readability": {
        "name": "可读性技巧",
        "subcategories": ["paragraph_length", "sentence_variety", "transitions", "white_space", "flow_control"]
    },
    "commercial": {
        "name": "商业爽点技巧",
        "subcategories": ["face_slapping", "power_display", "underdog_comeback", "treasure_acquisition", "level_up_moment", "harem_interaction"]
    },
    "foreshadow": {
        "name": "伏笔技巧",
        "subcategories": ["item_foreshadow", "dialogue_foreshadow", "prophecy_foreshadow", "character_secret", "world_rule_hint", "emotional_payoff_setup"]
    },
    "dialogue": {
        "name": "对话技巧",
        "subcategories": ["subtext", "conflict_dialogue", "character_voice", " exposition_dialogue", "witty_exchange"]
    },
    "worldbuilding": {
        "name": "世界观技巧",
        "subcategories": ["rule_establishment", "cultural_detail", "history_weaving", "magic_system", "power_structure"]
    },
    "scene": {
        "name": "场景技巧",
        "subcategories": ["opening_scene", "action_scene", "emotional_scene", "transition_scene", "climax_scene"]
    },
    "conflict": {
        "name": "冲突技巧",
        "subcategories": ["man_vs_man", "man_vs_self", "man_vs_society", "man_vs_nature", "escalation", "resolution"]
    },
    "romance": {
        "name": "感情线技巧",
        "subcategories": ["slow_burn", "love_triangle", "misunderstanding", "reunion", "mutual_growth"]
    },
}


class SkillSelectionService:
    """技巧卡选择服务"""

    def __init__(self, db: Session):
        self.db = db

    def classify_skill(
        self,
        technique_id: int,
        taxonomy_level_1: str,
        taxonomy_level_2: str = None,
        scene_stage: str = None
    ) -> Optional[TechniqueCard]:
        """
        为技巧卡打分类标签
        """
        card = self.db.query(TechniqueCard).filter(
            TechniqueCard.id == technique_id
        ).first()

        if not card:
            return None

        card.taxonomy_level_1 = taxonomy_level_1
        if taxonomy_level_2:
            card.taxonomy_level_2 = taxonomy_level_2
        if scene_stage:
            card.scene_stage = scene_stage

        self.db.commit()
        self.db.refresh(card)
        logger.info(f"[Skill] 技巧卡 {card.id} 分类: {taxonomy_level_1}/{taxonomy_level_2}")
        return card

    def auto_classify_skills(self, technique_ids: List[int] = None) -> Dict[str, Any]:
        """
        自动分类技巧卡（基于关键词匹配）
        """
        query = self.db.query(TechniqueCard).filter(
            TechniqueCard.taxonomy_level_1.is_(None)
        )

        if technique_ids:
            query = query.filter(TechniqueCard.id.in_(technique_ids))

        cards = query.all()
        classified = 0

        keywords_map = {
            "hook": ["钩子", "开头", "结尾", "悬念", "吸引"],
            "pacing": ["节奏", "紧张", "放松", "压力", "释放"],
            "emotion": ["情绪", "爽点", "虐", "感动", "愤怒", "喜悦"],
            "character": ["人物", "性格", "成长", "转变", "内心"],
            "foreshadow": ["伏笔", "铺垫", "暗示", "回收", "呼应"],
            "conflict": ["冲突", "矛盾", "对抗", "斗争"],
            "dialogue": ["对话", "台词", "语言"],
            "scene": ["场景", "描写", "环境", "氛围"],
            "commercial": ["爽", "打脸", "装逼", "收获", "升级"],
        }

        for card in cards:
            text = f"{card.title} {card.description or ''} {card.observation or ''}"

            for tax_level_1, keywords in keywords_map.items():
                for kw in keywords:
                    if kw in text:
                        card.taxonomy_level_1 = tax_level_1
                        classified += 1
                        break
                if card.taxonomy_level_1:
                    break

            # 如果没有匹配，设为通用
            if not card.taxonomy_level_1:
                card.taxonomy_level_1 = "structure"

        self.db.commit()
        return {"classified": classified, "total": len(cards)}

    def select_skills_for_chapter(
        self,
        project_id: int,
        chapter_index: int,
        genre: str = None,
        scene_stage: str = None,
        needed_emotion: str = None,
        conflict_type: str = None,
        max_skills: int = 5
    ) -> List[Dict[str, Any]]:
        """
        为章节选择最相关的技巧卡

        输入:
        - project_id: 项目ID
        - chapter_index: 章节序号
        - genre: 题材
        - scene_stage: 场景阶段
        - needed_emotion: 需要的情绪效果
        - conflict_type: 冲突类型
        - max_skills: 最大返回数量

        输出:
        - 3-8张最相关的技巧卡
        """
        query = self.db.query(TechniqueCard).filter(
            TechniqueCard.is_active == 1
        )

        # 根据章节阶段筛选
        if chapter_index <= 3:
            # 开篇优先钩子、结构
            priority_categories = ["hook", "structure", "pacing"]
        elif chapter_index <= 10:
            # 前期优先人物、冲突
            priority_categories = ["character", "conflict", "hook"]
        elif chapter_index % 10 == 0:
            # 每10章的高潮
            priority_categories = ["commercial", "emotion", "conflict"]
        else:
            # 常规章节
            priority_categories = ["pacing", "emotion", "character", "foreshadow"]

        # 如果有场景阶段，进一步筛选
        if scene_stage:
            stage_category_map = {
                "opening": ["hook", "structure"],
                "climax": ["commercial", "emotion", "conflict"],
                "ending": ["hook", "emotion"],
                "daily_scene": ["character", "dialogue", "worldbuilding"],
                "transition": ["pacing", "foreshadow"],
            }
            if scene_stage in stage_category_map:
                priority_categories = stage_category_map[scene_stage]

        # 构建查询
        # 优先匹配分类
        cards = query.filter(
            TechniqueCard.taxonomy_level_1.in_(priority_categories)
        ).order_by(
            desc(TechniqueCard.effectiveness_score),
            desc(TechniqueCard.confidence_score)
        ).limit(max_skills * 2).all()

        # 如果没有足够结果，补充其他高效果卡片
        if len(cards) < max_skills:
            existing_ids = [c.id for c in cards]
            additional = self.db.query(TechniqueCard).filter(
                TechniqueCard.is_active == 1,
                ~TechniqueCard.id.in_(existing_ids) if existing_ids else True
            ).order_by(
                desc(TechniqueCard.effectiveness_score)
            ).limit(max_skills - len(cards)).all()
            cards.extend(additional)

        # 格式化输出
        result = []
        for card in cards[:max_skills]:
            result.append({
                "id": card.id,
                "title": card.title,
                "category": card.category,
                "taxonomy_level_1": card.taxonomy_level_1,
                "taxonomy_level_2": card.taxonomy_level_2,
                "scene_stage": card.scene_stage,
                "principle": card.principle,
                "usage_instruction": card.usage_instruction,
                "anti_pattern": card.anti_pattern,
                "prevention_rule": card.prevention_rule,
                "prompt_instruction": card.prompt_instruction,
                "effectiveness_score": card.effectiveness_score,
                "risk_level": card.risk_level,
                "difficulty": card.difficulty,
            })

        return result

    def format_skills_for_prompt(self, skills: List[Dict]) -> str:
        """
        将选中的技巧卡格式化为Prompt指令
        """
        if not skills:
            return "（本章无特定技巧要求，使用通用写作原则）"

        sections = ["## 本章必须使用的写作技巧\n"]

        for i, skill in enumerate(skills, 1):
            sections.append(f"\n### 技巧 {i}: {skill['title']}")
            sections.append(f"**分类**: {skill['taxonomy_level_1']}/{skill.get('taxonomy_level_2', 'general')}")

            if skill.get('principle'):
                sections.append(f"**原理**: {skill['principle'][:100]}...")

            if skill.get('usage_instruction'):
                sections.append(f"**使用指令**: {skill['usage_instruction']}")

            if skill.get('prompt_instruction'):
                sections.append(f"**Prompt**: {skill['prompt_instruction']}")

            if skill.get('anti_pattern'):
                sections.append(f"**禁用反模式**: {skill['anti_pattern']}")

            if skill.get('prevention_rule'):
                sections.append(f"**预防措施**: {skill['prevention_rule']}")

            if skill.get('risk_level', 0) > 3:
                sections.append(f"**⚠️ 高风险**: 使用此技巧需谨慎")

        return "\n".join(sections)

    def update_skill_feedback(
        self,
        technique_id: int,
        chapter_id: int,
        was_successful: bool,
        score: float = None,
        note: str = None
    ) -> Optional[TechniqueCard]:
        """
        更新技巧卡效果反馈

        章节评审完成后调用
        """
        card = self.db.query(TechniqueCard).filter(
            TechniqueCard.id == technique_id
        ).first()

        if not card:
            return None

        # 更新使用记录
        used_chapters = card.used_in_chapters or []
        if chapter_id not in used_chapters:
            used_chapters.append(chapter_id)
            card.used_in_chapters = used_chapters

        # 更新效果统计
        if was_successful:
            card.positive_review_count += 1
        else:
            card.negative_review_count += 1

        # 重新计算效果评分
        total = card.positive_review_count + card.negative_review_count
        if total > 0:
            card.effectiveness_score = card.positive_review_count / total * 100

        # 更新成功率
        if score is not None:
            # 指数移动平均
            alpha = 0.3
            if card.success_rate == 0:
                card.success_rate = score
            else:
                card.success_rate = card.success_rate * (1 - alpha) + score * alpha

        card.usage_count = len(used_chapters)
        self.db.commit()
        self.db.refresh(card)

        logger.info(f"[Skill] 技巧 {card.id} 反馈更新: effective={was_successful}, score={card.effectiveness_score:.1f}")
        return card

    def get_skills_by_taxonomy(
        self,
        taxonomy_level_1: str = None,
        taxonomy_level_2: str = None,
        min_effectiveness: float = 0.0
    ) -> List[TechniqueCard]:
        """
        按分类获取技巧卡
        """
        query = self.db.query(TechniqueCard).filter(
            TechniqueCard.is_active == 1,
            TechniqueCard.effectiveness_score >= min_effectiveness
        )

        if taxonomy_level_1:
            query = query.filter(TechniqueCard.taxonomy_level_1 == taxonomy_level_1)
        if taxonomy_level_2:
            query = query.filter(TechniqueCard.taxonomy_level_2 == taxonomy_level_2)

        return query.order_by(desc(TechniqueCard.effectiveness_score)).all()

    def get_taxonomy_stats(self) -> Dict[str, Any]:
        """
        获取技巧分类统计
        """
        stats = {}

        for tax_key, tax_info in SKILL_TAXONOMY.items():
            count = self.db.query(TechniqueCard).filter(
                TechniqueCard.taxonomy_level_1 == tax_key
            ).count()

            avg_effectiveness = self.db.query(func.avg(TechniqueCard.effectiveness_score)).filter(
                TechniqueCard.taxonomy_level_1 == tax_key
            ).scalar() or 0

            stats[tax_key] = {
                "name": tax_info["name"],
                "count": count,
                "avg_effectiveness": round(avg_effectiveness, 2),
                "subcategories": tax_info["subcategories"]
            }

        return stats

    def suggest_skills_for_book(
        self,
        book_id: int,
        book_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        为书籍推荐可学习的技巧
        """
        # 根据书籍类型推荐
        type_skill_map = {
            "玄幻": ["commercial", "worldbuilding", "foreshadow"],
            "都市": ["character", "dialogue", "emotion"],
            "悬疑": ["hook", "foreshadow", "pacing"],
            "恋爱": ["romance", "emotion", "character"],
            "爽文": ["commercial", "hook", "pacing"],
        }

        categories = type_skill_map.get(book_type, ["structure", "character", "pacing"])

        suggestions = []
        for category in categories:
            cards = self.db.query(TechniqueCard).filter(
                TechniqueCard.taxonomy_level_1 == category,
                TechniqueCard.effectiveness_score >= 70
            ).order_by(desc(TechniqueCard.effectiveness_score)).limit(3).all()

            for card in cards:
                suggestions.append({
                    "id": card.id,
                    "title": card.title,
                    "category": category,
                    "effectiveness": card.effectiveness_score,
                    "reason": f"适合{book_type}类型的{SKILL_TAXONOMY.get(category, {}).get('name', category)}技巧"
                })

        return suggestions


# ========== Book Profile Service ==========

class BookProfileService:
    """书籍档案服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_or_update_profile(
        self,
        book_id: int,
        genre: str = None,
        sub_genre: str = None,
        audience: str = None,
        style_tags: List[str] = None,
        narrative_pov: str = None,
        pacing_type: str = None,
        commercial_density: int = 5,
        adult_level: int = 0,
        strengths: List[str] = None,
        weaknesses: List[str] = None
    ) -> BookProfile:
        """
        创建或更新书籍档案
        """
        profile = self.db.query(BookProfile).filter(
            BookProfile.book_id == book_id
        ).first()

        if not profile:
            profile = BookProfile(book_id=book_id)
            self.db.add(profile)

        if genre:
            profile.genre = genre
        if sub_genre:
            profile.sub_genre = sub_genre
        if audience:
            profile.audience = audience
        if style_tags:
            profile.style_tags = style_tags
        if narrative_pov:
            profile.narrative_pov = narrative_pov
        if pacing_type:
            profile.pacing_type = pacing_type
        if commercial_density is not None:
            profile.commercial_density = commercial_density
        if adult_level is not None:
            profile.adult_level = adult_level
        if strengths:
            profile.strengths = strengths
        if weaknesses:
            profile.weaknesses = weaknesses

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def analyze_reusable_skills(self, book_id: int) -> List[str]:
        """
        分析书籍中可复用的技巧分类
        """
        # 获取书籍的技巧卡
        from app.models.technique import TechniqueCard

        cards = self.db.query(TechniqueCard).filter(
            TechniqueCard.book_id == book_id,
            TechniqueCard.effectiveness_score >= 60
        ).all()

        # 统计分类
        category_counts = {}
        for card in cards:
            cat = card.taxonomy_level_1 or card.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # 返回高频分类
        sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, count in sorted_cats[:5]]

    def get_profile(self, book_id: int) -> Optional[BookProfile]:
        """获取书籍档案"""
        return self.db.query(BookProfile).filter(
            BookProfile.book_id == book_id
        ).first()
