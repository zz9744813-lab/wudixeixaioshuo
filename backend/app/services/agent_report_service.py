"""Agent Report Service - Agent 运行报告生成服务。"""

import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.agent_run import (
    AgentPlan,
    AgentRun,
    AgentRunStatus,
    AgentStep,
    AgentStepStatus,
    SubAgentTask,
    SubAgentTaskStatus,
)
from app.utils.time_utils import utc_now


class AgentReportService:
    """为 AgentRun 生成结构化运行报告。"""

    def __init__(self, db: Session):
        self.db = db

    def generate_report(self, run_id: int) -> Dict[str, Any]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")

        plan = self.db.query(AgentPlan).filter(AgentPlan.run_id == run_id).order_by(AgentPlan.id.desc()).first()
        steps = self.db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.id.asc()).all()
        subtasks = self.db.query(SubAgentTask).filter(SubAgentTask.run_id == run_id).order_by(SubAgentTask.id.asc()).all()

        total_tokens = sum(s.total_tokens or 0 for s in steps)
        total_cost = sum(s.cost or 0.0 for s in steps)
        subtask_tokens = sum(t.token_count or 0 for t in subtasks)
        subtask_cost = sum(t.cost or 0.0 for t in subtasks)

        succeeded_steps = [s for s in steps if s.status == AgentStepStatus.SUCCEEDED]
        failed_steps = [s for s in steps if s.status == AgentStepStatus.FAILED]
        skipped_steps = [s for s in steps if s.status == AgentStepStatus.SKIPPED]

        succeeded_subtasks = [t for t in subtasks if t.status == SubAgentTaskStatus.SUCCEEDED]
        failed_subtasks = [t for t in subtasks if t.status == SubAgentTaskStatus.FAILED]

        report = {
            "title": "自主 Agent 运行报告",
            "run_id": run.id,
            "status": run.status,
            "mode": run.mode,
            "user_request": run.user_request,
            "project_id": run.project_id,
            "plan": {
                "id": plan.id if plan else None,
                "title": plan.title if plan else None,
                "summary": plan.summary if plan else None,
                "planner_model": plan.planner_model if plan else None,
            },
            "steps_summary": {
                "total": len(steps),
                "succeeded": len(succeeded_steps),
                "failed": len(failed_steps),
                "skipped": len(skipped_steps),
                "steps": [
                    {
                        "id": s.id,
                        "step_key": s.step_key,
                        "title": s.title,
                        "tool_name": s.tool_name,
                        "status": s.status,
                        "attempt_count": s.attempt_count,
                        "tokens": s.total_tokens or 0,
                        "cost": s.cost or 0.0,
                        "error": s.error_message,
                    }
                    for s in steps
                ],
            },
            "subagents_summary": {
                "total": len(subtasks),
                "succeeded": len(succeeded_subtasks),
                "failed": len(failed_subtasks),
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "role": t.role,
                        "task_type": t.task_type,
                        "status": t.status,
                        "provider": t.provider_name,
                        "model": t.model_name,
                        "tokens": t.token_count or 0,
                        "cost": t.cost or 0.0,
                    }
                    for t in subtasks
                ],
            },
            "cost_summary": {
                "total_tokens": total_tokens + subtask_tokens,
                "total_cost": round(total_cost + subtask_cost, 6),
                "step_tokens": total_tokens,
                "step_cost": round(total_cost, 6),
                "subagent_tokens": subtask_tokens,
                "subagent_cost": round(subtask_cost, 6),
                "budget_tokens": run.budget_tokens,
                "budget_cost": run.budget_cost,
                "used_tokens": run.used_tokens or 0,
                "used_cost": run.used_cost or 0.0,
            },
            "timeline": {
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            },
            "error": run.error_message,
        }

        run.final_report = json.dumps(report, ensure_ascii=False, indent=2)
        run.updated_at = utc_now()
        self.db.commit()
        return report
