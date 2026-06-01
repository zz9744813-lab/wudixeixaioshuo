"""NovelForge AI - Agent runner: executes pipeline steps and persists state."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.errors import NovelForgeError
from app.models.entities import AgentRun, AgentStep
from app.services.llm_router import call_llm
from app.services.pipeline_service import (
    run_planner,
    run_drafter,
    run_critic,
    run_rewriter,
    run_continuity_checker,
    run_memory_updater,
)
from app.services.usage_service import record_usage

logger = logging.getLogger("novelforge.agent")


STEP_ORDER = [
    "planner",
    "drafter",
    "critic",
    "rewriter",
    "continuity_checker",
    "memory_updater",
]


async def _exec_step(db: Session, run: AgentRun, step: AgentStep) -> None:
    """
    Execute a single agent step using the appropriate pipeline function.
    In P1 we still call stubs; in P2 these call llm_router for real.
    """
    now = datetime.now(timezone.utc)
    step.status = "running"
    step.started_at = now
    step.provider_name = "stub"
    step.model_name = "stub-model"
    db.add(step)
    db.commit()
    db.refresh(step)

    try:
        if step.agent_name == "planner":
            result = run_planner(project_id=str(run.project_id), chapter_index=run.chapter_index, context={})
        elif step.agent_name == "drafter":
            result = run_drafter(plan={}, context={})
        elif step.agent_name == "critic":
            result = run_critic(content="", plan={})  # type: ignore[arg-type]
        elif step.agent_name == "rewriter":
            result = run_rewriter(content="", plan={}, critic={})  # type: ignore[arg-type]
        elif step.agent_name == "continuity_checker":
            result = run_continuity_checker(content="", project_id=str(run.project_id), chapter_index=run.chapter_index)
        elif step.agent_name == "memory_updater":
            result = run_memory_updater(project_id=str(run.project_id), chapter_index=run.chapter_index, content="")
        else:
            raise NovelForgeError("unknown_step", f"Unknown step: {step.agent_name}")

        step.status = "completed"
        step.raw_output = str(result)
        step.parsed_output = result
        step.finished_at = datetime.now(timezone.utc)

        # Usage bookkeeping (stub values for P1)
        record_usage(
            db,
            project_id=str(run.project_id),
            run_id=str(run.id),
            provider_id=None,
            provider_name="stub",
            model_name="stub",
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
            category=step.agent_name,
        )

        db.commit()

    except Exception as exc:
        logger.exception("step failed run=%s step=%s", run.id, step.id)
        step.status = "failed"
        step.error_message = str(exc)
        step.finished_at = datetime.now(timezone.utc)
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()


async def execute_run(db: Session, run_id: str) -> None:
    """
    Drive a single AgentRun through all 6 steps sequentially.
    """
    run = db.get(AgentRun, run_id)
    if not run:
        raise NovelForgeError("not_found", f"AgentRun {run_id} not found", status=404)

    if run.status == "completed":
        return

    run.status = "running"
    started_now = datetime.now(timezone.utc)
    run.started_at = run.started_at or started_now
    db.add(run)
    db.commit()

    for idx, role in enumerate(STEP_ORDER):
        existing = (
            db.query(AgentStep)
            .filter(AgentStep.run_id == run.id, AgentStep.agent_name == role)
            .first()
        )
        if not existing:
            step = AgentStep(
                run_id=run.id,
                step_index=idx,
                agent_name=role,
                status="pending",
            )
            db.add(step)
            db.commit()
            db.refresh(step)
        else:
            step = existing

        run.current_step = role
        db.add(run)
        db.commit()

        await _exec_step(db, run, step)

        if step.status == "failed":
            run.status = "failed"
            run.error_message = step.error_message
            db.commit()
            return

    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
