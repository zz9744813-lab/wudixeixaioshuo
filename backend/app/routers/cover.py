"""
Cover Router - 封面和元数据生成 API
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cover_service import CoverGeneratorService
from app.models.project import Project

router = APIRouter(prefix="/api/covers", tags=["covers"])


class CoverPromptRequest(BaseModel):
    """封面生成请求"""
    style: str = "anime"  # anime, realistic, ink, watercolor, fantasy
    composition: str = "character_focus"  # character_focus, scene, action, abstract, typography


class CoverPromptResponse(BaseModel):
    """封面生成响应"""
    project_id: int
    project_name: str
    style: str
    composition: str
    prompt: str
    negative_prompt: str
    parameters: dict
    metadata: dict
    generated_at: str


class CoverHtmlRequest(BaseModel):
    """封面HTML生成请求"""
    template: str = "default"  # default, minimal, dramatic


class CoverHtmlResponse(BaseModel):
    """封面HTML响应"""
    project_id: int
    template: str
    html_content: str
    filepath: str
    metadata: dict


class MetadataExportRequest(BaseModel):
    """元数据导出请求"""
    format: str = "json"  # json, yaml, xml


class MetadataExportResponse(BaseModel):
    """元数据导出响应"""
    project_id: int
    format: str
    filepath: str
    filename: str
    metadata: dict


@router.post("/projects/{project_id}/prompt", response_model=CoverPromptResponse)
async def generate_cover_prompt(
    project_id: int,
    request: CoverPromptRequest,
    db: Session = Depends(get_db)
):
    """
    生成封面AI绘图prompt

    - **style**: 风格（anime, realistic, ink, watercolor, fantasy）
    - **composition**: 构图（character_focus, scene, action, abstract, typography）
    """
    service = CoverGeneratorService(db)
    result = service.generate_cover_prompt(
        project_id,
        style=request.style,
        composition=request.composition
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/projects/{project_id}/html", response_model=CoverHtmlResponse)
async def generate_cover_html(
    project_id: int,
    request: CoverHtmlRequest,
    db: Session = Depends(get_db)
):
    """
    生成封面HTML预览

    - **template**: 模板（default, minimal, dramatic）
    """
    service = CoverGeneratorService(db)
    result = service.generate_simple_cover_html(
        project_id,
        template=request.template
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/projects/{project_id}/metadata", response_model=MetadataExportResponse)
async def export_metadata(
    project_id: int,
    request: MetadataExportRequest,
    db: Session = Depends(get_db)
):
    """
    导出书籍元数据

    - **format**: 格式（json, yaml, xml）
    """
    service = CoverGeneratorService(db)
    result = service.export_cover_metadata(
        project_id,
        format=request.format
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/projects/{project_id}/metadata")
async def get_metadata(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取书籍元数据"""
    from sqlalchemy.orm import Session as SqlSession
    service = CoverGeneratorService(db)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = service._generate_metadata(project)
    return result


@router.get("/templates")
async def list_templates():
    """列出可用的封面模板"""
    return {
        "templates": [
            {
                "id": "default",
                "name": "默认",
                "description": "蓝色渐变背景，居中布局，适合大多数类型",
            },
            {
                "id": "minimal",
                "name": "极简",
                "description": "黑色背景，简洁排版，适合严肃题材",
            },
            {
                "id": "dramatic",
                "name": "戏剧性",
                "description": "深色渐变，底部对齐，适合玄幻/仙侠",
            },
        ],
        "styles": [
            {"id": "anime", "name": "动漫", "description": "日式动漫风格，色彩鲜明"},
            {"id": "realistic", "name": "写实", "description": "照片级真实感"},
            {"id": "ink", "name": "水墨", "description": "中国水墨画风格"},
            {"id": "watercolor", "name": "水彩", "description": "水彩画风格，柔和梦幻"},
            {"id": "fantasy", "name": "奇幻", "description": "奇幻艺术风格"},
        ],
        "compositions": [
            {"id": "character_focus", "name": "人物特写", "description": "以人物为中心"},
            {"id": "scene", "name": "场景", "description": "宽景构图，展现场景"},
            {"id": "action", "name": "动作", "description": "动态场景，充满能量"},
            {"id": "abstract", "name": "抽象", "description": "象征性元素，艺术化"},
            {"id": "typography", "name": "文字", "description": "突出标题文字"},
        ],
    }
