"""
Production API 路由 - 自动排产
P4 Phase 5
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.production import ProductionPolicy
from app.services.production_scheduler import ProductionScheduler

router = APIRouter(tags=["production"])


# ========== Request/Response Models ==========

class ProductionPolicyCreate(BaseModel):
    enabled: bool = False
    target_daily_words: int = 10000
    target_daily_chapters: int = 3
    max_daily_cost: float = 5.0
    max_daily_tokens: int = 500000
    min_quality_score: float = 80.0
    max_rewrite_rounds: int = 2
    max_consecutive_failures: int = 3
    auto_create_next_chapter: bool = True
    auto_pause_on_failure: bool = True
    auto_pause_on_budget: bool = True
    active_hours: Optional[List[List[int]]] = None
    priority: int = 2


class ToggleProductionRequest(BaseModel):
    enabled: bool


# ========== Policy Endpoints ==========

@router.post("/projects/{project_id}/policy")
def create_production_policy(
    project_id: int,
    data: ProductionPolicyCreate,
    db: Session = Depends(get_db)
):
    """创建/更新生产策略"""
    scheduler = ProductionScheduler(db)
    policy = scheduler.create_policy(
        project_id=project_id,
        enabled=data.enabled,
        target_daily_words=data.target_daily_words,
        target_daily_chapters=data.target_daily_chapters,
        max_daily_cost=data.max_daily_cost,
        max_daily_tokens=data.max_daily_tokens,
        min_quality_score=data.min_quality_score,
        max_rewrite_rounds=data.max_rewrite_rounds,
        max_consecutive_failures=data.max_consecutive_failures,
        auto_create_next_chapter=data.auto_create_next_chapter,
        auto_pause_on_failure=data.auto_pause_on_failure,
        auto_pause_on_budget=data.auto_pause_on_budget,
        active_hours=data.active_hours,
        priority=data.priority
    )
    return {
        "id": policy.id,
        "project_id": policy.project_id,
        "enabled": policy.enabled == 1,
        "target_daily_words": policy.target_daily_words,
        "target_daily_chapters": policy.target_daily_chapters,
        "max_daily_cost": policy.max_daily_cost,
        "min_quality_score": policy.min_quality_score
    }


@router.get("/projects/{project_id}/policy")
def get_production_policy(project_id: int, db: Session = Depends(get_db)):
    """获取生产策略"""
    scheduler = ProductionScheduler(db)
    policy = scheduler.get_policy(project_id)
    if not policy:
        raise HTTPException(status_code=404, detail="生产策略不存在")
    return {
        "id": policy.id,
        "project_id": policy.project_id,
        "enabled": policy.enabled == 1,
        "target_daily_words": policy.target_daily_words,
        "target_daily_chapters": policy.target_daily_chapters,
        "max_daily_cost": policy.max_daily_cost,
        "max_daily_tokens": policy.max_daily_tokens,
        "min_quality_score": policy.min_quality_score,
        "max_rewrite_rounds": policy.max_rewrite_rounds,
        "max_consecutive_failures": policy.max_consecutive_failures,
        "auto_create_next_chapter": policy.auto_create_next_chapter == 1,
        "auto_pause_on_failure": policy.auto_pause_on_failure == 1,
        "auto_pause_on_budget": policy.auto_pause_on_budget == 1,
        "active_hours": policy.active_hours,
        "priority": policy.priority
    }


@router.post("/projects/{project_id}/toggle")
def toggle_production(
    project_id: int,
    data: ToggleProductionRequest,
    db: Session = Depends(get_db)
):
    """开关自动生产"""
    scheduler = ProductionScheduler(db)
    policy = scheduler.toggle_production(project_id, data.enabled)
    if not policy:
        raise HTTPException(status_code=404, detail="生产策略不存在")
    return {
        "enabled": policy.enabled == 1,
        "message": "自动生产已开启" if policy.enabled == 1 else "自动生产已暂停"
    }


# ========== Control Endpoints ==========

@router.post("/projects/{project_id}/start")
def start_production(project_id: int, db: Session = Depends(get_db)):
    """开始自动生产"""
    scheduler = ProductionScheduler(db)
    policy = scheduler.toggle_production(project_id, True)
    if not policy:
        raise HTTPException(status_code=404, detail="生产策略不存在")
    return {"status": "started", "message": "自动生产已启动"}


@router.post("/projects/{project_id}/pause")
def pause_production(project_id: int, db: Session = Depends(get_db)):
    """暂停自动生产"""
    scheduler = ProductionScheduler(db)
    policy = scheduler.toggle_production(project_id, False)
    if not policy:
        raise HTTPException(status_code=404, detail="生产策略不存在")
    return {"status": "paused", "message": "自动生产已暂停"}


@router.post("/projects/{project_id}/resume")
def resume_production(project_id: int, db: Session = Depends(get_db)):
    """恢复自动生产"""
    return start_production(project_id, db)


# ========== Scheduler Endpoints ==========

@router.post("/scheduler/scan")
def scan_and_schedule(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """手动触发调度扫描"""
    scheduler = ProductionScheduler(db)
    results = scheduler.scan_and_schedule()
    return {
        "scheduled": len(results),
        "results": results
    }


# ========== Stats Endpoints ==========

@router.get("/projects/{project_id}/stats")
def get_production_stats(
    project_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """获取生产统计"""
    scheduler = ProductionScheduler(db)
    stats = scheduler.get_project_stats(project_id, days)
    return stats


@router.get("/queue")
def get_queue_status(db: Session = Depends(get_db)):
    """获取生产队列状态"""
    scheduler = ProductionScheduler(db)
    return scheduler.get_queue_status()


@router.get("/projects/{project_id}/logs")
def get_production_logs(
    project_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取生产日志"""
    scheduler = ProductionScheduler(db)
    logs = scheduler.get_recent_logs(project_id, limit)
    return {"logs": logs}


# ========== Production Loop 控制 (P8) ==========

@router.post("/loop/start")
async def start_production_loop():
    """启动常驻生产循环"""
    from app.services.production_loop_service import production_loop
    await production_loop.start()
    return production_loop.get_status()


@router.post("/loop/stop")
async def stop_production_loop():
    """停止常驻生产循环"""
    from app.services.production_loop_service import production_loop
    await production_loop.stop()
    return production_loop.get_status()


@router.post("/loop/pause")
async def pause_production_loop():
    """暂停常驻生产循环"""
    from app.services.production_loop_service import production_loop
    await production_loop.pause()
    return production_loop.get_status()


@router.post("/loop/resume")
async def resume_production_loop():
    """恢复常驻生产循环"""
    from app.services.production_loop_service import production_loop
    await production_loop.resume()
    return production_loop.get_status()


@router.get("/loop/status")
async def get_production_loop_status():
    """查看常驻生产循环状态"""
    from app.services.production_loop_service import production_loop
    return production_loop.get_status()
