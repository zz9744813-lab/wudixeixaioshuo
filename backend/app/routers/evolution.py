"""
Evolution Router - 进化路由（修复版）
使用 EvolutionRun / EvolutionLog / VersionHistory
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chapter import ChapterVersion
from app.models.evolution import EvolutionDecision, EvolutionRun, EvolutionTarget, VersionHistory
from app.services.evolution_service import EvolutionService, EvolutionStrategy

router = APIRouter()


# ============== 请求模型 ==============

class EvolutionCreate(BaseModel):
    project_id: int
    target_dimension: str
    strategy: str = "auto"
    prompt_type: str = "writing"


class ABTestRequest(BaseModel):
    old_version_id: int
    new_version_id: int
    test_chapter_id: int


class EvolutionAction(BaseModel):
    action: str  # apply, rollback


# ============== 进化管理 API ==============

@router.get("/")
async def list_evolutions(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取进化记录列表"""
    query = db.query(EvolutionRun)

    if project_id:
        query = query.filter(EvolutionRun.project_id == project_id)
    if status:
        # 根据 decision 映射到 status
        if status == "completed":
            query = query.filter(EvolutionRun.decision == EvolutionDecision.KEEP)
        elif status == "rolled_back":
            query = query.filter(EvolutionRun.decision == EvolutionDecision.REVERT)
        elif status == "pending":
            query = query.filter(EvolutionRun.decision == EvolutionDecision.PENDING)

    evolutions = query.order_by(EvolutionRun.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": query.count(),
        "items": [
            {
                "id": e.id,
                "project_id": e.project_id,
                "target_type": e.target_type,
                "target_name": e.target_name,
                "decision": e.decision.value if e.decision else None,
                "before_score": e.before_score,
                "after_score": e.after_score,
                "improvement": e.improvement,
                "reason": e.reason,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "decided_at": e.decided_at.isoformat() if e.decided_at else None,
            }
            for e in evolutions
        ]
    }


@router.post("/")
async def create_evolution(
    request: EvolutionCreate,
    db: Session = Depends(get_db)
):
    """创建新的进化轮次"""
    service = EvolutionService(db)

    try:
        strategy = EvolutionStrategy(request.strategy)
    except ValueError:
        strategy = EvolutionStrategy.AUTO

    evolution = service.create_evolution_round(
        project_id=request.project_id,
        target_dimension=request.target_dimension,
        strategy=strategy,
        prompt_type=request.prompt_type
    )

    return {
        "id": evolution.id,
        "message": "进化轮次已创建",
        "target_name": evolution.target_name,
        "decision": evolution.decision.value,
    }


@router.get("/{evolution_id}")
async def get_evolution(
    evolution_id: int,
    db: Session = Depends(get_db)
):
    """获取进化详情"""
    evolution = db.query(EvolutionRun).filter(EvolutionRun.id == evolution_id).first()

    if not evolution:
        raise HTTPException(status_code=404, detail="进化记录不存在")

    # 获取相关版本历史
    versions = db.query(VersionHistory).filter(
        VersionHistory.project_id == evolution.project_id
    ).order_by(VersionHistory.created_at.desc()).limit(10).all()

    return {
        "id": evolution.id,
        "project_id": evolution.project_id,
        "target_type": evolution.target_type,
        "target_name": evolution.target_name,
        "decision": evolution.decision.value if evolution.decision else None,
        "before_version": evolution.before_version,
        "after_version": evolution.after_version,
        "before_score": evolution.before_score,
        "after_score": evolution.after_score,
        "improvement": evolution.improvement,
        "reason": evolution.reason,
        "test_sample_count": evolution.test_sample_count,
        "judge_agents": evolution.judge_agents,
        "created_at": evolution.created_at.isoformat() if evolution.created_at else None,
        "decided_at": evolution.decided_at.isoformat() if evolution.decided_at else None,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "asset_type": v.asset_type,
                "asset_name": v.asset_name,
                "is_current": v.is_current == 1,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]
    }


@router.post("/{evolution_id}/test")
async def run_ab_test(
    evolution_id: int,
    request: ABTestRequest,
    db: Session = Depends(get_db)
):
    """运行 A/B 测试"""
    service = EvolutionService(db)

    result = service.run_ab_test(
        evolution_id=evolution_id,
        old_version_id=request.old_version_id,
        new_version_id=request.new_version_id,
        test_chapter_id=request.test_chapter_id
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/{evolution_id}/action")
async def evolution_action(
    evolution_id: int,
    request: EvolutionAction,
    db: Session = Depends(get_db)
):
    """执行进化操作（应用或回滚）"""
    service = EvolutionService(db)

    if request.action == "apply":
        # 获取该进化记录关联的版本
        evolution = db.query(EvolutionRun).filter(
            EvolutionRun.id == evolution_id
        ).first()

        if not evolution:
            raise HTTPException(status_code=404, detail="进化记录不存在")

        # 查找对应的 VersionHistory
        version = db.query(VersionHistory).filter(
            VersionHistory.project_id == evolution.project_id,
            VersionHistory.asset_type == evolution.target_type,
            VersionHistory.asset_name == evolution.target_name
        ).order_by(VersionHistory.created_at.desc()).first()

        if not version:
            raise HTTPException(status_code=404, detail="没有找到可应用的版本")

        success = service.apply_evolution(evolution_id, version.id)

        if success:
            return {"message": "进化已应用"}
        else:
            raise HTTPException(status_code=400, detail="应用失败")

    elif request.action == "rollback":
        success = service.rollback_evolution(evolution_id)

        if success:
            return {"message": "进化已回滚"}
        else:
            raise HTTPException(status_code=404, detail="进化记录不存在")

    else:
        raise HTTPException(status_code=400, detail=f"未知操作: {request.action}")


# ============== 统计和最佳实践 API ==============

@router.get("/stats/overview")
async def get_evolution_stats(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取进化统计"""
    service = EvolutionService(db)
    stats = service.get_evolution_stats(project_id)

    return stats


@router.get("/best-practices")
async def get_best_practices(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取最佳实践"""
    service = EvolutionService(db)
    practices = service.get_best_practices(project_id)

    return {
        "count": len(practices),
        "practices": practices
    }


@router.get("/dimensions")
async def get_evolution_dimensions():
    """获取支持的进化维度"""
    return {
        "dimensions": [
            {"id": "plot", "name": "剧情连贯性", "description": "改进剧情逻辑和伏笔回收"},
            {"id": "character", "name": "人物一致性", "description": "保持人物行为符合其设定"},
            {"id": "pacing", "name": "节奏把控", "description": "优化叙事节奏，避免拖沓"},
            {"id": "style", "name": "文笔质量", "description": "提升描写细节和句式多样性"},
            {"id": "engagement", "name": "吸引力", "description": "增强悬念和读者兴趣"},
        ],
        "strategies": [
            {"id": "auto", "name": "自动", "description": "根据问题自动选择策略"},
            {"id": "conservative", "name": "保守", "description": "小幅改进，低风险"},
            {"id": "aggressive", "name": "激进", "description": "大幅改进，可能引入新问题"},
            {"id": "targeted", "name": "针对性", "description": "针对特定问题精准改进"},
        ]
    }
