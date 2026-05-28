"""
Memory API 路由 - 记忆系统接口
Phase 1: 支持角色、世界观、章节、关系记忆的CRUD
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.memory import (
    CharacterMemory, WorldMemory, ChapterMemory, RelationshipMemory
)
from app.services.memory_service import MemoryService

router = APIRouter(tags=["memory"])


# ========== Request/Response Models ==========

class CharacterMemoryCreate(BaseModel):
    name: str
    role_type: str = "supporting"
    stable_profile: dict = {}
    dynamic_state: dict = {}
    personality: dict = {}
    goals: list = []
    secrets: list = []
    first_chapter: Optional[int] = None
    importance: float = 0.5


class CharacterMemoryUpdate(BaseModel):
    dynamic_state: Optional[dict] = None
    summary: Optional[str] = None
    latest_update_reason: Optional[str] = None


class WorldMemoryCreate(BaseModel):
    category: str
    name: str
    description: str = ""
    rules: list = []
    constraints: list = []
    related_characters: list = []
    importance: float = 0.5


class ChapterMemoryCreate(BaseModel):
    chapter_id: int
    chapter_index: int
    short_summary: str = ""
    detailed_summary: str = ""
    key_events: list = []
    character_changes: list = []
    world_updates: list = []
    relationship_changes: list = []
    unresolved_questions: list = []
    foreshadow_updates: list = []


class RelationshipMemoryCreate(BaseModel):
    character_a: str
    character_b: str
    relationship_type: str
    current_status: str = ""
    tension_level: int = 0
    trust_level: int = 0


class ContextAssemblyRequest(BaseModel):
    chapter_index: int
    mentioned_chars: Optional[List[str]] = None


# ========== Character Memory Endpoints ==========

@router.post("/projects/{project_id}/characters", response_model=dict)
def create_character_memory(
    project_id: int,
    data: CharacterMemoryCreate,
    db: Session = Depends(get_db)
):
    """创建角色记忆"""
    service = MemoryService(db)
    memory = service.create_character_memory(
        project_id=project_id,
        name=data.name,
        role_type=data.role_type,
        stable_profile=data.stable_profile,
        dynamic_state=data.dynamic_state,
        personality=data.personality,
        goals=data.goals,
        secrets=data.secrets,
        first_chapter=data.first_chapter,
        importance=data.importance
    )
    return {"id": memory.id, "name": memory.name, "created": True}


@router.get("/projects/{project_id}/characters")
def list_character_memories(
    project_id: int,
    role_type: Optional[str] = None,
    min_importance: float = 0.0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出角色记忆"""
    service = MemoryService(db)
    characters = service.list_characters(
        project_id=project_id,
        role_type=role_type,
        min_importance=min_importance,
        limit=limit
    )
    return [{
        "id": c.id,
        "name": c.name,
        "role_type": c.role_type,
        "importance_score": c.importance_score,
        "dynamic_state": c.dynamic_state,
        "first_appearance": c.first_appearance_chapter,
        "last_seen": c.last_seen_chapter,
        "summary": c.summary
    } for c in characters]


@router.get("/characters/{memory_id}")
def get_character_memory(memory_id: int, db: Session = Depends(get_db)):
    """获取单个角色记忆"""
    service = MemoryService(db)
    memory = service.get_character_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="角色记忆不存在")
    return {
        "id": memory.id,
        "name": memory.name,
        "aliases": memory.aliases,
        "role_type": memory.role_type,
        "stable_profile": memory.stable_profile,
        "dynamic_state": memory.dynamic_state,
        "personality": memory.personality,
        "goals": memory.goals,
        "secrets": memory.secrets,
        "importance_score": memory.importance_score,
        "summary": memory.summary,
        "first_appearance": memory.first_appearance_chapter,
        "last_seen": memory.last_seen_chapter
    }


@router.put("/characters/{memory_id}")
def update_character_memory(
    memory_id: int,
    data: CharacterMemoryUpdate,
    db: Session = Depends(get_db)
):
    """更新角色记忆"""
    service = MemoryService(db)
    memory = service.get_character_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="角色记忆不存在")

    if data.dynamic_state:
        service.update_character_state(
            memory_id=memory_id,
            state_updates=data.dynamic_state,
            reason=data.latest_update_reason or "手动更新"
        )

    if data.summary:
        memory.summary = data.summary
        db.commit()

    return {"updated": True}


# ========== World Memory Endpoints ==========

@router.post("/projects/{project_id}/world", response_model=dict)
def create_world_memory(
    project_id: int,
    data: WorldMemoryCreate,
    db: Session = Depends(get_db)
):
    """创建世界观记忆"""
    service = MemoryService(db)
    memory = service.create_world_memory(
        project_id=project_id,
        category=data.category,
        name=data.name,
        description=data.description,
        rules=data.rules,
        constraints=data.constraints,
        related_chars=data.related_characters,
        importance=data.importance
    )
    return {"id": memory.id, "name": memory.name, "created": True}


@router.get("/projects/{project_id}/world")
def list_world_memories(
    project_id: int,
    category: Optional[str] = None,
    min_importance: float = 0.0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出世界观记忆"""
    service = MemoryService(db)
    memories = service.list_world_memories(
        project_id=project_id,
        category=category,
        min_importance=min_importance,
        limit=limit
    )
    return [{
        "id": m.id,
        "category": m.category,
        "name": m.name,
        "description": m.description[:200] if m.description else "",
        "importance_score": m.importance_score,
        "is_canon": m.is_canon
    } for m in memories]


# ========== Chapter Memory Endpoints ==========

@router.post("/projects/{project_id}/chapters", response_model=dict)
def create_chapter_memory(
    project_id: int,
    data: ChapterMemoryCreate,
    db: Session = Depends(get_db)
):
    """创建章节记忆"""
    service = MemoryService(db)
    memory = service.create_chapter_memory(
        project_id=project_id,
        chapter_id=data.chapter_id,
        chapter_index=data.chapter_index,
        short_summary=data.short_summary,
        detailed_summary=data.detailed_summary,
        key_events=data.key_events,
        character_changes=data.character_changes,
        world_updates=data.world_updates,
        relationship_changes=data.relationship_changes,
        unresolved_questions=data.unresolved_questions,
        foreshadow_updates=data.foreshadow_updates
    )
    return {"id": memory.id, "chapter_index": memory.chapter_index, "created": True}


@router.get("/projects/{project_id}/chapters")
def list_chapter_memories(
    project_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """列出章节记忆"""
    memories = db.query(ChapterMemory).filter(
        ChapterMemory.project_id == project_id
    ).order_by(ChapterMemory.chapter_index.desc()).limit(limit).all()

    return [{
        "id": m.id,
        "chapter_id": m.chapter_id,
        "chapter_index": m.chapter_index,
        "short_summary": m.short_summary,
        "key_events": m.key_events[:5] if m.key_events else []
    } for m in memories]


@router.get("/chapters/{chapter_id}/memory")
def get_chapter_memory(chapter_id: int, db: Session = Depends(get_db)):
    """获取章节记忆"""
    service = MemoryService(db)
    memory = service.get_chapter_memory(chapter_id)
    if not memory:
        raise HTTPException(status_code=404, detail="章节记忆不存在")
    return {
        "id": memory.id,
        "chapter_index": memory.chapter_index,
        "short_summary": memory.short_summary,
        "detailed_summary": memory.detailed_summary,
        "key_events": memory.key_events,
        "character_changes": memory.character_changes,
        "world_updates": memory.world_updates,
        "relationship_changes": memory.relationship_changes,
        "unresolved_questions": memory.unresolved_questions,
        "foreshadow_updates": memory.foreshadow_updates
    }


# ========== Relationship Memory Endpoints ==========

@router.post("/projects/{project_id}/relationships", response_model=dict)
def create_relationship_memory(
    project_id: int,
    data: RelationshipMemoryCreate,
    db: Session = Depends(get_db)
):
    """创建关系记忆"""
    service = MemoryService(db)
    memory = service.create_relationship_memory(
        project_id=project_id,
        char_a=data.character_a,
        char_b=data.character_b,
        rel_type=data.relationship_type,
        status=data.current_status,
        tension=data.tension_level,
        trust=data.trust_level
    )
    return {"id": memory.id, "created": True}


@router.get("/projects/{project_id}/relationships")
def list_relationships(
    project_id: int,
    character: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出关系记忆"""
    service = MemoryService(db)
    if character:
        relationships = service.list_character_relationships(project_id, character)
    else:
        relationships = db.query(RelationshipMemory).filter(
            RelationshipMemory.project_id == project_id
        ).all()

    return [{
        "id": r.id,
        "character_a": r.character_a,
        "character_b": r.character_b,
        "relationship_type": r.relationship_type,
        "current_status": r.current_status,
        "tension_level": r.tension_level,
        "trust_level": r.trust_level,
        "last_changed_chapter": r.last_changed_chapter
    } for r in relationships]


# ========== Context Assembly Endpoints ==========

@router.post("/projects/{project_id}/context")
def assemble_context(
    project_id: int,
    data: ContextAssemblyRequest,
    db: Session = Depends(get_db)
):
    """为章节组装上下文记忆"""
    service = MemoryService(db)
    context = service.assemble_context_for_chapter(
        project_id=project_id,
        chapter_index=data.chapter_index,
        mentioned_chars=data.mentioned_chars
    )
    prompt_text = service.format_context_for_prompt(context)

    return {
        "context": context,
        "prompt_text": prompt_text,
        "recent_chapters_count": len(context.get("recent_chapters", [])),
        "relevant_characters_count": len(context.get("relevant_characters", [])),
        "key_world_elements_count": len(context.get("key_world_elements", []))
    }


@router.post("/projects/{project_id}/update-from-chapter/{chapter_id}")
def update_memory_from_chapter(
    project_id: int,
    chapter_id: int,
    db: Session = Depends(get_db)
):
    """从章节内容更新记忆（同步简化版）"""
    from app.models.chapter import Chapter
    from app.services.memory_update_agent import MemoryUpdateAgent

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 简化版：只创建基础章节记忆
    service = MemoryService(db)

    # 检查是否已有记忆
    existing = service.get_chapter_memory(chapter_id)
    if existing:
        return {"message": "章节记忆已存在", "memory_id": existing.id}

    # 创建基础记忆
    memory = service.create_chapter_memory(
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_index=chapter.chapter_index,
        short_summary=f"第{chapter.chapter_index}章: {chapter.title}",
        detailed_summary=chapter.final_content[:2000] if chapter.final_content else ""
    )

    # 更新角色最后出现
    characters = service.list_characters(project_id, limit=50)
    updated_chars = []
    if chapter.final_content:
        for char in characters:
            if char.name in chapter.final_content:
                service.update_character_last_seen(char.id, chapter.chapter_index)
                updated_chars.append(char.name)

    return {
        "memory_id": memory.id,
        "chapter_memory_created": True,
        "characters_updated": updated_chars
    }


# ========== Import to main router ==========
from fastapi import APIRouter as FastAPIRouter

def register_memory_routes(parent_router: FastAPIRouter):
    """注册记忆路由到父路由器"""
    parent_router.include_router(router)
