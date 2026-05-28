"""
Review Service - 独立评审系统
P4 Phase 4: 多维度独立评审
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.review import ReviewProfile, ReviewResult, FinalReview
from app.models.chapter import Chapter
from app.services.openai_llm_service import llm_manager

logger = logging.getLogger(__name__)


# 评审维度定义
REVIEW_DIMENSIONS = {
    "plot_progress": {
        "name": "剧情推进",
        "description": "本章是否有实质性剧情推进，避免水字数",
        "weight": 0.15
    },
    "character_consistency": {
        "name": "人物一致性",
        "description": "人物言行是否与其设定一致",
        "weight": 0.15
    },
    "continuity": {
        "name": "连续性",
        "description": "与前文的设定、时间线、伏笔是否一致",
        "weight": 0.12
    },
    "pacing": {
        "name": "节奏控制",
        "description": "节奏是否合适，避免过快或过慢",
        "weight": 0.10
    },
    "hook": {
        "name": "章节钩子",
        "description": "开头是否吸引人，结尾是否有悬念",
        "weight": 0.10
    },
    "emotional_reward": {
        "name": "情绪回报",
        "description": "是否有情绪满足点，让读者有获得感",
        "weight": 0.10
    },
    "foreshadow_quality": {
        "name": "伏笔质量",
        "description": "伏笔埋设/推进/回收是否自然",
        "weight": 0.08
    },
    "style_consistency": {
        "name": "文风稳定",
        "description": "文风是否稳定，避免突兀变化",
        "weight": 0.08
    },
    "readability": {
        "name": "可读性",
        "description": "段落、对话是否自然流畅",
        "weight": 0.07
    },
    "commercial_potential": {
        "name": "商业潜力",
        "description": "追读动力、爽点密度",
        "weight": 0.05
    },
}


class ReviewService:
    """评审服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== Review Profile ==========

    def create_review_profile(
        self,
        project_id: int = None,
        name: str = "默认评审配置",
        is_default: bool = False,
        reviewer_roles: List[str] = None,
        quality_threshold: float = 80.0,
        rewrite_threshold: float = 75.0,
        auto_reject_threshold: float = 60.0,
        weights: Dict[str, float] = None,
        strictness: int = 5,
        max_review_rounds: int = 2
    ) -> ReviewProfile:
        """创建评审配置"""
        profile = ReviewProfile(
            project_id=project_id,
            name=name,
            is_default=1 if is_default else 0,
            reviewer_roles=reviewer_roles or ["reviewer_plot", "reviewer_character", "reviewer_continuity"],
            quality_threshold=quality_threshold,
            rewrite_threshold=rewrite_threshold,
            auto_reject_threshold=auto_reject_threshold,
            weights=weights or {k: v["weight"] for k, v in REVIEW_DIMENSIONS.items()},
            strictness=strictness,
            max_review_rounds=max_review_rounds
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_review_profile(self, profile_id: int) -> Optional[ReviewProfile]:
        """获取评审配置"""
        return self.db.query(ReviewProfile).filter(
            ReviewProfile.id == profile_id
        ).first()

    def get_default_profile(self, project_id: int = None) -> Optional[ReviewProfile]:
        """获取默认评审配置"""
        # 先找项目专属默认
        if project_id:
            profile = self.db.query(ReviewProfile).filter(
                ReviewProfile.project_id == project_id,
                ReviewProfile.is_default == 1
            ).first()
            if profile:
                return profile

        # 找全局默认
        return self.db.query(ReviewProfile).filter(
            ReviewProfile.is_default == 1
        ).first()

    # ========== Single Dimension Review ==========

    async def review_dimension(
        self,
        task_id: int,
        chapter_id: int,
        version_id: int,
        chapter_content: str,
        chapter_title: str,
        reviewer_role: str,
        dimension: str,
        bible_context: str = "",
        memory_context: str = ""
    ) -> ReviewResult:
        """
        单维度评审

        reviewer_role:
        - reviewer_plot: 剧情评审
        - reviewer_character: 人物评审
        - reviewer_continuity: 连续性评审
        - reviewer_style: 文风评审
        - reviewer_commercial: 商业性评审
        """
        dim_config = REVIEW_DIMENSIONS.get(dimension, {})

        prompt = f"""你是一位专业的{dim_config.get('name', '小说')}评审专家。

请严格评审以下章节在"{dim_config.get('name', dimension)}"维度上的表现。

章节标题: {chapter_title}

章节内容:
{chapter_content[:5000]}

{bible_context}

{memory_context}

评审维度: {dim_config.get('name', dimension)}
维度说明: {dim_config.get('description', '')}

请输出JSON格式:
{{
    "score": 85,  // 0-100分
    "assessment": "详细评价...",
    "problems": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "required_fixes": ["必须修复1"]  // 如果有
}}

评分标准:
- 90-100: 优秀，可作为范例
- 80-89: 良好，基本达标
- 70-79: 及格，有改进空间
- 60-69: 不及格，需要改写
- <60: 严重问题，建议重写"""

        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role=reviewer_role,
                temperature=0.3  # 低温，更严格
            )

            content = response.get("content", "")

            # 解析JSON
            try:
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].strip()
                else:
                    json_str = content

                result_data = json.loads(json_str)
            except:
                # 解析失败，使用默认
                result_data = {
                    "score": 75,
                    "assessment": "解析失败，使用默认评分",
                    "problems": [],
                    "suggestions": [],
                    "required_fixes": []
                }

            # 保存评审结果
            review = ReviewResult(
                task_id=task_id,
                chapter_id=chapter_id,
                version_id=version_id,
                reviewer_role=reviewer_role,
                reviewer_model=response.get("model", "unknown"),
                provider_name=response.get("provider", "unknown"),
                total_score=result_data.get("score", 75),
                score_breakdown={dimension: result_data.get("score", 75)},
                problems=result_data.get("problems", []),
                suggestions=result_data.get("suggestions", []),
                required_fixes=result_data.get("required_fixes", []),
                pass_status="pass" if result_data.get("score", 0) >= 80 else "rewrite",
                raw_output=content
            )

            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)

            logger.info(f"[Review] {reviewer_role} 评审完成: score={review.total_score}")
            return review

        except Exception as e:
            logger.error(f"评审失败: {e}")
            # 创建失败记录
            review = ReviewResult(
                task_id=task_id,
                chapter_id=chapter_id,
                version_id=version_id,
                reviewer_role=reviewer_role,
                total_score=0,
                pass_status="error",
                raw_output=str(e)
            )
            self.db.add(review)
            self.db.commit()
            return review

    async def run_multi_dimension_review(
        self,
        task_id: int,
        chapter_id: int,
        version_id: int,
        chapter_content: str,
        chapter_title: str,
        profile: ReviewProfile = None,
        bible_context: str = "",
        memory_context: str = ""
    ) -> List[ReviewResult]:
        """
        运行多维度评审
        """
        if not profile:
            profile = self.get_default_profile()

        roles = profile.reviewer_roles if profile else ["reviewer_plot", "reviewer_character", "reviewer_continuity"]

        # 角色到维度的映射
        role_dimension_map = {
            "reviewer_plot": ["plot_progress", "pacing", "hook"],
            "reviewer_character": ["character_consistency", "emotional_reward"],
            "reviewer_continuity": ["continuity", "foreshadow_quality", "memory_consistency"],
            "reviewer_style": ["style_consistency", "readability"],
            "reviewer_commercial": ["commercial_potential"],
        }

        results = []
        for role in roles:
            dimensions = role_dimension_map.get(role, ["plot_progress"])
            for dim in dimensions:
                result = await self.review_dimension(
                    task_id=task_id,
                    chapter_id=chapter_id,
                    version_id=version_id,
                    chapter_content=chapter_content,
                    chapter_title=chapter_title,
                    reviewer_role=role,
                    dimension=dim,
                    bible_context=bible_context,
                    memory_context=memory_context
                )
                results.append(result)

        return results

    # ========== Final Review ==========

    async def run_final_judge(
        self,
        task_id: int,
        chapter_id: int,
        version_id: int,
        review_results: List[ReviewResult],
        profile: ReviewProfile = None
    ) -> FinalReview:
        """
        FinalJudge - 汇总多评审结果，做出最终判定
        """
        if not profile:
            profile = self.get_default_profile()

        weights = profile.weights if profile else {k: v["weight"] for k, v in REVIEW_DIMENSIONS.items()}

        # 计算加权分数
        dimension_scores = {}
        total_weighted = 0
        total_weight = 0

        for review in review_results:
            for dim, score in review.score_breakdown.items():
                if dim not in dimension_scores:
                    dimension_scores[dim] = []
                dimension_scores[dim].append(score)

        # 平均每个维度的分数
        avg_scores = {}
        for dim, scores in dimension_scores.items():
            avg_scores[dim] = sum(scores) / len(scores)

        # 计算加权总分
        for dim, score in avg_scores.items():
            weight = weights.get(dim, 0.1)
            total_weighted += score * weight
            total_weight += weight

        weighted_score = total_weighted / total_weight if total_weight > 0 else 0

        # 收集问题
        all_problems = []
        all_suggestions = []
        critical_issues = []
        required_fixes = []

        for review in review_results:
            all_problems.extend(review.problems or [])
            all_suggestions.extend(review.suggestions or [])
            required_fixes.extend(review.required_fixes or [])

            if review.total_score < 60:
                critical_issues.append(f"{review.reviewer_role}: 严重问题")

        # 判定状态
        threshold = profile.quality_threshold if profile else 80.0
        rewrite_threshold = profile.rewrite_threshold if profile else 75.0

        if weighted_score >= threshold:
            final_status = "pass"
        elif weighted_score >= rewrite_threshold:
            final_status = "rewrite"
        else:
            final_status = "reject"

        # 改写重点
        rewrite_focus = []
        for dim, score in avg_scores.items():
            if score < 70:
                rewrite_focus.append(dim)

        final_review = FinalReview(
            task_id=task_id,
            chapter_id=chapter_id,
            version_id=version_id,
            weighted_score=round(weighted_score, 2),
            min_score=min(avg_scores.values()) if avg_scores else 0,
            max_score=max(avg_scores.values()) if avg_scores else 0,
            review_result_ids=[r.id for r in review_results],
            dimension_scores=avg_scores,
            critical_issues=critical_issues,
            warnings=all_problems[:5],  # 最多5个警告
            final_status=final_status,
            rewrite_focus=rewrite_focus
        )

        self.db.add(final_review)
        self.db.commit()
        self.db.refresh(final_review)

        logger.info(f"[FinalReview] 最终评审: score={weighted_score:.1f}, status={final_status}")
        return final_review

    # ========== Rewrite Plan ==========

    async def generate_rewrite_plan(
        self,
        chapter_content: str,
        final_review: FinalReview,
        review_results: List[ReviewResult]
    ) -> Dict[str, Any]:
        """
        根据评审结果生成改写计划
        """
        # 收集必须修复的问题
        required_fixes = []
        for review in review_results:
            required_fixes.extend(review.required_fixes or [])

        # 收集低分维度
        low_dimensions = [
            dim for dim, score in final_review.dimension_scores.items()
            if score < 70
        ]

        prompt = f"""你是一位资深小说编辑。请根据以下评审结果，生成详细的改写计划。

章节内容:
{chapter_content[:3000]}

最终评分: {final_review.weighted_score}
低分维度: {low_dimensions}
必须修复的问题:
{chr(10).join([f"- {fix}" for fix in required_fixes[:10]])}

请输出JSON格式:
{{
    "priority": "high",  // high/medium/low
    "focus_areas": ["人物一致性", "节奏控制"],
    "specific_instructions": [
        "具体改写指令1",
        "具体改写指令2"
    ],
    "keep_unchanged": ["保留的部分1"],
    "expected_improvement": "预期改进效果"
}}"""

        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role="rewrite_planner",
                temperature=0.5
            )

            content = response.get("content", "")

            # 解析JSON
            try:
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].strip()
                else:
                    json_str = content

                plan = json.loads(json_str)
            except:
                plan = {
                    "priority": "high",
                    "focus_areas": low_dimensions,
                    "specific_instructions": required_fixes,
                    "keep_unchanged": [],
                    "expected_improvement": "修复上述问题"
                }

            return plan

        except Exception as e:
            logger.error(f"生成改写计划失败: {e}")
            return {
                "priority": "high",
                "focus_areas": low_dimensions,
                "specific_instructions": required_fixes,
                "error": str(e)
            }

    # ========== Statistics ==========

    def get_project_review_stats(self, project_id: int) -> Dict[str, Any]:
        """获取项目评审统计"""
        reviews = self.db.query(ReviewResult).filter(
            ReviewResult.chapter_id.in_(
                self.db.query(Chapter.id).filter(Chapter.project_id == project_id)
            )
        ).all()

        if not reviews:
            return {"total_reviews": 0}

        total = len(reviews)
        avg_score = sum(r.total_score for r in reviews) / total

        by_status = {}
        for status in ["pass", "rewrite", "reject"]:
            count = sum(1 for r in reviews if r.pass_status == status)
            by_status[status] = count

        # 按角色统计
        by_role = {}
        for r in reviews:
            role = r.reviewer_role
            if role not in by_role:
                by_role[role] = {"count": 0, "avg_score": 0, "total": 0}
            by_role[role]["count"] += 1
            by_role[role]["total"] += r.total_score

        for role in by_role:
            by_role[role]["avg_score"] = round(by_role[role]["total"] / by_role[role]["count"], 2)
            del by_role[role]["total"]

        return {
            "total_reviews": total,
            "avg_score": round(avg_score, 2),
            "by_status": by_status,
            "by_role": by_role
        }
