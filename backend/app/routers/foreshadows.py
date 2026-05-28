"""
Foreshadow API 路由 - 伏笔管理
P4 Phase 3
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.foreshadow import Foreshadow, ForeshadowPlan
from app.services.foreshadow_service import ForeshadowService

router = APIRouter(prefix="/foreshadows", tags=["foreshadows"])


# ========== Request/Response Models ==========

class ForeshadowCreate(BaseModel):
    title: str
    foreshadow_type: str = "item"
    setup_chapter: Optional[int] = None
    expected_payoff_chapter: Optional[int] = None
    setup_content: str = ""
    payoff_plan: str = ""
    related_characters: Optional[List[str]] = None
    related_items: Optional[List[str]] = None
    importance_score: float = 0.5


class ForeshadowUpdate(BaseModel):
    title: Optional[str] = None
    expected_payoff_chapter: Optional[int] = None
    payoff_plan: Optional[str] = None
    importance_score: Optional[float] = None
    status: Optional[str] = None


class ForeshadowPlanResponse(BaseModel):
    chapter_index: int
    new_foreshadows: List[dict]
    develop_foreshadow_ids: List[int]
    payoff_foreshadow_ids: List[int]
    risky_foreshadow_ids: List[int]


# ========== CRUD Endpoints ==========

@router.post("/projects/{project_id}", response_model=dict)
def create_foreshadow(
    project_id: int,
    data: ForeshadowCreate,
    db: Session = Depends(get_db)
):
    """创建伏笔"""
    service = ForeshadowService(db)
    foreshadow = service.create_foreshadow(
        project_id=project_id,
        title=data.title,
        foreshadow_type=data.foreshadow_type,
        setup_chapter=data.setup_chapter,
        expected_payoff_chapter=data.expected_payoff_chapter,
        setup_content=data.setup_content,
        payoff_plan=data.payoff_plan,
        related_characters=data.related_characters,
        related_items=data.related_items,
        importance_score=data.importance_score
    )
    return {
        "id": foreshadow.id,
        "title": foreshadow.title,
        "status": foreshadow.status,
        "created": True
    }


@router.get("/projects/{project_id}")
def list_foreshadows(
    project_id: int,
    status: Optional[str] = None,
    foreshadow_type: Optional[str] = None,
    min_importance: float = 0.0,
    db: Session = Depends(get_db)
):
    """列示项目伏笔"""
    service = ForeshadowService(db)
    foreshadows = service.list_foreshadows(
        project_id=project_id,
        status=status,
        foreshadow_type=foreshadow_type,
        min_importance=min_importance
    )
    return [{
        "id": f.id,
        "title": f.title,
        "type": f.foreshadow_type,
        "status": f.status,
        "importance": f.importance_score,
        "setup_chapter": f.setup_chapter,
        "expected_payoff": f.expected_payoff_chapter,
        "actual_payoff": f.actual_payoff_chapter,
        "risk_score": f.risk_score
    } for f in foreshadows]


@router.get("/{foreshadow_id}")
def get_foreshadow(foreshadow_id: int, db: Session = Depends(get_db)):
    """获取伏笔详情"""
    service = ForeshadowService(db)
    f = service.get_foreshadow(foreshadow_id)
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {
        "id": f.id,
        "title": f.title,
        "type": f.foreshadow_type,
        "status": f.status,
        "setup_chapter": f.setup_chapter,
        "setup_content": f.setup_content,
        "expected_payoff": f.expected_payoff_chapter,
        "actual_payoff": f.actual_payoff_chapter,
        "payoff_plan": f.payoff_plan,
        "payoff_content": f.payoff_content,
        "development_notes": f.development_notes,
        "related_characters": f.related_characters,
        "related_items": f.related_items,
        "importance": f.importance_score,
        "risk_score": f.risk_score
    }


@router.put("/{foreshadow_id}")
def update_foreshadow(
    foreshadow_id: int,
    data: ForeshadowUpdate,
    db: Session = Depends(get_db)
):
    """更新伏笔"""
    service = ForeshadowService(db)
    f = service.update_foreshadow(
        foreshadow_id=foreshadow_id,
        **data.dict(exclude_unset=True)
    )
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {"updated": True}


# ========== Lifecycle Endpoints ==========

@router.post("/{foreshadow_id}/mark-planted")
def mark_as_planted(
    foreshadow_id: int,
    setup_chapter: int,
    setup_content: str = "",
    db: Session = Depends(get_db)
):
    """标记伏笔已埋设"""
    service = ForeshadowService(db)
    f = service.mark_as_planted(foreshadow_id, setup_chapter, setup_content)
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {"status": "planted", "setup_chapter": setup_chapter}


@router.post("/{foreshadow_id}/mark-developed")
def mark_as_developed(
    foreshadow_id: int,
    chapter_index: int,
    development_note: str = "",
    db: Session = Depends(get_db)
):
    """标记伏笔已推进"""
    service = ForeshadowService(db)
    f = service.mark_as_developed(foreshadow_id, chapter_index, development_note)
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {"status": "developed", "chapter": chapter_index}


@router.post("/{foreshadow_id}/mark-ready")
def mark_as_ready(foreshadow_id: int, db: Session = Depends(get_db)):
    """标记伏笔准备回收"""
    service = ForeshadowService(db)
    f = service.mark_as_ready_to_payoff(foreshadow_id)
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {"status": "ready_to_payoff"}


@router.post("/{foreshadow_id}/mark-paid-off")
def mark_as_paid_off(
    foreshadow_id: int,
    payoff_chapter: int,
    payoff_content: str = "",
    db: Session = Depends(get_db)
):
    """标记伏笔已回收"""
    service = ForeshadowService(db)
    f = service.mark_as_paid_off(foreshadow_id, payoff_chapter, payoff_content)
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {"status": "paid_off", "payoff_chapter": payoff_chapter}


@router.post("/{foreshadow_id}/mark-abandoned")
def mark_as_abandoned(
    foreshadow_id: int,
    reason: str = "",
    db: Session = Depends(get_db)
):
    """标记伏笔废弃"""
    service = ForeshadowService(db)
    f = service.mark_as_abandoned(foreshadow_id, reason)
    if not f:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return {"status": "abandoned"}


# ========== Plan Endpoints ==========

@router.post("/projects/{project_id}/plan-for-chapter/{chapter_id}")
def create_chapter_plan(
    project_id: int,
    chapter_id: int,
    chapter_index: int,
    db: Session = Depends(get_db)
):
    """为章节创建伏笔计划"""
    service = ForeshadowService(db)
    plan = service.create_chapter_plan(project_id, chapter_id, chapter_index)

    # 展开ID为详情
    develop_details = []
    for fid in plan.develop_foreshadow_ids[:5]:
        f = service.get_foreshadow(fid)
        if f:
            develop_details.append({"id": f.id, "title": f.title, "setup_chapter": f.setup_chapter})

    payoff_details = []
    for fid in plan.payoff_foreshadow_ids:
        f = service.get_foreshadow(fid)
        if f:
            payoff_details.append({"id": f.id, "title": f.title, "payoff_plan": f.payoff_plan})

    risky_details = []
    for fid in plan.risky_foreshadow_ids[:3]:
        f = service.get_foreshadow(fid)
        if f:
            risky_details.append({"id": f.id, "title": f.title, "risk_score": f.risk_score})

    return {
        "plan_id": plan.id,
        "chapter_index": plan.chapter_index,
        "new_foreshadows": plan.new_foreshadows,
        "develop_foreshadows": develop_details,
        "payoff_foreshadows": payoff_details,
        "risky_foreshadows": risky_details,
        "prompt_text": service.format_plan_for_prompt(plan)
    }


@router.get("/projects/{project_id}/plan-for-chapter/{chapter_index}")
def get_chapter_plan(
    project_id: int,
    chapter_index: int,
    db: Session = Depends(get_db)
):
    """获取章节伏笔计划"""
    service = ForeshadowService(db)
    plan = service.get_chapter_plan(project_id, chapter_index=chapter_index)
    if not plan:
        raise HTTPException(status_code=404, detail="伏笔计划不存在")
    return {
        "plan_id": plan.id,
        "chapter_index": plan.chapter_index,
        "new_foreshadows": plan.new_foreshadows,
        "develop_foreshadow_ids": plan.develop_foreshadow_ids,
        "payoff_foreshadow_ids": plan.payoff_foreshadow_ids,
        "risky_foreshadow_ids": plan.risky_foreshadow_ids,
        "prompt_text": service.format_plan_for_prompt(plan)
    }


# ========== Stats Endpoints ==========

@router.get("/projects/{project_id}/stats")
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    """获取项目伏笔统计"""
    service = ForeshadowService(db)
    stats = service.get_project_stats(project_id)
    return stats


@router.get("/projects/{project_id}/risky")
def get_risky_foreshadows(
    project_id: int,
    current_chapter: int,
    db: Session = Depends(get_db)
):
    """获取高风险伏笔"""
    service = ForeshadowService(db)
    service.calculate_risk_scores(project_id, current_chapter)

    risky = service.db.query(Foreshadow).filter(
        Foreshadow.project_id == project_id,
        Foreshadow.risk_score > 0.5
    ).order_by(desc(Foreshadow.risk_score)).all()

    return [{
        "id": f.id,
        "title": f.title,
        "status": f.status,
        "setup_chapter": f.setup_chapter,
        "risk_score": f.risk_score,
        "importance": f.importance_score
    } for f in risky]
