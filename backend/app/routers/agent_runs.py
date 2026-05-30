"""Agent Runs Router"""
from typing import List, Optional
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.services.orchestrator_service import OrchestratorService, get_orchestrator_service

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])

class CreateAgentRunRequest(BaseModel):
    user_request: str = Field(..., description="用户创作需求")
    project_id: Optional[int] = None
    mode: str = "autonomous"
    budget_tokens: Optional[int] = None
    budget_cost: Optional[float] = None
    max_steps: int = 30

class AgentRunResponse(BaseModel):
    id: int
    status: str
    mode: str
    user_request: str
    class Config:
        from_attributes = True

@router.post("", response_model=AgentRunResponse)
async def create_agent_run(request: CreateAgentRunRequest, db: Session = Depends(get_db)):
    service = get_orchestrator_service(db)
    run = await service.start_run(
        user_request=request.user_request, project_id=request.project_id, mode=request.mode,
        budget_tokens=request.budget_tokens, budget_cost=request.budget_cost, max_steps=request.max_steps
    )
    return {"id": run.id, "status": run.status, "mode": run.mode, "user_request": run.user_request}

@router.get("")
async def list_agent_runs(status: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db)):
    service = get_orchestrator_service(db)
    return service.get_runs(status=status, limit=limit)

@router.get("/{run_id}")
async def get_agent_run(run_id: int, db: Session = Depends(get_db)):
    service = get_orchestrator_service(db)
    status = service.get_run_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    return status

async def _execute_agent_run_in_background(run_id: int):
    db = SessionLocal()
    try:
        await OrchestratorService(db).execute_run(run_id)
    finally:
        db.close()

@router.post("/{run_id}/start")
async def start_agent_run(run_id: int):
    asyncio.create_task(_execute_agent_run_in_background(run_id))
    return {"message": "运行已启动", "run_id": run_id}

@router.post("/{run_id}/cancel")
async def cancel_agent_run(run_id: int, db: Session = Depends(get_db)):
    service = get_orchestrator_service(db)
    success = await service.cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法取消运行")
    return {"message": "运行已取消", "run_id": run_id}
