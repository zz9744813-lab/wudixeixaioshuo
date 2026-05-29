"""
Prompts Router - Prompt模板管理 API
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.services.prompt_template_service import PromptTemplateService

router = APIRouter()


class CreateTemplateRequest(BaseModel):
    role: str
    name: str
    content: str
    description: str = ""
    project_id: Optional[int] = None
    activate: bool = True


class RenderPreviewRequest(BaseModel):
    role: str
    variables: dict
    project_id: Optional[int] = None


@router.get("/templates")
def list_templates(
    role: Optional[str] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """列出版本历史"""
    service = PromptTemplateService(db)
    templates = service.list_templates(role, project_id)
    return [
        {
            "id": t.id,
            "role": t.role,
            "name": t.name,
            "version": t.version,
            "description": t.description,
            "is_active": t.is_active,
            "project_id": t.project_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in templates
    ]


@router.post("/templates")
def create_template(request: CreateTemplateRequest, db: Session = Depends(get_db)):
    """创建新版本"""
    service = PromptTemplateService(db)
    template = service.create_new_version(
        role=request.role,
        name=request.name,
        content=request.content,
        description=request.description,
        project_id=request.project_id,
        activate=request.activate,
    )
    return {
        "id": template.id,
        "role": template.role,
        "name": template.name,
        "version": template.version,
        "is_active": template.is_active,
    }


@router.get("/templates/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    """获取模板详情"""
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {
        "id": template.id,
        "role": template.role,
        "name": template.name,
        "version": template.version,
        "content": template.content,
        "description": template.description,
        "is_active": template.is_active,
        "project_id": template.project_id,
        "created_at": template.created_at.isoformat() if template.created_at else None,
    }


@router.post("/templates/{template_id}/activate")
def activate_template(template_id: int, db: Session = Depends(get_db)):
    """激活版本"""
    service = PromptTemplateService(db)
    template = service.activate_template(template_id)
    return {"id": template.id, "role": template.role, "version": template.version, "is_active": template.is_active}


@router.post("/templates/{template_id}/disable")
def disable_template(template_id: int, db: Session = Depends(get_db)):
    """停用版本"""
    service = PromptTemplateService(db)
    template = service.disable_template(template_id)
    return {"id": template.id, "role": template.role, "version": template.version, "is_active": template.is_active}


@router.post("/render-preview")
def render_preview(request: RenderPreviewRequest, db: Session = Depends(get_db)):
    """预览渲染"""
    service = PromptTemplateService(db)
    template = service.get_active_template(request.role, request.project_id)
    content = template.content if template else ""

    try:
        rendered = content.format(**request.variables)
        return {"prompt": rendered, "source": "database" if template else "fallback"}
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"缺少变量: {e}")
