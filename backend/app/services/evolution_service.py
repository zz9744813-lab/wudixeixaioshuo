"""
Evolution Service - Darwin 进化引擎
自我进化机制：学习反馈 → 改进提示词 → 测试效果 → 保留/回滚
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.evolution import (
    Evolution,
    EvolutionStatus,
    PromptVersion,
    TestResult
)
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)


class EvolutionStrategy(str, Enum):
    """进化策略"""
    AUTO = "auto"           # 自动选择
    CONSERVATIVE = "conservative"  # 保守改进
    AGGRESSIVE = "aggressive"      # 激进改进
    TARGETED = "targeted"         # 针对性改进


class EvolutionService:
    """
    Darwin 进化服务

    核心流程：
    1. 收集反馈 → 识别问题模式
    2. 生成改进方案 → 修改提示词
    3. A/B 测试 → 对比新旧版本
    4. 评估结果 → 保留或回滚
    5. 记录经验 → 更新知识库
    """

    def __init__(self, db: Session):
        self.db = db
        self.improvement_history = []

    def create_evolution_round(
        self,
        project_id: int,
        target_dimension: str,
        strategy: EvolutionStrategy = EvolutionStrategy.AUTO,
        prompt_type: str = "writing"  # writing, planning, critique, etc.
    ) -> Evolution:
        """
        创建新的进化轮次

        Args:
            project_id: 项目ID
            target_dimension: 目标改进维度 (plot, character, pacing, etc.)
            strategy: 进化策略
            prompt_type: 提示词类型
        """
        evolution = Evolution(
            project_id=project_id,
            target_dimension=target_dimension,
            strategy=strategy.value,
            prompt_type=prompt_type,
            status=EvolutionStatus.EVALUATING,
            hypothesis=f"改进 {target_dimension} 维度的生成质量",
            metadata={
                "created_at": datetime.now().isoformat(),
                "feedback_collected": [],
            }
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
        """
        收集相关反馈用于进化分析

        Args:
            evolution_id: 进化轮次ID
            min_feedback_count: 最小反馈数量
        """
        evolution = self.db.query(Evolution).filter(
            Evolution.id == evolution_id
        ).first()

        if not evolution:
            return []

        # 获取目标维度的相关反馈
        feedbacks = self.db.query(Feedback).filter(
            Feedback.project_id == evolution.project_id,
            Feedback.resolved_at.is_(None)  # 未解决的反馈
        ).order_by(Feedback.severity.desc()).all()

        # 筛选与目标维度相关的反馈
        relevant_feedbacks = [
            fb for fb in feedbacks
            if self._is_feedback_relevant(fb, evolution.target_dimension)
        ]

        # 记录到进化元数据
        evolution.metadata["feedback_collected"] = [
            fb.id for fb in relevant_feedbacks
        ]
        evolution.metadata["feedback_count"] = len(relevant_feedbacks)
        self.db.commit()

        return relevant_feedbacks[:min_feedback_count]

    def _is_feedback_relevant(
        self,
        feedback: Feedback,
        dimension: str
    ) -> bool:
        """判断反馈是否与目标维度相关"""
        dimension_mapping = {
            "plot": ["plot_coherence", "story", "narrative"],
            "character": ["character_consistency", "character_development"],
            "pacing": ["pacing", "rhythm", "tempo"],
            "style": ["writing_quality", "prose", "description"],
            "engagement": ["engagement", "hook", "interest"],
        }

        keywords = dimension_mapping.get(dimension, [dimension])

        # 检查反馈内容或维度评分中是否包含关键词
        if feedback.dimension_scores:
            for key in feedback.dimension_scores.keys():
                if any(kw in key.lower() for kw in keywords):
                    return True

        content_lower = feedback.content.lower()
        return any(kw in content_lower for kw in keywords)

    def generate_improvement(
        self,
        evolution_id: int,
        current_prompt: str,
        feedbacks: List[Feedback]
    ) -> Optional[PromptVersion]:
        """
        基于反馈生成改进的提示词

        Args:
            evolution_id: 进化轮次ID
            current_prompt: 当前提示词
            feedbacks: 相关反馈列表
        """
        evolution = self.db.query(Evolution).filter(
            Evolution.id == evolution_id
        ).first()

        if not evolution:
            return None

        # 分析反馈模式
        patterns = self._analyze_feedback_patterns(feedbacks)

        # 生成改进后的提示词
        improved_prompt = self._evolve_prompt(
            current_prompt,
            patterns,
            evolution.target_dimension,
            evolution.strategy
        )

        # 创建新版本
        version = PromptVersion(
            evolution_id=evolution_id,
            version_number=self._get_next_version_number(evolution_id),
            prompt_type=evolution.prompt_type,
            content=improved_prompt,
            changes_summary=self._generate_changes_summary(patterns),
            parent_version_id=None,  # 简化版本，后续可支持版本链
            test_passed=False,
            is_active=False
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        # 更新进化状态
        evolution.status = EvolutionStatus.TESTING
        evolution.metadata["patterns_found"] = patterns
        self.db.commit()

        logger.info(f"新提示词版本已创建: {version.id}")
        return version

    def _analyze_feedback_patterns(
        self,
        feedbacks: List[Feedback]
    ) -> List[dict]:
        """分析反馈中的问题模式"""
        patterns = []

        # 按维度聚合反馈
        dimension_issues = {}
        for fb in feedbacks:
            if fb.dimension_scores:
                for dim, score in fb.dimension_scores.items():
                    if score < 7:  # 低于7分认为有问题
                        if dim not in dimension_issues:
                            dimension_issues[dim] = []
                        dimension_issues[dim].append({
                            "score": score,
                            "content": fb.content,
                            "severity": fb.severity.value
                        })

        # 生成模式描述
        for dim, issues in dimension_issues.items():
            avg_score = sum(i["score"] for i in issues) / len(issues)
            high_severity = sum(1 for i in issues if i["severity"] == "high")

            patterns.append({
                "dimension": dim,
                "issue_count": len(issues),
                "average_score": round(avg_score, 2),
                "high_severity_count": high_severity,
                "sample_issues": [i["content"] for i in issues[:3]]
            })

        # 按严重程度排序
        patterns.sort(key=lambda x: x["high_severity_count"], reverse=True)

        return patterns

    def _evolve_prompt(
        self,
        current_prompt: str,
        patterns: List[dict],
        target_dimension: str,
        strategy: str
    ) -> str:
        """
        进化提示词

        根据反馈模式生成改进的提示词
        """
        # 分析最严重的问题
        if not patterns:
            return current_prompt

        top_pattern = patterns[0]
        dimension = top_pattern["dimension"]

        # 根据维度和策略生成改进指令
        improvement_instructions = {
            "plot_coherence": {
                "conservative": "\n注意：确保剧情逻辑连贯，每个情节转折都有铺垫。",
                "aggressive": "\n关键要求：\n1. 每个重要事件必须有伏笔铺垫\n2. 人物决策必须符合其动机\n3. 避免突兀的剧情跳跃",
                "targeted": f"\n针对 {dimension} 的改进：{top_pattern['sample_issues'][0] if top_pattern['sample_issues'] else ''}"
            },
            "character_consistency": {
                "conservative": "\n注意：保持人物行为与其性格设定一致。",
                "aggressive": "\n关键要求：\n1. 严格遵循人物性格档案\n2. 人物反应必须符合其经历和价值观\n3. 避免人物性格突变",
                "targeted": f"\n针对人物一致性的改进：检查人物行为是否符合设定"
            },
            "pacing": {
                "conservative": "\n注意：控制叙事节奏，避免拖沓。",
                "aggressive": "\n关键要求：\n1. 每300字内必须有情节推进\n2. 删除冗余的环境描写\n3. 加快对话节奏",
                "targeted": "\n节奏优化：删减冗余，突出关键情节"
            },
            "writing_quality": {
                "conservative": "\n注意：增强描写细节，丰富感官体验。",
                "aggressive": "\n关键要求：\n1. 增加视觉、听觉、嗅觉描写\n2. 使用更生动的动词和形容词\n3. 优化句式多样性",
                "targeted": "\n文笔提升：增加感官描写和修辞手法"
            },
            "engagement": {
                "conservative": "\n注意：在章节结尾设置悬念。",
                "aggressive": "\n关键要求：\n1. 每章结尾必须有悬念或冲突\n2. 保持读者好奇心\n3. 适时揭示和隐藏信息",
                "targeted": "\n吸引力增强：强化悬念和冲突设置"
            }
        }

        dim_key = dimension if dimension in improvement_instructions else "plot_coherence"
        strategy_key = strategy if strategy in improvement_instructions[dim_key] else "conservative"

        instruction = improvement_instructions[dim_key][strategy_key]

        # 组合新提示词
        evolved_prompt = current_prompt + instruction

        return evolved_prompt

    def _get_next_version_number(self, evolution_id: int) -> int:
        """获取下一个版本号"""
        latest = self.db.query(PromptVersion).filter(
            PromptVersion.evolution_id == evolution_id
        ).order_by(PromptVersion.version_number.desc()).first()

        return (latest.version_number + 1) if latest else 1

    def _generate_changes_summary(self, patterns: List[dict]) -> str:
        """生成变更摘要"""
        if not patterns:
            return "无显著问题需要改进"

        summary_parts = []
        for p in patterns[:3]:
            summary_parts.append(
                f"{p['dimension']}: 修复 {p['issue_count']} 个问题 (avg score: {p['average_score']})"
            )

        return "; ".join(summary_parts)

    def run_ab_test(
        self,
        evolution_id: int,
        old_version_id: int,
        new_version_id: int,
        test_chapter_id: int
    ) -> TestResult:
        """
        运行 A/B 测试

        对比新旧提示词在相同样本上的表现
        """
        # 创建测试结果
        test_result = TestResult(
            evolution_id=evolution_id,
            old_version_id=old_version_id,
            new_version_id=new_version_id,
            test_sample_id=test_chapter_id,
            old_scores={},
            new_scores={},
            improvement_rate=0.0,
            passed=False
        )

        self.db.add(test_result)
        self.db.commit()

        # 这里应该实际运行测试
        # 当前使用模拟数据
        import random

        dimensions = ["plot_coherence", "character_consistency", "pacing", "writing_quality", "engagement"]

        old_scores = {d: random.uniform(6, 7.5) for d in dimensions}
        new_scores = {d: old_scores[d] + random.uniform(-0.5, 2) for d in dimensions}

        test_result.old_scores = old_scores
        test_result.new_scores = new_scores

        # 计算改进率
        old_avg = sum(old_scores.values()) / len(old_scores)
        new_avg = sum(new_scores.values()) / len(new_scores)
        improvement = (new_avg - old_avg) / old_avg * 100

        test_result.improvement_rate = round(improvement, 2)

        # 判断是否通过测试（改进率 > 5% 且没有维度显著下降）
        passed = improvement > 5 and all(
            new_scores[d] >= old_scores[d] - 1
            for d in dimensions
        )
        test_result.passed = passed

        self.db.commit()

        # 更新进化状态
        evolution = self.db.query(Evolution).filter(
            Evolution.id == evolution_id
        ).first()

        if evolution:
            evolution.status = (
                EvolutionStatus.COMPLETED if passed
                else EvolutionStatus.ROLLED_BACK
            )
            self.db.commit()

        return test_result

    def apply_evolution(self, evolution_id: int, version_id: int) -> bool:
        """
        应用进化结果

        将通过测试的新版本设为激活状态
        """
        # 停用旧版本
        self.db.query(PromptVersion).filter(
            PromptVersion.is_active == True
        ).update({"is_active": False})

        # 激活新版本
        version = self.db.query(PromptVersion).filter(
            PromptVersion.id == version_id
        ).first()

        if version:
            version.is_active = True
            version.test_passed = True

            # 更新进化状态
            evolution = self.db.query(Evolution).filter(
                Evolution.id == evolution_id
            ).first()

            if evolution:
                evolution.status = EvolutionStatus.COMPLETED
                evolution.applied_at = datetime.now()

            self.db.commit()
            logger.info(f"进化已应用: version {version_id}")
            return True

        return False

    def rollback_evolution(self, evolution_id: int) -> bool:
        """回滚进化"""
        evolution = self.db.query(Evolution).filter(
            Evolution.id == evolution_id
        ).first()

        if not evolution:
            return False

        evolution.status = EvolutionStatus.ROLLED_BACK
        evolution.metadata["rolled_back_at"] = datetime.now().isoformat()

        self.db.commit()
        logger.info(f"进化已回滚: {evolution_id}")
        return True

    def get_evolution_stats(self, project_id: Optional[int] = None) -> dict:
        """获取进化统计"""
        query = self.db.query(Evolution)

        if project_id:
            query = query.filter(Evolution.project_id == project_id)

        total = query.count()
        completed = query.filter(Evolution.status == EvolutionStatus.COMPLETED).count()
        rolled_back = query.filter(Evolution.status == EvolutionStatus.ROLLED_BACK).count()
        testing = query.filter(Evolution.status == EvolutionStatus.TESTING).count()

        # 计算成功率
        success_rate = completed / (completed + rolled_back) * 100 if (completed + rolled_back) > 0 else 0

        # 按维度统计
        by_dimension = {}
        for evo in query.all():
            dim = evo.target_dimension
            if dim not in by_dimension:
                by_dimension[dim] = {"total": 0, "success": 0}
            by_dimension[dim]["total"] += 1
            if evo.status == EvolutionStatus.COMPLETED:
                by_dimension[dim]["success"] += 1

        return {
            "total_evolutions": total,
            "completed": completed,
            "rolled_back": rolled_back,
            "testing": testing,
            "success_rate": round(success_rate, 1),
            "by_dimension": by_dimension
        }

    def get_best_practices(self, project_id: Optional[int] = None) -> List[dict]:
        """获取最佳实践（成功的进化经验）"""
        query = self.db.query(Evolution).filter(
            Evolution.status == EvolutionStatus.COMPLETED
        )

        if project_id:
            query = query.filter(Evolution.project_id == project_id)

        successful_evos = query.order_by(Evolution.applied_at.desc()).limit(10).all()

        practices = []
        for evo in successful_evos:
            version = self.db.query(PromptVersion).filter(
                PromptVersion.evolution_id == evo.id,
                PromptVersion.is_active == True
            ).first()

            if version:
                practices.append({
                    "dimension": evo.target_dimension,
                    "strategy": evo.strategy,
                    "changes": version.changes_summary,
                    "applied_at": evo.applied_at.isoformat() if evo.applied_at else None
                })

        return practices
