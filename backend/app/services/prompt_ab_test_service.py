"""
PromptABTestService - 真实 Prompt A/B 验证 (P6)
对每个候选 Prompt 用真实低分样本跑生成/评审，用同一 Critic 打分，
比较平均分，满足阈值才上线。绝不使用固定假提升。
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.evolution import PromptABTestRun
from app.services.openai_llm_service import llm_manager
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class PromptABTestService:
    """真实 A/B 验证服务"""

    def __init__(self, db: Session):
        self.db = db

    async def run_ab_test(
        self,
        project_id: int,
        role: str,
        baseline_prompt: str,
        candidate_prompts: List[dict],
        samples: List[dict],
        min_samples: int = 3,
        max_samples: int = 5,
        min_improvement: float = 3.0,
    ) -> dict:
        """对候选 Prompt 做真实 A/B 验证。

        返回 {"winner": {...} | None, "runs": [...], "baseline_avg": float}
        winner.passed 为 True 时才允许上线。
        """
        use_samples = (samples or [])[:max_samples]
        if len(use_samples) < min_samples:
            logger.warning(
                f"A/B 样本不足（{len(use_samples)} < {min_samples}），跳过"
            )
            return {"winner": None, "runs": [], "baseline_avg": 0.0,
                    "reason": "样本不足"}

        # 1. baseline 平均分
        baseline_avg, _ = await self._score_prompt(
            project_id, role, baseline_prompt, use_samples
        )

        runs = []
        winner = None
        for idx, candidate in enumerate(candidate_prompts or []):
            cand_prompt = candidate.get("prompt") or candidate.get("content") or ""
            if not cand_prompt:
                continue

            cand_avg, cand_cost = await self._score_prompt(
                project_id, role, cand_prompt, use_samples
            )
            improvement = round(cand_avg - baseline_avg, 2)
            passed = improvement >= min_improvement

            record = self._persist_run(
                project_id=project_id,
                role=role,
                candidate_index=idx,
                sample_ids=[s.get("id") for s in use_samples],
                baseline_avg=baseline_avg,
                candidate_avg=cand_avg,
                improvement=improvement,
                passed=passed,
                cost=cand_cost,
                candidate=candidate,
            )
            run_info = {
                "run_id": record.id,
                "candidate_index": idx,
                "baseline_avg_score": baseline_avg,
                "candidate_avg_score": cand_avg,
                "improvement": improvement,
                "passed": passed,
            }
            runs.append(run_info)

            if passed and (winner is None or improvement > winner["improvement"]):
                winner = {**run_info, "candidate": candidate}

        return {
            "winner": winner,
            "runs": runs,
            "baseline_avg": baseline_avg,
        }

    async def _score_prompt(
        self, project_id: int, role: str, prompt: str, samples: List[dict]
    ) -> tuple:
        """用候选 prompt 在每个样本上跑评审，返回 (平均分, 总成本)。

        以样本的章节内容为输入，调用 critic 角色做真实评分。
        样本无内容时回退使用样本自带 score。
        """
        scores = []
        total_cost = 0.0
        for sample in samples:
            content = sample.get("content") or sample.get("chapter_content") or ""
            if not content:
                # 无正文，退回样本既有分数（真实历史分，非伪造）
                if sample.get("score") is not None:
                    scores.append(float(sample["score"]))
                continue
            try:
                full_prompt = f"{prompt}\n\n## 待评审正文\n{content[:6000]}"
                response = await llm_manager.generate(
                    prompt=full_prompt,
                    role="critic",
                    temperature=0.3,
                    db=self.db,
                    request_type="prompt_ab_test",
                    project_id=project_id,
                )
                total_cost += response.get("cost", 0.0)
                score = self._extract_score(response.get("content", ""))
                if score is not None:
                    scores.append(score)
            except Exception as e:
                logger.warning(f"A/B 评分调用失败: {e}")

        avg = round(sum(scores) / len(scores), 2) if scores else 0.0
        return avg, total_cost

    def _extract_score(self, content: str) -> Optional[float]:
        """从评审输出中提取 overall_score。"""
        import json
        import re

        if not content:
            return None
        text = content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start:end + 1])
                val = data.get("overall_score")
                if isinstance(val, (int, float)):
                    return float(val)
            except Exception:
                pass
        # 退化：匹配 "overall_score": 82
        m = re.search(r'overall_score["\s:]+(\d+(?:\.\d+)?)', content)
        if m:
            return float(m.group(1))
        return None

    def _persist_run(
        self, project_id, role, candidate_index, sample_ids,
        baseline_avg, candidate_avg, improvement, passed, cost, candidate,
    ) -> PromptABTestRun:
        record = PromptABTestRun(
            project_id=project_id,
            role=role,
            candidate_prompt_id=candidate.get("id"),
            sample_ids=sample_ids,
            baseline_avg_score=baseline_avg,
            candidate_avg_score=candidate_avg,
            improvement=improvement,
            passed=1 if passed else 0,
            decision="apply" if passed else "reject",
            details={"candidate_index": candidate_index},
            total_cost=cost,
            created_at=utc_now(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
