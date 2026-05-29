"""
Projects Router - 项目路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import NovelBible, Project, ProjectStatus
from app.models.technique import ProjectPlaybook
from app.utils.time_utils import utc_now

router = APIRouter()


# Pydantic 模型
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    genre: str
    target_reader: Optional[str] = None
    total_word_goal: int = 100000
    daily_word_goal: int = 3000
    chapter_word_goal: int = 3000


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    daily_word_goal: Optional[int] = None
    quality_threshold: Optional[int] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    genre: str
    status: str
    current_chapter_index: int
    total_words_written: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    projects = query.offset(skip).limit(limit).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "genre": p.genre,
            "status": p.status,
            "current_chapter_index": p.current_chapter_index,
            "total_words_written": p.total_words_written,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """创建新项目"""
    db_project = Project(
        name=project.name,
        description=project.description,
        genre=project.genre,
        target_reader=project.target_reader,
        total_word_goal=project.total_word_goal,
        daily_word_goal=project.daily_word_goal,
        chapter_word_goal=project.chapter_word_goal,
        status=ProjectStatus.DRAFT,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # 自动创建空的 Bible
    bible = NovelBible(project_id=db_project.id)
    db.add(bible)
    db.commit()

    return {
        "id": db_project.id,
        "name": db_project.name,
        "description": db_project.description,
        "genre": db_project.genre,
        "status": db_project.status,
        "current_chapter_index": db_project.current_chapter_index,
        "total_words_written": db_project.total_words_written,
        "created_at": db_project.created_at.isoformat() if db_project.created_at else None,
    }


@router.get("/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "genre": project.genre,
        "target_reader": project.target_reader,
        "status": project.status,
        "goals": {
            "total_word": project.total_word_goal,
            "daily_word": project.daily_word_goal,
            "chapter_word": project.chapter_word_goal,
        },
        "quality": {
            "plot_progress": project.plot_progress_intensity,
            "satisfaction": project.satisfaction_density,
            "threshold": project.quality_threshold,
        },
        "progress": {
            "current_chapter": project.current_chapter_index,
            "total_words": project.total_words_written,
        },
        "bible": {
            "world_setting": project.bible.world_setting if project.bible else None,
            "characters": project.bible.characters if project.bible else [],
        } if project.bible else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """更新项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return {"message": "项目已更新", "id": project.id}


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """删除项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    db.delete(project)
    db.commit()

    return {"message": "项目已删除", "id": project_id}


@router.post("/{project_id}/start")
async def start_project(project_id: int, db: Session = Depends(get_db)):
    """启动项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.status = ProjectStatus.ACTIVE
    from datetime import datetime
    project.started_at = utc_now()
    db.commit()

    return {"message": "项目已启动", "id": project.id, "status": project.status}


@router.post("/{project_id}/pause")
async def pause_project(project_id: int, db: Session = Depends(get_db)):
    """暂停项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.status = ProjectStatus.PAUSED
    db.commit()

    return {"message": "项目已暂停", "id": project.id, "status": project.status}


# ========== Playbook 接口 ==========

class PlaybookUpdate(BaseModel):
    source_techniques: Optional[list] = None
    rules: Optional[list] = None
    style_boundaries: Optional[str] = None
    tone_guidelines: Optional[str] = None
    chapter_template: Optional[dict] = None
    scoring_rubric: Optional[dict] = None


@router.post("/{project_id}/playbook")
async def update_playbook(
    project_id: int,
    playbook_data: PlaybookUpdate,
    db: Session = Depends(get_db)
):
    """创建或更新项目写作手册 (Playbook)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 查找或创建 Playbook
    playbook = db.query(ProjectPlaybook).filter(
        ProjectPlaybook.project_id == project_id
    ).first()

    if not playbook:
        playbook = ProjectPlaybook(project_id=project_id)
        db.add(playbook)

    # 更新字段
    if playbook_data.source_techniques is not None:
        playbook.source_techniques = playbook_data.source_techniques
    if playbook_data.rules is not None:
        playbook.rules = playbook_data.rules
    if playbook_data.style_boundaries is not None:
        playbook.style_boundaries = playbook_data.style_boundaries
    if playbook_data.tone_guidelines is not None:
        playbook.tone_guidelines = playbook_data.tone_guidelines
    if playbook_data.chapter_template is not None:
        playbook.chapter_template = playbook_data.chapter_template
    if playbook_data.scoring_rubric is not None:
        playbook.scoring_rubric = playbook_data.scoring_rubric

    db.commit()
    db.refresh(playbook)

    return {
        "message": "Playbook 已更新",
        "project_id": project_id,
        "source_techniques": playbook.source_techniques,
        "rules_count": len(playbook.rules) if playbook.rules else 0,
    }


@router.get("/{project_id}/playbook")
async def get_playbook(project_id: int, db: Session = Depends(get_db)):
    """获取项目写作手册"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    playbook = db.query(ProjectPlaybook).filter(
        ProjectPlaybook.project_id == project_id
    ).first()

    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook 不存在")

    return {
        "project_id": project_id,
        "source_techniques": playbook.source_techniques,
        "rules": playbook.rules,
        "style_boundaries": playbook.style_boundaries,
        "tone_guidelines": playbook.tone_guidelines,
        "chapter_template": playbook.chapter_template,
        "scoring_rubric": playbook.scoring_rubric,
    }


@router.get("/{project_id}/failures")
async def get_project_failures(project_id: int, db: Session = Depends(get_db)):
    """获取项目失败模式记录"""
    from app.models.technique import FailurePattern

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    failures = db.query(FailurePattern).filter(
        FailurePattern.project_id == project_id
    ).order_by(
        FailurePattern.occurrence_count.desc()
    ).all()

    return [
        {
            "id": f.id,
            "category": f.category,
            "symptom": f.symptom,
            "prevention_rule": f.prevention_rule,
            "occurrence_count": f.occurrence_count,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in failures
    ]
