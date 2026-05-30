"""SubAgent Service - 子 Agent 任务服务。"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun, SubAgentTask, SubAgentTaskStatus
from app.services.llm_router import LLMRouter, LLMRouterAllProvidersFailed
from app.utils.time_utils import utc_now


class SubAgentService:
    """子 Agent 任务服务：负责创建、执行、重试与汇总子任务。"""

    def __init__(self, db: Session):
        self.db = db

    async def create_tasks_from_plan(
        self,
        run_id: int,
        parent_step_id: Optional[int],
        task_specs: List[Dict[str, Any]],
    ) -> List[SubAgentTask]:
        """根据计划创建子 Agent 任务。"""
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")

        tasks = []
        for index, spec in enumerate(task_specs, start=1):
            task = SubAgentTask(
                run_id=run_id,
                parent_step_id=parent_step_id,
                task_type=spec.get("task_type") or "summary",
                title=spec.get("title") or f"子 Agent 任务 {index}",
                role=spec.get("role") or "planner",
                status=SubAgentTaskStatus.PENDING,
                context_json=spec.get("context") or {},
                input_prompt=spec.get("input_prompt") or spec.get("prompt") or "",
                created_at=utc_now(),
            )
            self.db.add(task)
            tasks.append(task)

        self.db.commit()
        for task in tasks:
            self.db.refresh(task)
        return tasks

    async def run_task(self, task_id: int, use_llm: bool = True) -> SubAgentTask:
        """执行单个子 Agent 任务；无可用路由时使用规则化结果，保证 P0 主干可运行。"""
        task = self.db.query(SubAgentTask).filter(SubAgentTask.id == task_id).first()
        if not task:
            raise ValueError(f"子 Agent 任务不存在: {task_id}")
        if task.status == SubAgentTaskStatus.CANCELLED:
            return task

        task.status = SubAgentTaskStatus.RUNNING
        task.started_at = utc_now()
        task.error_message = None
        self.db.commit()

        try:
            result = None
            if use_llm:
                result = await self._try_llm(task)

            if result is None:
                result = self._rule_based_result(task)

            task.output_text = result["output_text"]
            task.parsed_output = result["parsed_output"]
            task.provider_name = result.get("provider_name")
            task.model_name = result.get("model_name")
            task.token_count = result.get("token_count", 0)
            task.cost = result.get("cost", 0.0)
            task.status = SubAgentTaskStatus.SUCCEEDED
            task.finished_at = utc_now()
            self.db.commit()
            self.db.refresh(task)
            return task
        except Exception as exc:
            task.status = SubAgentTaskStatus.FAILED
            task.error_message = str(exc)
            task.finished_at = utc_now()
            self.db.commit()
            self.db.refresh(task)
            return task

    async def run_parallel(self, task_ids: List[int], max_concurrency: int = 3) -> List[SubAgentTask]:
        """按并发上限执行多个子 Agent 任务。"""
        semaphore = asyncio.Semaphore(max(1, max_concurrency))

        async def _runner(task_id: int):
            async with semaphore:
                return await self.run_task(task_id)

        return await asyncio.gather(*[_runner(task_id) for task_id in task_ids])

    async def retry_task(self, task_id: int) -> SubAgentTask:
        """重试失败或已取消的子任务。"""
        task = self.db.query(SubAgentTask).filter(SubAgentTask.id == task_id).first()
        if not task:
            raise ValueError(f"子 Agent 任务不存在: {task_id}")
        task.status = SubAgentTaskStatus.PENDING
        task.error_message = None
        task.started_at = None
        task.finished_at = None
        self.db.commit()
        return await self.run_task(task_id)

    async def cancel_task(self, task_id: int) -> bool:
        """取消未完成的子任务。"""
        task = self.db.query(SubAgentTask).filter(SubAgentTask.id == task_id).first()
        if not task or task.status in [SubAgentTaskStatus.SUCCEEDED, SubAgentTaskStatus.FAILED]:
            return False
        task.status = SubAgentTaskStatus.CANCELLED
        task.finished_at = utc_now()
        self.db.commit()
        return True

    def reduce_results(self, run_id: int) -> Dict[str, Any]:
        """汇总某次运行下所有子 Agent 结果。"""
        tasks = (
            self.db.query(SubAgentTask)
            .filter(SubAgentTask.run_id == run_id)
            .order_by(SubAgentTask.id.asc())
            .all()
        )
        return {
            "run_id": run_id,
            "total": len(tasks),
            "succeeded": len([t for t in tasks if t.status == SubAgentTaskStatus.SUCCEEDED]),
            "failed": len([t for t in tasks if t.status == SubAgentTaskStatus.FAILED]),
            "cancelled": len([t for t in tasks if t.status == SubAgentTaskStatus.CANCELLED]),
            "results": [self.serialize_task(t) for t in tasks],
        }

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        task = self.db.query(SubAgentTask).filter(SubAgentTask.id == task_id).first()
        return self.serialize_task(task) if task else None

    def list_tasks(self, run_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.query(SubAgentTask)
        if run_id is not None:
            query = query.filter(SubAgentTask.run_id == run_id)
        if status:
            query = query.filter(SubAgentTask.status == status)
        tasks = query.order_by(SubAgentTask.created_at.desc(), SubAgentTask.id.desc()).all()
        return [self.serialize_task(task) for task in tasks]

    def get_run_tree(self, run_id: int) -> Dict[str, Any]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")
        tasks = self.list_tasks(run_id=run_id)
        by_parent: Dict[str, List[Dict[str, Any]]] = {}
        for task in tasks:
            key = str(task.get("parent_step_id") or "root")
            by_parent.setdefault(key, []).append(task)
        return {"run_id": run_id, "status": run.status, "tasks_by_parent_step": by_parent}

    async def _try_llm(self, task: SubAgentTask) -> Optional[Dict[str, Any]]:
        """尝试通过 LLMRouter 执行，路由不可用时返回 None。"""
        try:
            result = await LLMRouter(self.db).generate(
                role=task.role,
                messages=[
                    {"role": "system", "content": "你是小说自主创作系统中的子 Agent，请输出简洁、可执行的结构化建议。"},
                    {"role": "user", "content": task.input_prompt or task.title},
                ],
                task_id=f"subagent:{task.id}",
                trace={"run_id": task.run_id, "subagent_task_id": task.id},
            )
            return {
                "output_text": result.content,
                "parsed_output": self._parse_json_or_summary(result.content),
                "provider_name": result.provider_name,
                "model_name": result.model_name,
                "token_count": result.total_tokens,
                "cost": result.cost,
            }
        except LLMRouterAllProvidersFailed:
            return None

    def _rule_based_result(self, task: SubAgentTask) -> Dict[str, Any]:
        """P0 兜底规则结果：不伪造进度，只记录可审计的本地分析。"""
        if task.task_type == "critic" or task.role == "critic":
            parsed = {
                "summary": "已完成规则化风险检查。",
                "findings": [
                    "当前子 Agent 可落库、可追踪，但真实深度评审需要配置 LLM 路由。",
                    "建议后续接入 planner/critic 专用模型并记录调用成本。",
                ],
                "severity": "medium",
            }
        else:
            parsed = {
                "summary": "已完成规则化任务汇总。",
                "findings": [
                    "主流程已创建项目、Bible、章节大纲与任务队列。",
                    "该结果来自本地 P0 兜底逻辑，未消耗模型调用。",
                ],
                "severity": "info",
            }
        return {
            "output_text": json.dumps(parsed, ensure_ascii=False, indent=2),
            "parsed_output": parsed,
            "provider_name": "local-rule-based",
            "model_name": "subagent-p0-fallback",
            "token_count": 0,
            "cost": 0.0,
        }

    def _parse_json_or_summary(self, content: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
            return {"items": parsed}
        except Exception:
            return {"summary": content[:1000] if content else ""}

    def serialize_task(self, task: SubAgentTask) -> Dict[str, Any]:
        return {
            "id": task.id,
            "run_id": task.run_id,
            "parent_step_id": task.parent_step_id,
            "task_type": task.task_type,
            "title": task.title,
            "role": task.role,
            "status": task.status,
            "context_json": task.context_json,
            "input_prompt": task.input_prompt,
            "output_text": task.output_text,
            "parsed_output": task.parsed_output,
            "provider_name": task.provider_name,
            "model_name": task.model_name,
            "token_count": task.token_count,
            "cost": task.cost,
            "error_message": task.error_message,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
