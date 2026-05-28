"""
Review API 路由 - 独立评审系统
P4 Phase 4
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.review import ReviewProfile, ReviewResult, FinalReview
from app.services.review_service import ReviewService, REVIEW_DIMENSIONS

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ========== Request/Response Models ==========

class ReviewProfileCreate(BaseModel):
    name: str = "默认评审配置"
    is_default: bool = False
    reviewer_roles: Optional[List[str]] = None
    quality_threshold: float = 80.0
    rewrite_threshold: float = 75.0
    auto_reject_threshold: float = 60.0
    weights: Optional[dict] = None
    strictness: int = 5
    max_review_rounds: int = 2


class SingleReviewRequest(BaseModel):
    chapter_content: str
    chapter_title: str = ""
    reviewer_role: str = "reviewer_plot"
    dimension: str = "plot_progress"
    bible_context: str = ""
    memory_context: str = ""


class MultiReviewRequest(BaseModel):
    chapter_content: str
    chapter_title: str = ""
    profile_id: Optional[int] = None
    bible_context: str = ""
    memory_context: str = ""


class RewritePlanRequest(BaseModel):
    chapter_content: str
    final_review_id: int


# ========== Profile Endpoints ==========

@router.post("/projects/{project_id}/profile")
def create_review_profile(
    project_id: int,
    data: ReviewProfileCreate,
    db: Session = Depends(get_db)
):
    """创建评审配置"""
    service = ReviewService(db)
    profile = service.create_review_profile(
        project_id=project_id,
        name=data.name,
        is_default=data.is_default,
        reviewer_roles=data.reviewer_roles,
        quality_threshold=data.quality_threshold,
        rewrite_threshold=data.rewrite_threshold,
        auto_reject_threshold=data.auto_reject_threshold,
        weights=data.weights,
        strictness=data.strictness,
        max_review_rounds=data.max_review_rounds
    )
    return {
        "id": profile.id,
        "name": profile.name,
        "is_default": profile.is_default,
        "quality_threshold": profile.quality_threshold,
        "rewrite_threshold": profile.rewrite_threshold
    }


@router.get("/projects/{project_id}/profile")
def get_project_review_profile(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取项目评审配置"""
    service = ReviewService(db)
    profile = service.get_default_profile(project_id)
    if not profile:
        raise HTTPException(status_code=404, detail="评审配置不存在")
    return {
        "id": profile.id,
        "name": profile.name,
        "reviewer_roles": profile.reviewer_roles,
        "quality_threshold": profile.quality_threshold,
        "rewrite_threshold": profile.rewrite_threshold,
        "auto_reject_threshold": profile.auto_reject_threshold,
        "weights": profile.weights,
        "strictness": profile.strictness,
        "max_review_rounds": profile.max_review_rounds
    }


@router.get("/dimensions")
def get_review_dimensions():
    """获取评审维度定义"""
    return REVIEW_DIMENSIONS


# ========== Review Endpoints ==========

@router.post("/chapters/{chapter_id}/single")
async def single_review(
    chapter_id: int,
    task_id: int,
    version_id: Optional[int],
    data: SingleReviewRequest,
    db: Session = Depends(get_db)
):
    """单维度评审"""
    service = ReviewService(db)
    result = await service.review_dimension(
        task_id=task_id,
        chapter_id=chapter_id,
        version_id=version_id,
        chapter_content=data.chapter_content,
        chapter_title=data.chapter_title,
        reviewer_role=data.reviewer_role,
        dimension=data.dimension,
        bible_context=data.bible_context,
        memory_context=data.memory_context
    )
    return {
        "id": result.id,
        "reviewer_role": result.reviewer_role,
        "total_score": result.total_score,
        "score_breakdown": result.score_breakdown,
        "problems": result.problems,
        "suggestions": result.suggestions,
        "required_fixes": result.required_fixes,
        "pass_status": result.pass_status
    }


@router.post("/chapters/{chapter_id}/multi")
async def multi_dimension_review(
    chapter_id: int,
    task_id: int,
    version_id: Optional[int],
    data: MultiReviewRequest,
    db: Session = Depends(get_db)
):
    """多维度评审"""
    service = ReviewService(db)

    # 获取评审配置
    profile = None
    if data.profile_id:
        profile = service.get_review_profile(data.profile_id)

    results = await service.run_multi_dimension_review(
        task_id=task_id,
        chapter_id=chapter_id,
        version_id=version_id,
        chapter_content=data.chapter_content,
        chapter_title=data.chapter_title,
        profile=profile,
        bible_context=data.bible_context,
        memory_context=data.memory_context
    )

    return {
        "review_count": len(results),
        "reviews": [{
            "id": r.id,
            "reviewer_role": r.reviewer_role,
            "total_score": r.total_score,
            "pass_status": r.pass_status
        } for r in results]
    }


@router.post("/chapters/{chapter_id}/final")
async def final_review(
    chapter_id: int,
    task_id: int,
    version_id: Optional[int],
    profile_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """最终评审（FinalJudge）"""
    service = ReviewService(db)

    # 获取评审配置
    profile = None
    if profile_id:
        profile = service.get_review_profile(profile_id)
    else:
        profile = service.get_default_profile()

    # 获取已有的评审结果
    results = db.query(ReviewResult).filter(
        ReviewResult.chapter_id == chapter_id,
        ReviewResult.task_id == task_id
    ).all()

    if not results:
        raise HTTPException(status_code=400, detail="没有可用的评审结果，请先运行多维度评审")

    final = await service.run_final_judge(
        task_id=task_id,
        chapter_id=chapter_id,
        version_id=version_id,
        review_results=results,
        profile=profile
    )

    return {
        "id": final.id,
        "weighted_score": final.weighted_score,
        "min_score": final.min_score,
        "max_score": final.max_score,
        "dimension_scores": final.dimension_scores,
        "final_status": final.final_status,
        "critical_issues": final.critical_issues,
        "warnings": final.warnings,
        "rewrite_focus": final.rewrite_focus
    }


@router.get("/chapters/{chapter_id}/results")
def get_chapter_reviews(chapter_id: int, db: Session = Depends(get_db)):
    """获取章节所有评审结果"""
    results = db.query(ReviewResult).filter(
        ReviewResult.chapter_id == chapter_id
    ).order_by(ReviewResult.created_at.desc()).all()

    return [{
        "id": r.id,
        "reviewer_role": r.reviewer_role,
        "reviewer_model": r.reviewer_model,
        "total_score": r.total_score,
        "score_breakdown": r.score_breakdown,
        "problems": r.problems,
        "suggestions": r.suggestions,
        "required_fixes": r.required_fixes,
        "pass_status": r.pass_status,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in results]


@router.get("/chapters/{chapter_id}/final-result")
def get_final_review(chapter_id: int, db: Session = Depends(get_db)):
    """获取章节最终评审"""
    final = db.query(FinalReview).filter(
        FinalReview.chapter_id == chapter_id
    ).order_by(FinalReview.created_at.desc()).first()

    if not final:
        raise HTTPException(status_code=404, detail="最终评审不存在")

    return {
        "id": final.id,
        "weighted_score": final.weighted_score,
        "dimension_scores": final.dimension_scores,
        "final_status": final.final_status,
        "critical_issues": final.critical_issues,
        "warnings": final.warnings,
        "rewrite_focus": final.rewrite_focus
    }


# ========== Rewrite Endpoints ==========

@router.post("/chapters/{chapter_id}/rewrite-plan")
async def generate_rewrite_plan(
    chapter_id: int,
    data: RewritePlanRequest,
    db: Session = Depends(get_db)
):
    """生成改写计划"""
    service = ReviewService(db)

    final = db.query(FinalReview).filter(FinalReview.id == data.final_review_id).first()
    if not final:
        raise HTTPException(status_code=404, detail="最终评审不存在")

    results = db.query(ReviewResult).filter(
        ReviewResult.id.in_(final.review_result_ids)
    ).all()

    plan = await service.generate_rewrite_plan(
        chapter_content=data.chapter_content,
        final_review=final,
        review_results=results
    )

    return plan


# ========== Stats Endpoints ==========

@router.get("/projects/{project_id}/stats")
def get_project_review_stats(project_id: int, db: Session = Depends(get_db)):
    """获取项目评审统计"""
    service = ReviewService(db)
    stats = service.get_project_review_stats(project_id)
    return stats
