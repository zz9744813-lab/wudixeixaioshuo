"""Orchestrator Service - 主Agent编排服务"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.agent_run import AgentRun, AgentRunStatus, AgentPlan, AgentPlanStatus, AgentStep, AgentStepStatus
from app.utils.time_utils import utc_now

class OrchestratorService:
    def __init__(self, db: Session):
        self.db = db
        self._running_runs: Dict[int, asyncio.Task] = {}

    async def start_run(self, user_request: str, project_id: Optional[int] = None, mode: str = "autonomous",
                       budget_tokens: Optional[int] = None, budget_cost: Optional[float] = None,
                       max_steps: int = 30, max_retries: int = 2, max_concurrency: int = 3) -> AgentRun:
        run = AgentRun(
            project_id=project_id, user_request=user_request, mode=mode, status=AgentRunStatus.PENDING,
            budget_tokens=budget_tokens, budget_cost=budget_cost, max_steps=max_steps,
            max_retries=max_retries, max_concurrency=max_concurrency,
            created_at=utc_now(), updated_at=utc_now()
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_run(self, run_id: int) -> AgentRun:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")
        run.status = AgentRunStatus.RUNNING
        run.started_at = utc_now()
        self.db.commit()

        try:
            await self._execute_default_plan(run)
            if run.status == AgentRunStatus.RUNNING:
                run.status = AgentRunStatus.SUCCEEDED
                run.finished_at = utc_now()
        except Exception as e:
            run.status = AgentRunStatus.FAILED
            run.error_message = str(e)
            run.finished_at = utc_now()
        finally:
            self.db.commit()
        return run

    async def _execute_default_plan(self, run: AgentRun):
        steps = [
            {"key": "parse_request", "title": "解析需求", "tool": "parse"},
            {"key": "create_project", "title": "创建项目", "tool": "create_project"},
            {"key": "generate_bible", "title": "生成Bible", "tool": "generate_bible"},
            {"key": "plan_outline", "title": "规划大纲", "tool": "plan_outline"},
            {"key": "build_report", "title": "生成报告", "tool": "report"}
        ]

        context = {"run_id": run.id, "user_request": run.user_request, "steps_executed": []}

        for step_data in steps:
            if not self._check_budget(run):
                run.status = AgentRunStatus.PAUSED
                run.error_message = "预算超限"
                break

            step = AgentStep(
                run_id=run.id, plan_id=0, step_key=step_data["key"], title=step_data["title"],
                tool_name=step_data["tool"], args_json={}, depends_on=[],
                status=AgentStepStatus.RUNNING, started_at=utc_now()
            )
            self.db.add(step)
            self.db.commit()

            await asyncio.sleep(0.5)

            step.status = AgentStepStatus.SUCCEEDED
            step.finished_at = utc_now()
            step.output_json = {"success": True, "step": step_data["key"]}
            self.db.commit()
            context["steps_executed"].append(step_data["key"])

        run.final_report = json.dumps({"success": True, "steps": context["steps_executed"]}, ensure_ascii=False)

    def _check_budget(self, run: AgentRun) -> bool:
        if run.budget_tokens and run.used_tokens >= run.budget_tokens:
            return False
        if run.budget_cost and run.used_cost >= run.budget_cost:
            return False
        return True

    async def cancel_run(self, run_id: int) -> bool:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run or run.status in ["succeeded", "failed", "cancelled"]:
            return False
        run.status = AgentRunStatus.CANCELLED
        run.finished_at = utc_now()
        self.db.commit()
        return True

    def get_run_status(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return None
        steps = self.db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.created_at).all()
        return {
            "id": run.id, "status": run.status, "mode": run.mode,
            "user_request": run.user_request, "project_id": run.project_id,
            "budget": {"tokens": {"used": run.used_tokens, "budget": run.budget_tokens},
                      "cost": {"used": run.used_cost, "budget": run.budget_cost}},
            "steps": [{"id": s.id, "step_key": s.step_key, "title": s.title, "tool_name": s.tool_name,
                      "status": s.status} for s in steps],
            "final_report": run.final_report, "error_message": run.error_message
        }

    def get_runs(self, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        query = self.db.query(AgentRun)
        if status:
            query = query.filter(AgentRun.status == status)
        runs = query.order_by(AgentRun.created_at.desc()).offset(offset).limit(limit).all()
        return [{"id": r.id, "status": r.status, "mode": r.mode,
                "user_request": r.user_request[:100] + "..." if len(r.user_request) > 100 else r.user_request,
                "project_id": r.project_id, "created_at": r.created_at.isoformat() if r.created_at else None}
                for r in runs]

def get_orchestrator_service(db: Session) -> OrchestratorService:
    return OrchestratorService(db)
