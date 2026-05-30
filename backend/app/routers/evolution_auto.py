"""Evolution Auto Router - 自治进化 API。"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evolution_auto import PromptEvolutionPolicy, PromptEvolutionRun
from app.schemas.evolution_policy import (
    CreateEvolutionPolicyRequest,
    EvolutionPolicyResponse,
    EvolutionRunResponse,
    RollbackEvolutionRequest,
    UpdateEvolutionPolicyRequest,
)
from app.services.evolution_orchestrator import EvolutionOrchestrator

router = APIRouter(prefix="/evolution-auto", tags=["evolution-auto"])


@router.get("/policies", response_model=List[EvolutionPolicyResponse])
async def list_evolution_policies(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取进化策略列表。"""
    query = db.query(PromptEvolutionPolicy)
    if role:
        query = query.filter(PromptEvolutionPolicy.role == role)
    return query.order_by(PromptEvolutionPolicy.created_at.desc()).all()


@router.post("/policies", response_model=EvolutionPolicyResponse)
async def create_evolution_policy(request: CreateEvolutionPolicyRequest, db: Session = Depends(get_db)):
    """创建进化策略。"""
    policy = PromptEvolutionPolicy(
        role=request.role,
        enabled=request.enabled,
        min_sample_count=request.min_sample_count,
        min_average_score=request.min_average_score,
        max_rewrite_rate=request.max_rewrite_rate,
        trigger_window_days=request.trigger_window_days,
        candidate_count=request.candidate_count,
        ab_test_sample_count=request.ab_test_sample_count,
        min_improvement=request.min_improvement,
        auto_apply=request.auto_apply,
        rollout_ratio=request.rollout_ratio,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.patch("/policies/{policy_id}", response_model=EvolutionPolicyResponse)
async def update_evolution_policy(
    policy_id: int,
    request: UpdateEvolutionPolicyRequest,
    db: Session = Depends(get_db),
):
    """更新进化策略。"""
    policy = db.query(PromptEvolutionPolicy).filter(PromptEvolutionPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="进化策略不存在")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy


@router.post("/policies/{policy_id}/run", response_model=EvolutionRunResponse)
async def run_evolution_policy(policy_id: int, db: Session = Depends(get_db)):
    """执行一次进化运行。"""
    orchestrator = EvolutionOrchestrator(db)
    try:
        run = await orchestrator.run_auto_evolution(policy_id)
        return run
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"进化执行失败: {str(exc)}")


@router.get("/runs", response_model=List[EvolutionRunResponse])
async def list_evolution_runs(
    policy_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取进化运行列表。"""
    query = db.query(PromptEvolutionRun)
    if policy_id:
        query = query.filter(PromptEvolutionRun.policy_id == policy_id)
    if role:
        query = query.filter(PromptEvolutionRun.role == role)
    if status:
        query = query.filter(PromptEvolutionRun.status == status)
    return query.order_by(PromptEvolutionRun.created_at.desc()).limit(limit).all()


@router.get("/runs/{run_id}", response_model=EvolutionRunResponse)
async def get_evolution_run(run_id: int, db: Session = Depends(get_db)):
    """获取进化运行详情。"""
    run = db.query(PromptEvolutionRun).filter(PromptEvolutionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="进化运行不存在")
    return run


@router.post("/runs/{run_id}/rollback")
async def rollback_evolution_run(
    run_id: int,
    request: RollbackEvolutionRequest,
    db: Session = Depends(get_db),
):
    """回滚进化运行。"""
    orchestrator = EvolutionOrchestrator(db)
    try:
        result = await orchestrator.rollback(run_id, reason=request.reason)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
