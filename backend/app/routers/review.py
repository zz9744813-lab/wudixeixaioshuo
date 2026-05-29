"""
Review Router - 成书复盘与技巧蒸馏 API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.book_review_service import BookReviewService

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewReportResponse(BaseModel):
    """复盘报告响应"""
    project_id: int
    project_name: str
    review_time: str
    summary: dict
    dimension_analysis: dict
    chapter_analysis: dict
    skill_usage: dict
    strengths: Optional[list] = None
    weaknesses: Optional[list] = None
    patterns: Optional[dict] = None


class DistillRequest(BaseModel):
    """技巧蒸馏请求"""
    min_chapter_score: int = 80
    create_cards: bool = True


class DistillResponse(BaseModel):
    """技巧蒸馏响应"""
    project_id: int
    project_name: str
    analyzed_chapters: int
    success_factors: list
    candidate_cards: list
    created_cards_count: int


class UpdateLibraryResponse(BaseModel):
    """更新技巧库响应"""
    updated_cards: list
    updated_count: int


@router.post("/books/{project_id}/review", response_model=ReviewReportResponse)
async def review_book(
    project_id: int,
    include_analysis: bool = True,
    db: Session = Depends(get_db)
):
    """
    对完成的书籍进行全面复盘

    - **project_id**: 项目ID
    - **include_analysis**: 是否包含详细分析
    """
    service = BookReviewService(db)
    result = service.review_completed_book(project_id, include_analysis)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/books/{project_id}/distill", response_model=DistillResponse)
async def distill_techniques(
    project_id: int,
    request: DistillRequest,
    db: Session = Depends(get_db)
):
    """
    从书籍中蒸馏技巧卡

    - **project_id**: 项目ID
    - **min_chapter_score**: 最低章节分数
    - **create_cards**: 是否自动创建技巧卡
    """
    service = BookReviewService(db)
    result = service.distill_techniques_from_book(
        project_id,
        min_chapter_score=request.min_chapter_score,
        create_cards=request.create_cards
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/books/{project_id}/update-library", response_model=UpdateLibraryResponse)
async def update_technique_library(
    project_id: int,
    min_usage_count: int = 3,
    db: Session = Depends(get_db)
):
    """
    基于项目经验更新技巧库

    - **project_id**: 项目ID
    - **min_usage_count**: 最低使用次数
    """
    service = BookReviewService(db)
    result = service.update_technique_library(project_id, min_usage_count)

    return result


@router.get("/books/{project_id}/strengths")
async def get_book_strengths(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取书籍的优势分析"""
    service = BookReviewService(db)
    result = service.review_completed_book(project_id, include_analysis=True)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "project_id": project_id,
        "strengths": result.get("strengths", []),
        "patterns": result.get("patterns", {}),
    }


@router.get("/books/{project_id}/stats")
async def get_book_stats(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取书籍统计信息"""
    service = BookReviewService(db)
    result = service.review_completed_book(project_id, include_analysis=False)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "project_id": result["project_id"],
        "project_name": result["project_name"],
        "summary": result["summary"],
        "dimension_analysis": result["dimension_analysis"],
        "skill_usage": result["skill_usage"],
    }
