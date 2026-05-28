"""
Evolution Router - 进化路由（完整版）
Darwin 进化引擎 API
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evolution import Evolution, EvolutionStatus, PromptVersion, TestResult
from app.services.evolution_service import EvolutionService, EvolutionStrategy

router = APIRouter()


# ============== 请求模型 ==============

class EvolutionCreate(BaseModel):
    project_id: int
    target_dimension: str  # plot, character, pacing, style, engagement
    strategy: str = "auto"  # auto, conservative, aggressive, targeted
    prompt_type: str = "writing"


class ImprovementGenerate(BaseModel):
    current_prompt: str
    feedback_ids: Optional[List[int]] = None  # 指定反馈，None 则自动收集


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
    query = db.query(Evolution)

    if project_id:
        query = query.filter(Evolution.project_id == project_id)
    if status:
        query = query.filter(Evolution.status == status)

    evolutions = query.order_by(Evolution.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": query.count(),
        "items": [
            {
                "id": e.id,
                "project_id": e.project_id,
                "target_dimension": e.target_dimension,
                "strategy": e.strategy,
                "prompt_type": e.prompt_type,
                "status": e.status.value if e.status else None,
                "hypothesis": e.hypothesis,
                "applied_at": e.applied_at.isoformat() if e.applied_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "metadata": e.metadata,
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
        "target_dimension": evolution.target_dimension,
        "status": evolution.status.value,
    }


@router.get("/{evolution_id}")
async def get_evolution(
    evolution_id: int,
    db: Session = Depends(get_db)
):
    """获取进化详情"""
    evolution = db.query(Evolution).filter(Evolution.id == evolution_id).first()

    if not evolution:
        raise HTTPException(status_code=404, detail="进化记录不存在")

    # 获取相关版本
    versions = db.query(PromptVersion).filter(
        PromptVersion.evolution_id == evolution_id
    ).all()

    # 获取测试结果
    test_results = db.query(TestResult).filter(
        TestResult.evolution_id == evolution_id
    ).all()

    return {
        "id": evolution.id,
        "project_id": evolution.project_id,
        "target_dimension": evolution.target_dimension,
        "strategy": evolution.strategy,
        "prompt_type": evolution.prompt_type,
        "status": evolution.status.value if evolution.status else None,
        "hypothesis": evolution.hypothesis,
        "metadata": evolution.metadata,
        "applied_at": evolution.applied_at.isoformat() if evolution.applied_at else None,
        "created_at": evolution.created_at.isoformat() if evolution.created_at else None,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "prompt_type": v.prompt_type,
                "content": v.content[:200] + "..." if len(v.content) > 200 else v.content,
                "changes_summary": v.changes_summary,
                "test_passed": v.test_passed,
                "is_active": v.is_active,
            }
            for v in versions
        ],
        "test_results": [
            {
                "id": t.id,
                "old_version_id": t.old_version_id,
                "new_version_id": t.new_version_id,
                "improvement_rate": t.improvement_rate,
                "passed": t.passed,
                "old_scores": t.old_scores,
                "new_scores": t.new_scores,
            }
            for t in test_results
        ]
    }


@router.post("/{evolution_id}/collect-feedback")
async def collect_feedback(
    evolution_id: int,
    min_count: int = 5,
    db: Session = Depends(get_db)
):
    """收集反馈用于进化分析"""
    service = EvolutionService(db)

    feedbacks = service.collect_feedback_for_evolution(
        evolution_id=evolution_id,
        min_feedback_count=min_count
    )

    return {
        "evolution_id": evolution_id,
        "feedback_collected": len(feedbacks),
        "feedback_ids": [f.id for f in feedbacks],
    }


@router.post("/{evolution_id}/generate")
async def generate_improvement(
    evolution_id: int,
    request: ImprovementGenerate,
    db: Session = Depends(get_db)
):
    """生成改进的提示词"""
    service = EvolutionService(db)

    # 如果指定了反馈ID，先更新元数据
    if request.feedback_ids:
        evolution = db.query(Evolution).filter(Evolution.id == evolution_id).first()
        if evolution:
            evolution.metadata = evolution.metadata or {}
            evolution.metadata["feedback_collected"] = request.feedback_ids
            db.commit()

    version = service.generate_improvement(
        evolution_id=evolution_id,
        current_prompt=request.current_prompt,
        feedbacks=[]  # 服务内部会根据 feedback_ids 或自动收集
    )

    if not version:
        raise HTTPException(status_code=400, detail="生成改进失败")

    return {
        "version_id": version.id,
        "version_number": version.version_number,
        "changes_summary": version.changes_summary,
        "message": "新版本已生成，准备测试",
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

    return {
        "test_id": result.id,
        "passed": result.passed,
        "improvement_rate": result.improvement_rate,
        "old_scores": result.old_scores,
        "new_scores": result.new_scores,
        "message": "测试通过" if result.passed else "测试未通过，建议回滚",
    }


@router.post("/{evolution_id}/action")
async def evolution_action(
    evolution_id: int,
    request: EvolutionAction,
    db: Session = Depends(get_db)
):
    """执行进化操作（应用或回滚）"""
    service = EvolutionService(db)

    if request.action == "apply":
        # 获取最新版本
        version = db.query(PromptVersion).filter(
            PromptVersion.evolution_id == evolution_id
        ).order_by(PromptVersion.version_number.desc()).first()

        if not version:
            raise HTTPException(status_code=404, detail="没有找到可应用的版本")

        success = service.apply_evolution(evolution_id, version.id)

        if success:
            return {
                "message": "进化已应用",
                "applied_version_id": version.id,
            }
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
            {
                "id": "plot",
                "name": "剧情连贯性",
                "description": "改进剧情逻辑和伏笔回收",
            },
            {
                "id": "character",
                "name": "人物一致性",
                "description": "保持人物行为符合其设定",
            },
            {
                "id": "pacing",
                "name": "节奏把控",
                "description": "优化叙事节奏，避免拖沓",
            },
            {
                "id": "style",
                "name": "文笔质量",
                "description": "提升描写细节和句式多样性",
            },
            {
                "id": "engagement",
                "name": "吸引力",
                "description": "增强悬念和读者兴趣",
            },
        ],
        "strategies": [
            {"id": "auto", "name": "自动", "description": "根据问题自动选择策略"},
            {"id": "conservative", "name": "保守", "description": "小幅改进，低风险"},
            {"id": "aggressive", "name": "激进", "description": "大幅改进，可能引入新问题"},
            {"id": "targeted", "name": "针对性", "description": "针对特定问题精准改进"},
        ]
    }
