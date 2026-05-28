"""
Techniques Router - 技巧库路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.technique import TechniqueCard

router = APIRouter()


# Pydantic 模型
class TechniqueResponse(BaseModel):
    id: int
    category: str
    title: str
    description: Optional[str]
    confidence_score: float
    usage_count: int
    is_active: bool
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TechniqueResponse])
async def list_techniques(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    book_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取技巧卡列表"""
    query = db.query(TechniqueCard)
    if category:
        query = query.filter(TechniqueCard.category == category)
    if book_id:
        query = query.filter(TechniqueCard.book_id == book_id)

    techniques = query.order_by(TechniqueCard.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": t.id,
            "category": t.category,
            "title": t.title,
            "description": t.description[:200] + "..." if t.description and len(t.description) > 200 else t.description,
            "confidence_score": t.confidence_score,
            "usage_count": t.usage_count,
            "is_active": t.is_active == 1,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in techniques
    ]


@router.get("/{technique_id}")
async def get_technique(technique_id: int, db: Session = Depends(get_db)):
    """获取技巧卡详情"""
    technique = db.query(TechniqueCard).filter(TechniqueCard.id == technique_id).first()
    if not technique:
        raise HTTPException(status_code=404, detail="技巧卡不存在")

    return {
        "id": technique.id,
        "category": technique.category,
        "title": technique.title,
        "observation": technique.observation,
        "description": technique.description,
        "principle": technique.principle,
        "transfer_rule": technique.transfer_rule,
        "usage_instruction": technique.usage_instruction,
        "anti_pattern": technique.anti_pattern,
        "prevention_rule": technique.prevention_rule,
        "prompt_instruction": technique.prompt_instruction,
        "confidence_score": technique.confidence_score,
        "success_rate": technique.success_rate,
        "usage_count": technique.usage_count,
        "applicable_genres": technique.applicable_genres,
        "tags": technique.tags,
        "is_active": technique.is_active == 1,
        "is_verified": technique.is_verified == 1,
        "created_at": technique.created_at.isoformat() if technique.created_at else None,
    }


@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """获取技巧分类列表"""
    categories = db.query(TechniqueCard.category).distinct().all()
    return [c[0] for c in categories if c[0]]
