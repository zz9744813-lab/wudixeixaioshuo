"""Prompt Meta Agent - 自动生成 Prompt 候选。"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.llm_router import LLMRouter, LLMRouterAllProvidersFailed


class PromptMetaAgent:
    """根据诊断结果生成多个 Prompt 候选。"""

    def __init__(self, db: Session):
        self.db = db

    async def propose_candidates(
        self,
        role: str,
        current_prompt: str,
        diagnosis: str,
        best_practices: Optional[List[str]] = None,
        candidate_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """生成多个 Prompt 候选。

        每个候选包含：修改点说明、完整 prompt 文本、预期改善指标、风险点。
        """
        system_prompt = (
            "你是 Prompt 优化专家。根据诊断结果和当前 Prompt，生成改进候选。"
            "每个候选必须包含：modifications（修改说明）、prompt（完整文本）、expected_improvement（预期改善）、risks（风险）。"
            "输出严格 JSON 数组。"
        )

        user_prompt = (
            f"当前角色：{role}\n"
            f"当前 Prompt：\n{current_prompt[:2000]}\n\n"
            f"诊断结果：{diagnosis}\n\n"
            f"最佳实践参考：\n{chr(10).join(best_practices or ['无'])}\n\n"
            f"请生成 {candidate_count} 个改进候选。"
        )

        try:
            result = await LLMRouter(self.db).generate(
                role="meta_prompt",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=3000,
                temperature=0.5,
                trace={"component": "prompt_meta_agent", "role": role},
            )
            candidates = self._parse_json_array(result.content)
            # 确保每个候选都有必要字段
            validated = []
            for c in candidates[:candidate_count]:
                validated.append({
                    "modifications": c.get("modifications", "无说明"),
                    "prompt": c.get("prompt", current_prompt),
                    "expected_improvement": c.get("expected_improvement", "待验证"),
                    "risks": c.get("risks", "无"),
                })
            return validated
        except (LLMRouterAllProvidersFailed, Exception):
            return self._fallback_candidates(role, current_prompt, diagnosis, candidate_count)

    def _fallback_candidates(
        self,
        role: str,
        current_prompt: str,
        diagnosis: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        """无 LLM 时的兜底候选。"""
        candidates = []
        for i in range(min(count, 2)):
            candidates.append({
                "modifications": f"候选 {i+1}：基于诊断「{diagnosis[:50]}」的规则化调整",
                "prompt": current_prompt,
                "expected_improvement": "需要 A/B 验证",
                "risks": "规则化兜底，改进幅度有限",
            })
        return candidates

    def _parse_json_array(self, content: str) -> List[Dict[str, Any]]:
        """从 LLM 输出中解析 JSON 数组。"""
        text = (content or "").strip()
        if text.startswith("```"):
            lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            start = text.find("[")
            end = text.rfind("]")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        return []
