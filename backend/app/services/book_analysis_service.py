"""
Book Analysis Service - 书籍分析服务
分析参考书籍，提取结构指纹和爽点曲线
"""

import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.book_analysis import BookAnalysisProfile, ProjectStyleProfile
from app.models.book import Book
from app.models.project import Project

logger = logging.getLogger(__name__)


class BookAnalysisService:
    """书籍分析服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== Book Analysis Profile ==========

    def create_analysis_profile(
        self,
        book_id: int,
        total_chapters: int = 0,
        total_words: int = 0,
        avg_chapter_words: float = 3000.0,
        chapter_word_std: float = 500.0,
        hook_rate: float = 0.7,
        cliffhanger_rate: float = 0.3,
        payoff_cadence_chapters: float = 5.0,
        emotion_curve: dict = None,
        pacing_rules: dict = None,
        character_arc_patterns: list = None,
        plot_structure: dict = None,
        satisfaction_peaks: list = None,
    ) -> BookAnalysisProfile:
        """创建书籍分析档案"""
        profile = BookAnalysisProfile(
            book_id=book_id,
            total_chapters=total_chapters,
            total_words=total_words,
            avg_chapter_words=avg_chapter_words,
            chapter_word_std=chapter_word_std,
            hook_rate=hook_rate,
            cliffhanger_rate=cliffhanger_rate,
            payoff_cadence_chapters=payoff_cadence_chapters,
            emotion_curve=emotion_curve or {
                "baseline": 5.0,
                "peak_intensity": 8.0,
                "valley_depth": 3.0,
                "rhythm": "wave",
            },
            pacing_rules=pacing_rules or {
                "opening_pace": "medium",
                "rising_action_ratio": 0.4,
                "climax_density": "high",
                "resolution_brevity": "concise",
            },
            character_arc_patterns=character_arc_patterns or [],
            plot_structure=plot_structure or {
                "act_structure": "three_act",
                "turning_points_per_volume": 3,
            },
            satisfaction_peaks=satisfaction_peaks or [],
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"创建书籍分析档案: book_id={book_id}")
        return profile

    def get_analysis_profile(self, book_id: int) -> Optional[BookAnalysisProfile]:
        """获取书籍分析档案"""
        return (
            self.db.query(BookAnalysisProfile)
            .filter(BookAnalysisProfile.book_id == book_id)
            .first()
        )

    def update_analysis_profile(
        self,
        profile_id: int,
        **kwargs
    ) -> Optional[BookAnalysisProfile]:
        """更新书籍分析档案"""
        profile = (
            self.db.query(BookAnalysisProfile)
            .filter(BookAnalysisProfile.id == profile_id)
            .first()
        )
        if not profile:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"更新书籍分析档案: id={profile_id}")
        return profile

    def analyze_book_structure(
        self,
        book_id: int,
        sample_chapters: List[Dict[str, Any]] = None
    ) -> BookAnalysisProfile:
        """
        分析书籍结构，生成结构指纹

        Args:
            book_id: 书籍ID
            sample_chapters: 样章数据列表，每项包含 {
                "chapter_index": int,
                "word_count": int,
                "has_hook": bool,
                "is_cliffhanger": bool,
                "emotion_intensity": float,
                "satisfaction_score": float,
            }
        """
        # 获取或创建分析档案
        profile = self.get_analysis_profile(book_id)
        if not profile:
            book = self.db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise ValueError(f"书籍不存在: {book_id}")
            profile = self.create_analysis_profile(book_id=book_id)

        if not sample_chapters:
            logger.warning(f"没有提供样章数据，使用默认结构: book_id={book_id}")
            return profile

        # 计算统计数据
        word_counts = [ch.get("word_count", 3000) for ch in sample_chapters]
        hooks = [ch for ch in sample_chapters if ch.get("has_hook", False)]
        cliffhangers = [ch for ch in sample_chapters if ch.get("is_cliffhanger", False)]
        satisfactions = [ch.get("satisfaction_score", 5.0) for ch in sample_chapters if ch.get("satisfaction_score")]
        emotions = [ch.get("emotion_intensity", 5.0) for ch in sample_chapters if ch.get("emotion_intensity")]

        # 计算爽点峰值位置
        satisfaction_peaks = []
        if satisfactions:
            avg_sat = sum(satisfactions) / len(satisfactions)
            for i, ch in enumerate(sample_chapters):
                sat = ch.get("satisfaction_score", 0)
                if sat > avg_sat * 1.3:  # 高于平均30%视为峰值
                    satisfaction_peaks.append({
                        "chapter_index": ch.get("chapter_index", i),
                        "intensity": sat,
                        "type": "satisfaction_peak",
                    })

        # 更新分析数据
        profile.total_chapters = len(sample_chapters)
        profile.total_words = sum(word_counts)
        profile.avg_chapter_words = sum(word_counts) / len(word_counts) if word_counts else 3000
        profile.chapter_word_std = self._calculate_std(word_counts) if len(word_counts) > 1 else 500
        profile.hook_rate = len(hooks) / len(sample_chapters) if sample_chapters else 0.7
        profile.cliffhanger_rate = len(cliffhangers) / len(sample_chapters) if sample_chapters else 0.3
        profile.payoff_cadence_chapters = self._calculate_payoff_cadence(satisfaction_peaks)
        profile.satisfaction_peaks = satisfaction_peaks

        # 计算情绪曲线
        if emotions:
            profile.emotion_curve = {
                "baseline": sum(emotions) / len(emotions),
                "peak_intensity": max(emotions),
                "valley_depth": min(emotions),
                "rhythm": self._detect_rhythm_pattern(emotions),
            }

        # 计算节奏规则
        if sample_chapters:
            profile.pacing_rules = self._infer_pacing_rules(sample_chapters)

        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"完成书籍结构分析: book_id={book_id}, 章节数={len(sample_chapters)}")
        return profile

    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _calculate_payoff_cadence(self, peaks: List[Dict]) -> float:
        """计算爽点间隔"""
        if len(peaks) < 2:
            return 5.0
        intervals = [
            peaks[i]["chapter_index"] - peaks[i-1]["chapter_index"]
            for i in range(1, len(peaks))
        ]
        return sum(intervals) / len(intervals) if intervals else 5.0

    def _detect_rhythm_pattern(self, emotions: List[float]) -> str:
        """检测情绪节奏模式"""
        if len(emotions) < 3:
            return "wave"
        # 简单的模式检测
        peaks = sum(1 for i in range(1, len(emotions)-1)
                   if emotions[i] > emotions[i-1] and emotions[i] > emotions[i+1])
        if peaks > len(emotions) * 0.4:
            return "intense"
        elif peaks < len(emotions) * 0.2:
            return "calm"
        return "wave"

    def _infer_pacing_rules(self, chapters: List[Dict]) -> Dict:
        """推断节奏规则"""
        first_third = chapters[:len(chapters)//3]
        last_third = chapters[-len(chapters)//3:]

        first_word_counts = [ch.get("word_count", 3000) for ch in first_third]
        last_word_counts = [ch.get("word_count", 3000) for ch in last_third]

        avg_first = sum(first_word_counts) / len(first_word_counts) if first_word_counts else 3000
        avg_last = sum(last_word_counts) / len(last_word_counts) if last_word_counts else 3000

        return {
            "opening_pace": "fast" if avg_first < 2500 else "medium" if avg_first < 3500 else "slow",
            "rising_action_ratio": 0.4,
            "climax_density": "high" if avg_last > avg_first * 1.2 else "medium",
            "resolution_brevity": "concise" if avg_last < 2000 else "detailed",
        }

    # ========== Project Style Profile ==========

    def create_style_profile(
        self,
        project_id: int,
        profile_name: str = "默认风格",
        book_analysis_id: int = None,
        derived_rules: dict = None,
        enabled: bool = True,
    ) -> ProjectStyleProfile:
        """创建项目风格档案"""
        profile = ProjectStyleProfile(
            project_id=project_id,
            profile_name=profile_name,
            book_analysis_id=book_analysis_id,
            derived_rules=derived_rules or {},
            enabled=enabled,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"创建项目风格档案: project_id={project_id}, name={profile_name}")
        return profile

    def get_project_style_profiles(
        self,
        project_id: int,
        enabled_only: bool = True
    ) -> List[ProjectStyleProfile]:
        """获取项目的风格档案列表"""
        query = self.db.query(ProjectStyleProfile).filter(
            ProjectStyleProfile.project_id == project_id
        )
        if enabled_only:
            query = query.filter(ProjectStyleProfile.enabled == True)
        return query.order_by(desc(ProjectStyleProfile.created_at)).all()

    def get_active_style_profile(self, project_id: int) -> Optional[ProjectStyleProfile]:
        """获取项目当前启用的风格档案"""
        profiles = self.get_project_style_profiles(project_id, enabled_only=True)
        return profiles[0] if profiles else None

    def apply_book_analysis_to_project(
        self,
        book_analysis_id: int,
        project_id: int,
        customization: dict = None
    ) -> ProjectStyleProfile:
        """
        将书籍分析应用到项目，生成风格档案

        Args:
            book_analysis_id: 书籍分析档案ID
            project_id: 项目ID
            customization: 自定义覆盖规则
        """
        book_analysis = (
            self.db.query(BookAnalysisProfile)
            .filter(BookAnalysisProfile.id == book_analysis_id)
            .first()
        )
        if not book_analysis:
            raise ValueError(f"书籍分析档案不存在: {book_analysis_id}")

        # 生成派生规则
        derived_rules = self._generate_derived_rules(book_analysis, customization)

        # 检查是否已存在该分析档案的应用
        existing = (
            self.db.query(ProjectStyleProfile)
            .filter(
                ProjectStyleProfile.project_id == project_id,
                ProjectStyleProfile.book_analysis_id == book_analysis_id,
            )
            .first()
        )

        if existing:
            existing.derived_rules = derived_rules
            existing.enabled = True
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"更新项目风格档案: project_id={project_id}, analysis_id={book_analysis_id}")
            return existing

        # 禁用其他档案
        self.db.query(ProjectStyleProfile).filter(
            ProjectStyleProfile.project_id == project_id
        ).update({"enabled": False})

        # 创建新档案
        profile = self.create_style_profile(
            project_id=project_id,
            profile_name=f"基于《{book_analysis.book.title if book_analysis.book else '未知书籍'}》的风格",
            book_analysis_id=book_analysis_id,
            derived_rules=derived_rules,
            enabled=True,
        )

        logger.info(f"应用书籍分析到项目: project_id={project_id}, analysis_id={book_analysis_id}")
        return profile

    def _generate_derived_rules(
        self,
        book_analysis: BookAnalysisProfile,
        customization: dict = None
    ) -> Dict[str, Any]:
        """生成派生写作规则"""
        customization = customization or {}

        rules = {
            # 字数控制
            "target_chapter_words": {
                "min": int(book_analysis.avg_chapter_words * 0.8),
                "optimal": int(book_analysis.avg_chapter_words),
                "max": int(book_analysis.avg_chapter_words * 1.2),
            },
            # Hook规则
            "hook_requirements": {
                "opening_hook": True,
                "hook_intensity": "strong" if book_analysis.hook_rate > 0.8 else "moderate",
                "hook_types": ["冲突", "悬念", "反常"],
            },
            # 断章规则
            "cliffhanger_rules": {
                "frequency": book_analysis.cliffhanger_rate,
                "trigger_chapters": self._generate_cliffhanger_triggers(
                    book_analysis.payoff_cadence_chapters,
                    book_analysis.satisfaction_peaks
                ),
            },
            # 爽点曲线
            "satisfaction_curve": {
                "cadence": book_analysis.payoff_cadence_chapters,
                "peak_intensity": book_analysis.emotion_curve.get("peak_intensity", 8.0),
                "buildup_chapters": max(2, int(book_analysis.payoff_cadence_chapters * 0.6)),
            },
            # 节奏模板
            "pacing_template": book_analysis.pacing_rules,
            # 情绪曲线
            "emotion_guidelines": {
                "baseline": book_analysis.emotion_curve.get("baseline", 5.0),
                "variation_range": [
                    book_analysis.emotion_curve.get("valley_depth", 3.0),
                    book_analysis.emotion_curve.get("peak_intensity", 8.0),
                ],
                "rhythm": book_analysis.emotion_curve.get("rhythm", "wave"),
            },
        }

        # 应用自定义覆盖
        if customization:
            self._deep_merge(rules, customization)

        return rules

    def _generate_cliffhanger_triggers(
        self,
        payoff_cadence: float,
        satisfaction_peaks: List[Dict]
    ) -> List[int]:
        """生成断章触发章节"""
        if satisfaction_peaks:
            return [p["chapter_index"] for p in satisfaction_peaks]
        # 默认每N章一个断章
        return list(range(int(payoff_cadence), 1000, int(payoff_cadence)))

    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def update_style_profile(
        self,
        profile_id: int,
        **kwargs
    ) -> Optional[ProjectStyleProfile]:
        """更新项目风格档案"""
        profile = (
            self.db.query(ProjectStyleProfile)
            .filter(ProjectStyleProfile.id == profile_id)
            .first()
        )
        if not profile:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"更新风格档案: id={profile_id}")
        return profile

    def disable_style_profile(self, profile_id: int) -> bool:
        """禁用风格档案"""
        profile = (
            self.db.query(ProjectStyleProfile)
            .filter(ProjectStyleProfile.id == profile_id)
            .first()
        )
        if not profile:
            return False

        profile.enabled = False
        self.db.commit()
        logger.info(f"禁用风格档案: id={profile_id}")
        return True

    def delete_style_profile(self, profile_id: int) -> bool:
        """删除风格档案"""
        profile = (
            self.db.query(ProjectStyleProfile)
            .filter(ProjectStyleProfile.id == profile_id)
            .first()
        )
        if not profile:
            return False

        self.db.delete(profile)
        self.db.commit()
        logger.info(f"删除风格档案: id={profile_id}")
        return True

    # ========== 风格注入辅助方法 ==========

    def get_style_injection_context(self, project_id: int) -> Dict[str, Any]:
        """
        获取用于注入到写作流程的风格上下文

        Returns:
            包含风格规则的字典，可直接用于prompt模板
        """
        profile = self.get_active_style_profile(project_id)
        if not profile:
            return {}

        rules = profile.derived_rules or {}

        return {
            "has_style_profile": True,
            "profile_name": profile.profile_name,
            "target_words": rules.get("target_chapter_words", {}),
            "hook_rules": rules.get("hook_requirements", {}),
            "cliffhanger_rules": rules.get("cliffhanger_rules", {}),
            "satisfaction_curve": rules.get("satisfaction_curve", {}),
            "pacing_template": rules.get("pacing_template", {}),
            "emotion_guidelines": rules.get("emotion_guidelines", {}),
        }
