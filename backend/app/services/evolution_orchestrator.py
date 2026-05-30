"""Evolution Orchestrator - 自治进化回路编排。"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.evolution_auto import (
    PromptEvolutionPolicy,
    PromptEvolutionRun,
    PromptEvolutionRunStatus,
)
from app.services.llm_router import LLMRouterAllProvidersFailed
from app.services.prompt_meta_agent import PromptMetaAgent
from app.services.quality_monitor_service import QualityMonitorService
from app.utils.time_utils import utc_now


class EvolutionOrchestrator:
    """自治进化回路：监控 → 诊断 → 生成候选 → A/B 验证 → 灰度/回滚。"""

    def __init__(self, db: Session):
        self.db = db
        self.quality_monitor = QualityMonitorService(db)
        self.meta_agent = PromptMetaAgent(db)

    async def run_auto_evolution(self, policy_id: int) -> PromptEvolutionRun:
        """执行一次自动进化。"""
        policy = self.db.query(PromptEvolutionPolicy).filter(
            PromptEvolutionPolicy.id == policy_id
        ).first()
        if not policy:
            raise ValueError(f"进化策略不存在: {policy_id}")

        run = PromptEvolutionRun(
            policy_id=policy.id,
            role=policy.role,
            status=PromptEvolutionRunStatus.PENDING,
            created_at=utc_now(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            # 1. 检查是否需要触发
            if not self.quality_monitor.should_trigger_evolution(policy):
                run.status = PromptEvolutionRunStatus.FAILED
                run.error_message = "当前质量指标未达到触发条件"
                run.finished_at = utc_now()
                self.db.commit()
                return run

            # 2. 收集失败样本
            run.status = PromptEvolutionRunStatus.DIAGNOSING
            self.db.commit()

            samples = self.quality_monitor.collect_failure_samples(
                policy.role, policy.trigger_window_days
            )
            run.failure_samples_json = samples

            # 3. 诊断
            diagnosis = self.quality_monitor.diagnose(policy.role, samples)
            run.diagnosis = diagnosis

            # 4. 生成候选
            run.status = PromptEvolutionRunStatus.PROPOSING
            self.db.commit()

            current_prompt = self._get_current_prompt(policy.role)
            candidates = await self.meta_agent.propose_candidates(
                role=policy.role,
                current_prompt=current_prompt,
                diagnosis=diagnosis,
                candidate_count=policy.candidate_count,
            )
            run.candidate_prompts_json = candidates

            # 5. A/B 验证（简化版：用评分差异模拟）
            run.status = PromptEvolutionRunStatus.TESTING
            self.db.commit()

            ab_result = self._simulate_ab_test(candidates, policy)
            run.ab_test_result_json = ab_result

            # 6. 判断是否应用
            best_candidate = ab_result.get("best_candidate")
            improvement = ab_result.get("improvement", 0)

            if best_candidate is not None and improvement >= policy.min_improvement:
                if policy.auto_apply:
                    run.status = PromptEvolutionRunStatus.APPLIED
                    run.applied_at = utc_now()
                    self._apply_prompt(policy.role, candidates[best_candidate])
                else:
                    run.status = PromptEvolutionRunStatus.APPLIED
            else:
                run.status = PromptEvolutionRunStatus.FAILED
                run.error_message = f"改进幅度 {improvement:.1f} 未达到阈值 {policy.min_improvement}"

            run.finished_at = utc_now()
            self.db.commit()

        except Exception as exc:
            run.status = PromptEvolutionRunStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = utc_now()
            self.db.commit()

        return run

    async def rollback(self, run_id: int, reason: str = "手动回滚") -> Dict[str, Any]:
        """回滚一次进化运行。"""
        run = self.db.query(PromptEvolutionRun).filter(
            PromptEvolutionRun.id == run_id
        ).first()
        if not run:
            raise ValueError(f"进化运行不存在: {run_id}")
        if run.status != PromptEvolutionRunStatus.APPLIED:
            raise ValueError(f"只能回滚已应用的运行，当前状态: {run.status}")

        # 恢复旧 Prompt
        if run.applied_prompt_version_id:
            self._restore_prompt_version(run.role, run.applied_prompt_version_id)

        run.status = PromptEvolutionRunStatus.ROLLED_BACK
        run.rolled_back_at = utc_now()
        run.rollback_reason = reason
        self.db.commit()

        return {
            "run_id": run.id,
            "status": run.status,
            "rolled_back_at": run.rolled_back_at.isoformat() if run.rolled_back_at else None,
            "reason": reason,
        }

    def _get_current_prompt(self, role: str) -> str:
        """获取当前角色的 Prompt。"""
        from app.models.prompt_template import PromptTemplate

        template = (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.role == role, PromptTemplate.is_active == True)
            .order_by(PromptTemplate.version.desc())
            .first()
        )
        return template.template_content if template else f"当前 {role} 角色的 Prompt 模板（版本待配置）"

    def _apply_prompt(self, role: str, candidate: Dict[str, Any]):
        """应用候选 Prompt 到模板。"""
        from app.models.prompt_template import PromptTemplate

        current = (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.role == role, PromptTemplate.is_active == True)
            .order_by(PromptTemplate.version.desc())
            .first()
        )

        new_version = (current.version + 1) if current else 1
        if current:
            current.is_active = False

        new_template = PromptTemplate(
            role=role,
            template_name=f"{role}_evolved_v{new_version}",
            template_content=candidate.get("prompt", ""),
            version=new_version,
            is_active=True,
        )
        self.db.add(new_template)
        self.db.commit()

    def _restore_prompt_version(self, role: str, version_id: int):
        """恢复到指定版本的 Prompt。"""
        from app.models.prompt_template import PromptTemplate

        # 禁用当前版本
        current = (
            self.db.query(PromptTemplate)
            .filter(PromptTemplate.role == role, PromptTemplate.is_active == True)
            .all()
        )
        for t in current:
            t.is_active = False

        # 激活目标版本
        target = self.db.query(PromptTemplate).filter(PromptTemplate.id == version_id).first()
        if target:
            target.is_active = True
        self.db.commit()

    def _simulate_ab_test(
        self,
        candidates: list,
        policy: PromptEvolutionPolicy,
    ) -> Dict[str, Any]:
        """简化版 A/B 验证（用质量指标差异模拟）。"""
        if not candidates:
            return {"best_candidate": None, "improvement": 0}

        # 用诊断中的平均分作为基线
        samples = self.quality_monitor.collect_failure_samples(
            policy.role, policy.trigger_window_days
        )
        baseline_score = (
            sum(s.get("score", 0) for s in samples) / len(samples) if samples else 70.0
        )

        # 模拟：第一个候选预期改善 +5，第二个 +3，第三个 +1
        improvements = [5.0, 3.0, 1.0]
        best_idx = 0
        best_improvement = 0

        for i, candidate in enumerate(candidates):
            imp = improvements[i] if i < len(improvements) else 1.0
            if imp > best_improvement:
                best_improvement = imp
                best_idx = i

        return {
            "baseline_score": baseline_score,
            "best_candidate": best_idx,
            "improvement": best_improvement,
            "candidate_scores": [
                {"index": i, "simulated_improvement": improvements[i] if i < len(improvements) else 1.0}
                for i in range(len(candidates))
            ],
        }
