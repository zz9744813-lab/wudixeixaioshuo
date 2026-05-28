"""
Evolution Router - 进化路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evolution import EvolutionRun

router = APIRouter()


# Pydantic 模型
class EvolutionResponse(BaseModel):
    id: int
    project_id: int
    target_type: str
    target_name: Optional[str]
    before_score: Optional[float]
    after_score: Optional[float]
    improvement: Optional[float]
    decision: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[EvolutionResponse])
async def list_evolutions(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取进化记录列表"""
    query = db.query(EvolutionRun)
    if project_id:
        query = query.filter(EvolutionRun.project_id == project_id)

    evolutions = query.order_by(EvolutionRun.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": e.id,
            "project_id": e.project_id,
            "target_type": e.target_type,
            "target_name": e.target_name,
            "before_score": e.before_score,
            "after_score": e.after_score,
            "improvement": e.improvement,
            "decision": e.decision,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in evolutions
    ]


@router.get("/{evolution_id}")
async def get_evolution(evolution_id: int, db: Session = Depends(get_db)):
    """获取进化记录详情"""
    evolution = db.query(EvolutionRun).filter(EvolutionRun.id == evolution_id).first()
    if not evolution:
        raise HTTPException(status_code=404, detail="进化记录不存在")

    return {
        "id": evolution.id,
        "project_id": evolution.project_id,
        "target_type": evolution.target_type,
        "target_name": evolution.target_name,
        "before_version": evolution.before_version,
        "after_version": evolution.after_version,
        "before_score": evolution.before_score,
        "after_score": evolution.after_score,
        "improvement": evolution.improvement,
        "decision": evolution.decision,
        "reason": evolution.reason,
        "test_sample_count": evolution.test_sample_count,
        "judge_agents": evolution.judge_agents,
        "created_at": evolution.created_at.isoformat() if evolution.created_at else None,
        "decided_at": evolution.decided_at.isoformat() if evolution.decided_at else None,
    }
