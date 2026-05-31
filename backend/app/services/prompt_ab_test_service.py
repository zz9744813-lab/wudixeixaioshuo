"""PromptABTestService - 真实 Prompt A/B 验证 (P6)
按方案 P4：真人分 reader_score / dimension_scores 优先作为金标准。
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.evolution import PromptABTestRun
from app.services.openai_llm_service import llm_manager
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class PromptABTestService:
    """真实 A/B 验证服务（真人分优先评分）"""

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

        评分优先级：
        1. 样本自带 reader_score（真人总分，优先作为金标准）
        2. dimension_scores reader_addiction/commercial_readability 均值
        3. 用 Critic 跑分（系统自评，降级）

        返回 {"winner": {...} | None, "runs": [...], "baseline_avg": float}
        """
        use_samples = (samples or [])[:max_samples]
        if len(use_samples) < min_samples:
            logger.warning(f"A/B 样本不足（{len(use_samples)} < {min_samples}），跳过")
            return {"winner": None, "runs": [], "baseline_avg": 0.0,
                    "reason": "样本不足"}

        # 金标准：优先真人分
        baseline_gold_scores, baseline_detail = self._collect_gold_scores(
            use_samples, role=role, prompt_text=baseline_prompt, project_id=project_id,
        )
        use_reader_gold = baseline_detail.get("source") == "reader"
        baseline_avg = round(
            sum(baseline_gold_scores) / len(baseline_gold_scores), 2
        ) if baseline_gold_scores else 0.0

        runs = []
        winner = None
        for idx, candidate in enumerate(candidate_prompts or []):
            cand_prompt = candidate.get("prompt") or candidate.get("content") or ""
            if not cand_prompt:
                continue

            if use_reader_gold:
                cand_gold_scores, _ = self._collect_gold_scores(
                    use_samples, role=role, prompt_text=cand_prompt, project_id=project_id,
                )
                cand_avg = round(
                    sum(cand_gold_scores) / len(cand_gold_scores), 2
                ) if cand_gold_scores else 0.0
                cand_cost = 0.0  # 真人分无需额外 LLM 调用
            else:
                cand_avg, cand_cost = await self._score_prompt(
                    project_id, role, cand_prompt, use_samples
                )

            improvement = round(cand_avg - baseline_avg, 2)
            passed = improvement >= min_improvement

            record = self._persist_run(
                project_id=project_id, role=role, candidate_index=idx,
                sample_ids=[s.get("id") for s in use_samples],
                baseline_avg=baseline_avg, candidate_avg=cand_avg,
                improvement=improvement, passed=passed, cost=cand_cost,
                candidate=candidate,
                gold_source=baseline_detail.get("source", "system"),
            )
            run_info = {
                "run_id": record.id,
                "candidate_index": idx,
                "baseline_avg_score": baseline_avg,
                "candidate_avg_score": cand_avg,
                "improvement": improvement,
                "passed": passed,
                "gold_source": baseline_detail.get("source", "system"),
            }
            runs.append(run_info)

            if passed and (winner is None or improvement > winner["improvement"]):
                winner = {**run_info, "candidate": candidate}

        return {
            "winner": winner,
            "runs": runs,
            "baseline_avg": baseline_avg,
            "gold_source": baseline_detail.get("source", "system"),
        }

    def _collect_gold_scores(
        self, samples: List[dict], role: str, prompt_text: str, project_id: int,
    ) -> tuple:
        """收集样本金标准分数，优先 reader_score，其次 dimension_scores/score 字段，降级系统评分。

        返回 (score_list, {"source": ..., "count": ...})
        """
        reader_scores: List[float] = []
        dim_scores: List[float] = []

        for sample in samples:
            # 1. 样本自带 reader_score
            if "reader_score" in sample and sample["reader_score"] is not None:
                try:
                    reader_scores.append(float(sample["reader_score"]))
                except (TypeError, ValueError):
                    pass
                continue

            # 2. 查库：chapter_id/id → 真人反馈均值
            chapter_id = sample.get("chapter_id") or sample.get("id")
            if chapter_id and project_id:
                try:
                    from app.models.feedback import Feedback as _FB
                    rows = (
                        self.db.query(_FB.reader_score)
                        .filter(
                            _FB.chapter_id == int(chapter_id),
                            _FB.reader_score.isnot(None),
                            _FB.source == "reader",
                        )
                        .all()
                    )
                    if rows:
                        vals = [float(r[0]) for r in rows]
                        reader_scores.append(sum(vals) / len(vals))
                        continue
                except Exception:
                    pass

            # 3. dimension_scores 均值
            dims = sample.get("dimension_scores") or {}
            if isinstance(dims, dict) and dims:
                vals = []
                for k in ("reader_addiction", "commercial_readability", "emotional_hook"):
                    v = dims.get(k)
                    if v is not None:
                        try:
                            vals.append(float(v))
                        except (TypeError, ValueError):
                            pass
                if vals:
                    dim_scores.append(sum(vals) / len(vals))
                    continue

            # 4. legacy score 字段（测试样本/历史分）
            raw = sample.get("score")
            if raw is not None:
                try:
                    dim_scores.append(float(raw))
                except (TypeError, ValueError):
                    pass
                continue

        if reader_scores:
            return reader_scores, {"source": "reader", "count": len(reader_scores)}
        if dim_scores:
            return dim_scores, {"source": "dimension", "count": len(dim_scores)}

        # 4. 降级：Critic 跑分
        scores, _ = self._score_prompt_sync(role, prompt_text, samples)
        if scores:
            return scores, {"source": "system", "count": len(scores)}
        return [], {"source": "none", "count": 0}

    def _score_prompt_sync(
        self, role: str, prompt: str, samples: List[dict],
    ) -> tuple:
        """同步调用 Critic 对样本打分，降级模式不记录成本。

        注意：不能在已有运行中 event loop 内调用（会抛 RuntimeError），
        因此这里用 asyncio.new_event_loop 创建独立 loop。
        """
        scores: List[float] = []
        for sample in samples:
            content = sample.get("content") or sample.get("chapter_content") or ""
            if not content:
                raw = sample.get("score")
                if raw is not None:
                    try:
                        scores.append(float(raw))
                    except (TypeError, ValueError):
                        pass
                continue
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    llm_manager.generate(
                        prompt=f"{prompt}\n\n## 待评审\n{content[:6000]}",
                        role="critic", temperature=0.3, db=self.db,
                        request_type="prompt_ab_test",
                        project_id=sample.get("project_id") or 0,
                    )
                )
                loop.close()
                score = self._extract_score(response.get("content", ""))
                if score is not None:
                    scores.append(score)
            except Exception as e:
                logger.debug(f"A/B 降级评分失败: {e}")
        avg = round(sum(scores) / len(scores), 2) if scores else 0.0
        return scores, avg

    async def _score_prompt(
        self, project_id: int, role: str, prompt: str, samples: List[dict],
    ) -> tuple:
        """用候选 prompt 在每个样本上跑评审，返回 (平均分, 总成本)。"""
        scores = []
        total_cost = 0.0
        for sample in samples:
            content = sample.get("content") or sample.get("chapter_content") or ""
            if not content:
                raw = sample.get("score")
                if raw is not None:
                    try:
                        scores.append(float(raw))
                    except (TypeError, ValueError):
                        pass
                continue
            try:
                response = await llm_manager.generate(
                    prompt=f"{prompt}\n\n## 待评审\n{content[:6000]}",
                    role="critic", temperature=0.3, db=self.db,
                    request_type="prompt_ab_test", project_id=project_id,
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
        m = re.search(r'overall_score["\s:]+(\d+(?:\.\d+)?)', content)
        if m:
            return float(m.group(1))
        return None

    def _persist_run(
        self, project_id, role, candidate_index, sample_ids,
        baseline_avg, candidate_avg, improvement, passed, cost, candidate,
        gold_source: str = "system",
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
            details={
                "candidate_index": candidate_index,
                "gold_source": gold_source,
            },
            total_cost=cost,
            created_at=utc_now(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
