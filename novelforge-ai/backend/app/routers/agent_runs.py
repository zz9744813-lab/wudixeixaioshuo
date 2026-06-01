from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import AgentRun, AgentStep
from app.schemas.agent import AgentRunCreate, AgentRunOut, AgentRunListResponse
from app.services.agent_service import execute_run

router = APIRouter()


@router.post("/runs", response_model=AgentRunOut, status_code=201)
async def create_run(payload: AgentRunCreate, db: Session = Depends(get_db)):
    run = AgentRun(
        job_id=None,
        project_id=payload.project_id,
        chapter_id=payload.chapter_id,
        chapter_index=payload.chapter_index or 0,
        status="pending",
        total_steps=6,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return AgentRunOut(
        id=run.id,
        project_id=run.project_id,
        chapter_index=run.chapter_index,
        status=run.status,
        current_step=run.current_step,
        total_steps=run.total_steps,
        final_score=run.final_score,
        word_count=run.word_count,
        total_tokens=run.total_tokens,
        total_cost=run.total_cost,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@router.get("/projects/{project_id}/runs", response_model=AgentRunListResponse)
async def list_runs(project_id: str, db: Session = Depends(get_db)):
    stmt = (
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(desc(AgentRun.created_at))
    )
    items = list(db.execute(stmt).scalars().all())
    return AgentRunListResponse(
        items=[
            AgentRunOut(
                id=r.id,
                project_id=r.project_id,
                chapter_index=r.chapter_index,
                status=r.status,
                current_step=r.current_step,
                total_steps=r.total_steps,
                final_score=r.final_score,
                word_count=r.word_count,
                total_tokens=r.total_tokens,
                total_cost=r.total_cost,
                error_message=r.error_message,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )
            for r in items
        ],
        total=len(items),
    )


@router.get("/runs/{run_id}", response_model=AgentRunOut)
async def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="run not found")
    steps_stmt = select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_index)
    steps = list(db.execute(steps_stmt).scalars().all())
    return AgentRunOut(
        id=run.id,
        project_id=run.project_id,
        chapter_index=run.chapter_index,
        status=run.status,
        current_step=run.current_step,
        total_steps=run.total_steps,
        final_score=run.final_score,
        word_count=run.word_count,
        total_tokens=run.total_tokens,
        total_cost=run.total_cost,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=[
            AgentStepOut(
                id=s.id,
                agent_name=s.agent_name,
                status=s.status,
                model_name=s.model_name,
                input_tokens=s.input_tokens,
                output_tokens=s.output_tokens,
                cost=float(s.cost),
                error_message=s.error_message,
                started_at=s.started_at,
                finished_at=s.finished_at,
            )
            for s in steps
        ],
    )


@router.post("/runs/{run_id}/execute", response_model=AgentRunOut)
async def execute_run_endpoint(run_id: str, db: Session = Depends(get_db)):
    await execute_run(db, run_id)
    return await get_run(run_id, db)
