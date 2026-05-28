"""
Skill API 路由 - 技巧库分类与调用
P4 Phase 2
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.technique import TechniqueCard, BookProfile
from app.services.skill_service import SkillSelectionService, BookProfileService, SKILL_TAXONOMY

router = APIRouter(prefix="/skills", tags=["skills"])


# ========== Request/Response Models ==========

class ClassifySkillRequest(BaseModel):
    taxonomy_level_1: str
    taxonomy_level_2: Optional[str] = None
    scene_stage: Optional[str] = None


class AutoClassifyRequest(BaseModel):
    technique_ids: Optional[List[int]] = None


class SelectSkillsRequest(BaseModel):
    chapter_index: int
    genre: Optional[str] = None
    scene_stage: Optional[str] = None
    needed_emotion: Optional[str] = None
    conflict_type: Optional[str] = None
    max_skills: int = 5


class SkillFeedbackRequest(BaseModel):
    technique_id: int
    chapter_id: int
    was_successful: bool
    score: Optional[float] = None
    note: Optional[str] = None


class BookProfileCreate(BaseModel):
    genre: Optional[str] = None
    sub_genre: Optional[str] = None
    audience: Optional[str] = None
    style_tags: Optional[List[str]] = None
    narrative_pov: Optional[str] = None
    pacing_type: Optional[str] = None
    commercial_density: int = 5
    adult_level: int = 0
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None


# ========== Taxonomy Endpoints ==========

@router.get("/taxonomy")
def get_skill_taxonomy():
    """获取技巧分类体系"""
    return {
        "taxonomy": SKILL_TAXONOMY,
        "scene_stages": [
            "opening", "daily_scene", "conflict", "climax",
            "transition", "ending", "volume_opening", "volume_finale"
        ]
    }


@router.get("/taxonomy/stats")
def get_taxonomy_stats(db: Session = Depends(get_db)):
    """获取技巧分类统计"""
    service = SkillSelectionService(db)
    return service.get_taxonomy_stats()


# ========== Skill Classification Endpoints ==========

@router.post("/{technique_id}/classify")
def classify_skill(
    technique_id: int,
    data: ClassifySkillRequest,
    db: Session = Depends(get_db)
):
    """为技巧卡打分类标签"""
    service = SkillSelectionService(db)
    card = service.classify_skill(
        technique_id=technique_id,
        taxonomy_level_1=data.taxonomy_level_1,
        taxonomy_level_2=data.taxonomy_level_2,
        scene_stage=data.scene_stage
    )
    if not card:
        raise HTTPException(status_code=404, detail="技巧卡不存在")
    return {
        "id": card.id,
        "title": card.title,
        "taxonomy_level_1": card.taxonomy_level_1,
        "taxonomy_level_2": card.taxonomy_level_2,
        "scene_stage": card.scene_stage
    }


@router.post("/auto-classify")
def auto_classify_skills(
    data: AutoClassifyRequest,
    db: Session = Depends(get_db)
):
    """自动分类未分类的技巧卡"""
    service = SkillSelectionService(db)
    result = service.auto_classify_skills(data.technique_ids)
    return result


# ========== Skill Selection Endpoints ==========

@router.post("/projects/{project_id}/select-for-chapter")
def select_skills_for_chapter(
    project_id: int,
    data: SelectSkillsRequest,
    db: Session = Depends(get_db)
):
    """为章节选择相关技巧卡"""
    service = SkillSelectionService(db)
    skills = service.select_skills_for_chapter(
        project_id=project_id,
        chapter_index=data.chapter_index,
        genre=data.genre,
        scene_stage=data.scene_stage,
        needed_emotion=data.needed_emotion,
        conflict_type=data.conflict_type,
        max_skills=data.max_skills
    )

    # 同时返回格式化后的prompt文本
    prompt_text = service.format_skills_for_prompt(skills)

    return {
        "skills": skills,
        "prompt_text": prompt_text,
        "count": len(skills)
    }


@router.get("/by-taxonomy")
def get_skills_by_taxonomy(
    taxonomy_level_1: Optional[str] = None,
    taxonomy_level_2: Optional[str] = None,
    min_effectiveness: float = 0.0,
    db: Session = Depends(get_db)
):
    """按分类获取技巧卡"""
    service = SkillSelectionService(db)
    cards = service.get_skills_by_taxonomy(
        taxonomy_level_1=taxonomy_level_1,
        taxonomy_level_2=taxonomy_level_2,
        min_effectiveness=min_effectiveness
    )
    return [{
        "id": c.id,
        "title": c.title,
        "taxonomy_level_1": c.taxonomy_level_1,
        "taxonomy_level_2": c.taxonomy_level_2,
        "effectiveness_score": c.effectiveness_score,
        "risk_level": c.risk_level,
        "usage_count": c.usage_count
    } for c in cards]


# ========== Skill Feedback Endpoints ==========

@router.post("/feedback")
def update_skill_feedback(
    data: SkillFeedbackRequest,
    db: Session = Depends(get_db)
):
    """更新技巧卡效果反馈"""
    service = SkillSelectionService(db)
    card = service.update_skill_feedback(
        technique_id=data.technique_id,
        chapter_id=data.chapter_id,
        was_successful=data.was_successful,
        score=data.score,
        note=data.note
    )
    if not card:
        raise HTTPException(status_code=404, detail="技巧卡不存在")
    return {
        "id": card.id,
        "effectiveness_score": card.effectiveness_score,
        "positive_count": card.positive_review_count,
        "negative_count": card.negative_review_count,
        "usage_count": card.usage_count
    }


# ========== Book Profile Endpoints ==========

@router.post("/books/{book_id}/profile")
def create_book_profile(
    book_id: int,
    data: BookProfileCreate,
    db: Session = Depends(get_db)
):
    """创建或更新书籍档案"""
    service = BookProfileService(db)
    profile = service.create_or_update_profile(
        book_id=book_id,
        genre=data.genre,
        sub_genre=data.sub_genre,
        audience=data.audience,
        style_tags=data.style_tags,
        narrative_pov=data.narrative_pov,
        pacing_type=data.pacing_type,
        commercial_density=data.commercial_density,
        adult_level=data.adult_level,
        strengths=data.strengths,
        weaknesses=data.weaknesses
    )
    return {
        "id": profile.id,
        "book_id": profile.book_id,
        "genre": profile.genre,
        "sub_genre": profile.sub_genre,
        "style_tags": profile.style_tags
    }


@router.get("/books/{book_id}/profile")
def get_book_profile(book_id: int, db: Session = Depends(get_db)):
    """获取书籍档案"""
    service = BookProfileService(db)
    profile = service.get_profile(book_id)
    if not profile:
        raise HTTPException(status_code=404, detail="书籍档案不存在")
    return {
        "id": profile.id,
        "book_id": profile.book_id,
        "genre": profile.genre,
        "sub_genre": profile.sub_genre,
        "audience": profile.audience,
        "style_tags": profile.style_tags,
        "narrative_pov": profile.narrative_pov,
        "pacing_type": profile.pacing_type,
        "commercial_density": profile.commercial_density,
        "adult_level": profile.adult_level,
        "strengths": profile.strengths,
        "weaknesses": profile.weaknesses,
        "reusable_skill_categories": profile.reusable_skill_categories
    }


@router.post("/books/{book_id}/analyze-skills")
def analyze_book_skills(book_id: int, db: Session = Depends(get_db)):
    """分析书籍可复用技巧"""
    service = BookProfileService(db)
    categories = service.analyze_reusable_skills(book_id)

    # 更新到profile
    profile = service.get_profile(book_id)
    if profile:
        profile.reusable_skill_categories = categories
        db.commit()

    return {
        "book_id": book_id,
        "reusable_categories": categories,
        "suggestions": service.suggest_skills_for_book(book_id, profile.genre if profile else None) if hasattr(service, 'suggest_skills_for_book') else []
    }


@router.get("/suggest-for-book/{book_id}")
def suggest_skills_for_book(book_id: int, db: Session = Depends(get_db)):
    """为书籍推荐可学习技巧"""
    profile_service = BookProfileService(db)
    profile = profile_service.get_profile(book_id)

    skill_service = SkillSelectionService(db)
    suggestions = skill_service.suggest_skills_for_book(
        book_id=book_id,
        book_type=profile.genre if profile else None
    )
    return {
        "book_id": book_id,
        "book_type": profile.genre if profile else None,
        "suggestions": suggestions
    }
