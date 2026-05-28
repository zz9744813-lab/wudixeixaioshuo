"""
Bible Router - 小说圣经路由
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import NovelBible, Project
from app.services.bible_service import BibleService

router = APIRouter()


# Pydantic 模型
class WorldSettingUpdate(BaseModel):
    world_setting: str


class CharacterCreate(BaseModel):
    name: str
    role: str = "配角"  # 主角/配角/反派/导师等
    age: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    desires: Optional[str] = None
    flaws: Optional[str] = None
    background: Optional[str] = None
    abilities: Optional[str] = None
    notes: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    age: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    desires: Optional[str] = None
    flaws: Optional[str] = None
    background: Optional[str] = None
    abilities: Optional[str] = None
    notes: Optional[str] = None


class OutlineGenerate(BaseModel):
    volume_count: int = 3
    chapters_per_volume: int = 30


class ChapterOutlineUpdate(BaseModel):
    chapter_index: int
    title: Optional[str] = None
    summary: Optional[str] = None
    plot_points: Optional[List[str]] = None
    hooks: Optional[Dict] = None


@router.get("/projects/{project_id}/bible")
async def get_bible(project_id: int, db: Session = Depends(get_db)):
    """获取小说圣经"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    bible = BibleService.get_bible(db, project_id)
    if not bible:
        # 创建空的 bible
        bible = NovelBible(project_id=project_id)
        db.add(bible)
        db.commit()
        db.refresh(bible)

    return {
        "project_id": project_id,
        "world_setting": bible.world_setting,
        "world_rules": bible.world_rules or [],
        "timeline": bible.timeline or [],
        "characters": bible.characters or [],
        "character_relationships": bible.character_relationships or [],
        "main_plot": bible.main_plot,
        "sub_plots": bible.sub_plots or [],
        "foreshadowing": bible.foreshadowing or [],
        "style_boundaries": bible.style_boundaries or [],
        "tone_guidelines": bible.tone_guidelines,
        "forbidden_items": bible.forbidden_items or [],
        "volume_outline": bible.volume_outline or [],
        "chapter_outline": bible.chapter_outline or [],
    }


@router.post("/projects/{project_id}/bible/world-setting/generate")
async def generate_world_setting(
    project_id: int,
    hint: str = "",
    db: Session = Depends(get_db)
):
    """AI生成世界观设定"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    content = await BibleService.generate_world_setting(project, hint)

    # 保存到 bible
    BibleService.update_bible(db, project_id, {"world_setting": content})

    return {
        "project_id": project_id,
        "content": content,
        "message": "世界观已生成并保存",
    }


@router.put("/projects/{project_id}/bible/world-setting")
async def update_world_setting(
    project_id: int,
    data: WorldSettingUpdate,
    db: Session = Depends(get_db)
):
    """更新世界观设定"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    BibleService.update_bible(db, project_id, {"world_setting": data.world_setting})

    return {
        "project_id": project_id,
        "message": "世界观已更新",
    }


@router.get("/projects/{project_id}/bible/characters")
async def list_characters(project_id: int, db: Session = Depends(get_db)):
    """获取人物列表"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    bible = BibleService.get_bible(db, project_id)
    characters = bible.characters if bible and bible.characters else []

    return {
        "project_id": project_id,
        "characters": characters,
        "total": len(characters),
    }


@router.post("/projects/{project_id}/bible/characters")
async def add_character(
    project_id: int,
    character: CharacterCreate,
    db: Session = Depends(get_db)
):
    """添加人物"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    char_data = character.dict()
    bible = BibleService.add_character(db, project_id, char_data)

    return {
        "project_id": project_id,
        "character": char_data,
        "message": "人物已添加",
    }


@router.post("/projects/{project_id}/bible/characters/generate")
async def generate_character(
    project_id: int,
    role: str = "主角",
    traits_hint: str = "",
    db: Session = Depends(get_db)
):
    """AI生成人物"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    character = await BibleService.generate_character(project, role, traits_hint)

    # 添加到 bible
    BibleService.add_character(db, project_id, character)

    return {
        "project_id": project_id,
        "character": character,
        "message": f"{role}已生成并添加",
    }


@router.put("/projects/{project_id}/bible/characters/{character_id}")
async def update_character(
    project_id: int,
    character_id: int,
    updates: CharacterUpdate,
    db: Session = Depends(get_db)
):
    """更新人物"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    bible = BibleService.update_character(
        db, project_id, character_id, updates.dict(exclude_unset=True)
    )
    if not bible:
        raise HTTPException(status_code=404, detail="人物不存在")

    return {
        "project_id": project_id,
        "character_id": character_id,
        "message": "人物已更新",
    }


@router.delete("/projects/{project_id}/bible/characters/{character_id}")
async def delete_character(
    project_id: int,
    character_id: int,
    db: Session = Depends(get_db)
):
    """删除人物"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    success = BibleService.delete_character(db, project_id, character_id)
    if not success:
        raise HTTPException(status_code=404, detail="人物不存在")

    return {
        "project_id": project_id,
        "character_id": character_id,
        "message": "人物已删除",
    }


@router.post("/projects/{project_id}/bible/outline/generate")
async def generate_outline(
    project_id: int,
    data: OutlineGenerate,
    db: Session = Depends(get_db)
):
    """生成大纲"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    outline = await BibleService.generate_outline(
        project, data.volume_count, data.chapters_per_volume
    )

    # 保存到 bible
    BibleService.update_bible(db, project_id, {
        "main_plot": outline["main_plot"],
        "volume_outline": outline["volumes"],
        "chapter_outline": [
            chapter for volume in outline["volumes"] for chapter in volume["chapters"]
        ]
    })

    return {
        "project_id": project_id,
        "outline": outline,
        "message": "大纲已生成",
    }


@router.get("/projects/{project_id}/bible/outline")
async def get_outline(project_id: int, db: Session = Depends(get_db)):
    """获取大纲"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    bible = BibleService.get_bible(db, project_id)

    return {
        "project_id": project_id,
        "main_plot": bible.main_plot if bible else None,
        "volume_outline": bible.volume_outline if bible else [],
        "chapter_outline": bible.chapter_outline if bible else [],
    }


@router.put("/projects/{project_id}/bible/outline/chapters/{chapter_index}")
async def update_chapter_outline(
    project_id: int,
    chapter_index: int,
    data: ChapterOutlineUpdate,
    db: Session = Depends(get_db)
):
    """更新章节大纲"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    bible = BibleService.get_bible(db, project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="圣经不存在")

    # 找到并更新对应章节
    outline = bible.chapter_outline or []
    found = False
    for i, chapter in enumerate(outline):
        if chapter.get("chapter_index") == chapter_index:
            if data.title:
                outline[i]["title"] = data.title
            if data.summary:
                outline[i]["summary"] = data.summary
            if data.plot_points:
                outline[i]["plot_points"] = data.plot_points
            if data.hooks:
                outline[i]["hooks"] = data.hooks
            found = True
            break

    if not found:
        # 添加新章节
        outline.append({
            "chapter_index": chapter_index,
            "title": data.title or f"第{chapter_index}章",
            "summary": data.summary or "",
            "plot_points": data.plot_points or [],
            "hooks": data.hooks or {}
        })

    BibleService.update_bible(db, project_id, {"chapter_outline": outline})

    return {
        "project_id": project_id,
        "chapter_index": chapter_index,
        "message": "章节大纲已更新",
    }
