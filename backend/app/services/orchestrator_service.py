"""Orchestrator Service - 主 Agent 编排服务。"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_run import (
    AgentPlan,
    AgentPlanStatus,
    AgentRun,
    AgentRunStatus,
    AgentStep,
    AgentStepStatus,
)
from app.services.agent_planner_service import AgentPlannerService
from app.services.agent_tool_registry import AgentToolRegistry
from app.utils.time_utils import utc_now


class OrchestratorService:
    def __init__(self, db: Session):
        self.db = db
        self.registry = AgentToolRegistry(db)

    async def start_run(
        self,
        user_request: str,
        project_id: Optional[int] = None,
        mode: str = "autonomous",
        budget_tokens: Optional[int] = None,
        budget_cost: Optional[float] = None,
        max_steps: int = 30,
        max_retries: int = 2,
        max_concurrency: int = 3,
    ) -> AgentRun:
        run = AgentRun(
            project_id=project_id,
            user_request=user_request,
            mode=mode,
            status=AgentRunStatus.PENDING,
            budget_tokens=budget_tokens,
            budget_cost=budget_cost,
            max_steps=max_steps,
            max_retries=max_retries,
            max_concurrency=max_concurrency,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_run(self, run_id: int) -> AgentRun:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")
        if run.status == AgentRunStatus.CANCELLED:
            return run

        run.status = AgentRunStatus.RUNNING
        run.started_at = utc_now()
        self.db.commit()

        try:
            plan = await self._create_plan(run)
            if run.mode == "require_approval":
                run.status = AgentRunStatus.PAUSED
                run.final_report = json.dumps({"paused_reason": "等待用户确认计划", "plan_id": plan.id}, ensure_ascii=False)
                self.db.commit()
                return run

            await self._execute_plan(run, plan)
            if run.status == AgentRunStatus.RUNNING:
                run.status = AgentRunStatus.SUCCEEDED
                run.finished_at = utc_now()
        except Exception as e:
            self.db.rollback()
            run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
            if run is not None:
                run.status = AgentRunStatus.FAILED
                run.error_message = str(e)
                run.finished_at = utc_now()
                self.db.commit()
            else:
                raise
        finally:
            self.db.commit()
        return run

    async def _create_plan(self, run: AgentRun) -> AgentPlan:
        existing = self.db.query(AgentPlan).filter(AgentPlan.run_id == run.id).first()
        if existing:
            return existing

        plan_json = await AgentPlannerService(self.db).create_plan(
            user_request=run.user_request,
            project_id=run.project_id,
            max_steps=run.max_steps or 30,
        )
        planner_model = plan_json.pop("planner_model", "rule-based-p0")
        planner_source = plan_json.pop("planner_source", "fallback")
        plan_json["planner_source"] = planner_source
        plan = AgentPlan(
            run_id=run.id,
            title=plan_json["title"],
            summary=plan_json["summary"],
            plan_json=plan_json,
            planner_model=planner_model,
            status=AgentPlanStatus.CREATED,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        for spec in plan_json["steps"]:
            self.db.add(AgentStep(
                run_id=run.id,
                plan_id=plan.id,
                step_key=spec["step_key"],
                title=spec["title"],
                tool_name=spec["tool_name"],
                args_json=spec.get("args") or {},
                depends_on=spec.get("depends_on") or [],
                status=AgentStepStatus.PENDING,
                created_at=utc_now(),
            ))
        self.db.commit()
        return plan

    async def _execute_plan(self, run: AgentRun, plan: AgentPlan):
        plan.status = AgentPlanStatus.EXECUTING
        self.db.commit()

        context: Dict[str, Any] = {
            "run_id": run.id,
            "project_id": run.project_id,
            "user_request": run.user_request,
            "steps_executed": [],
            "outputs": {},
        }
        steps = self.db.query(AgentStep).filter(AgentStep.plan_id == plan.id).order_by(AgentStep.id.asc()).all()
        executed = set()

        for step in steps:
            if not self._check_budget(run, len(executed)):
                run.status = AgentRunStatus.PAUSED
                run.error_message = "预算或最大步骤数超限，已暂停"
                run.final_report = json.dumps({
                    "paused_reason": run.error_message,
                    "budget_tokens": run.budget_tokens,
                    "used_tokens": run.used_tokens,
                    "budget_cost": run.budget_cost,
                    "used_cost": run.used_cost,
                    "max_steps": run.max_steps,
                    "executed_steps": len(executed),
                }, ensure_ascii=False, indent=2)
                break
            missing = [dep for dep in (step.depends_on or []) if dep not in executed]
            if missing:
                step.status = AgentStepStatus.SKIPPED
                step.error_message = f"依赖未完成: {missing}"
                self.db.commit()
                continue

            step.status = AgentStepStatus.RUNNING
            step.started_at = utc_now()
            step.attempt_count += 1
            step.input_snapshot = {"context_keys": list(context.keys()), "args": step.args_json or {}}
            self.db.commit()

            try:
                context["current_step_id"] = step.id
                output = await self.registry.call(step.tool_name, step.args_json or {}, context)
                step.output_json = output
                step.status = AgentStepStatus.SUCCEEDED
                step.finished_at = utc_now()
                executed.add(step.step_key)
                context["steps_executed"].append(step.step_key)
                context["outputs"][step.step_key] = output
                if context.get("project_id") and run.project_id != context.get("project_id"):
                    run.project_id = context.get("project_id")
                if step.step_key == "build_report":
                    output.setdefault("budget", {
                        "budget_tokens": run.budget_tokens,
                        "used_tokens": run.used_tokens,
                        "budget_cost": run.budget_cost,
                        "used_cost": run.used_cost,
                        "max_steps": run.max_steps,
                        "executed_steps": len(executed),
                    })
                    run.final_report = json.dumps(output, ensure_ascii=False, indent=2)
                self.db.commit()
            except Exception as exc:
                step.status = AgentStepStatus.FAILED
                step.error_message = str(exc)
                step.finished_at = utc_now()
                run.status = AgentRunStatus.FAILED
                run.error_message = f"步骤 {step.step_key} 失败: {exc}"
                self.db.commit()
                return

        if run.status == AgentRunStatus.RUNNING:
            plan.status = AgentPlanStatus.DONE
        elif run.status == AgentRunStatus.FAILED:
            plan.status = AgentPlanStatus.FAILED
        self.db.commit()

    def _check_budget(self, run: AgentRun, executed_steps: int) -> bool:
        if run.max_steps is not None and executed_steps >= run.max_steps:
            return False
        if run.budget_tokens is not None and (run.used_tokens or 0) >= run.budget_tokens:
            return False
        if run.budget_cost is not None and (run.used_cost or 0) >= run.budget_cost:
            return False
        return True

    async def resume_run(self, run_id: int) -> AgentRun:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")
        if run.status != AgentRunStatus.PAUSED:
            return run
        run.status = AgentRunStatus.RUNNING
        run.error_message = None
        run.finished_at = None
        self.db.commit()
        plan = self.db.query(AgentPlan).filter(AgentPlan.run_id == run.id).order_by(AgentPlan.id.desc()).first()
        if not plan:
            return await self.execute_run(run_id)
        await self._execute_plan(run, plan)
        if run.status == AgentRunStatus.RUNNING:
            run.status = AgentRunStatus.SUCCEEDED
            run.finished_at = utc_now()
            self.db.commit()
        return run

    def get_run_steps(self, run_id: int) -> List[Dict[str, Any]]:
        status = self.get_run_status(run_id)
        return status["steps"] if status else []

    def get_run_report(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return None
        if not run.final_report:
            return {"run_id": run.id, "status": run.status, "final_report": None}
        try:
            parsed = json.loads(run.final_report)
        except json.JSONDecodeError:
            parsed = {"text": run.final_report}
        return {"run_id": run.id, "status": run.status, "report": parsed}

    def get_run_events(self, run_id: int) -> List[Dict[str, Any]]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return []
        steps = self.db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.id.asc()).all()
        events: List[Dict[str, Any]] = []
        if run.started_at:
            events.append({"event": "agent_run_started", "run_id": run.id, "timestamp": run.started_at.isoformat()})
        for step in steps:
            if step.started_at:
                events.append({
                    "event": "agent_step_started",
                    "run_id": run.id,
                    "step_id": step.id,
                    "title": step.title,
                    "timestamp": step.started_at.isoformat(),
                })
            if step.finished_at:
                event_name = "agent_step_succeeded" if step.status == AgentStepStatus.SUCCEEDED else "agent_step_failed"
                events.append({
                    "event": event_name,
                    "run_id": run.id,
                    "step_id": step.id,
                    "title": step.title,
                    "status": step.status,
                    "error_message": step.error_message,
                    "timestamp": step.finished_at.isoformat(),
                })
        if run.finished_at:
            events.append({"event": "agent_run_finished", "run_id": run.id, "status": run.status, "timestamp": run.finished_at.isoformat()})
        elif run.status == AgentRunStatus.PAUSED:
            events.append({"event": "agent_run_paused", "run_id": run.id, "status": run.status, "error_message": run.error_message})
        return events

    async def cancel_run(self, run_id: int) -> bool:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run or run.status in [AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]:
            return False
        run.status = AgentRunStatus.CANCELLED
        run.finished_at = utc_now()
        self.db.commit()
        return True

    def get_run_status(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return None
        plans = self.db.query(AgentPlan).filter(AgentPlan.run_id == run_id).order_by(AgentPlan.id.asc()).all()
        steps = self.db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.id.asc()).all()
        return {
            "id": run.id,
            "status": run.status,
            "mode": run.mode,
            "user_request": run.user_request,
            "project_id": run.project_id,
            "budget_tokens": run.budget_tokens,
            "budget_cost": run.budget_cost,
            "used_tokens": run.used_tokens,
            "used_cost": run.used_cost,
            "max_steps": run.max_steps,
            "max_retries": run.max_retries,
            "max_concurrency": run.max_concurrency,
            "plans": [{"id": p.id, "title": p.title, "summary": p.summary, "status": p.status, "plan_json": p.plan_json} for p in plans],
            "steps": [{
                "id": s.id,
                "step_key": s.step_key,
                "title": s.title,
                "tool_name": s.tool_name,
                "status": s.status,
                "attempt_count": s.attempt_count,
                "depends_on": s.depends_on,
                "input_snapshot": s.input_snapshot,
                "output_json": s.output_json,
                "error_message": s.error_message,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            } for s in steps],
            "final_report": run.final_report,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }

    def get_runs(self, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        query = self.db.query(AgentRun)
        if status:
            query = query.filter(AgentRun.status == status)
        runs = query.order_by(AgentRun.created_at.desc()).offset(offset).limit(limit).all()
        return [{
            "id": r.id,
            "status": r.status,
            "mode": r.mode,
            "user_request": r.user_request,
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        } for r in runs]


def get_orchestrator_service(db: Session) -> OrchestratorService:
    return OrchestratorService(db)
