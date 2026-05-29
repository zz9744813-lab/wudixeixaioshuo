"""
Export Router - 导出路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.export_service import ExportFormat, ExportService

router = APIRouter()


# ============== 请求模型 ==============

class ExportRequest(BaseModel):
    project_id: int
    format: str = "md"  # md, txt, docx, epub, pdf, json
    include_outline: bool = True
    include_metadata: bool = True
    chapter_filter: str = "completed"  # all, completed, reviewed


class ExportHistoryQuery(BaseModel):
    project_id: Optional[int] = None
    limit: int = 20


# ============== 导出 API ==============

@router.post("/")
async def export_project(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    导出项目

    支持格式：md, txt, docx, epub, pdf, json
    """
    service = ExportService(db)

    try:
        export_format = ExportFormat(request.format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {request.format}")

    result = service.export_project(
        project_id=request.project_id,
        format=export_format,
        include_outline=request.include_outline,
        include_metadata=request.include_metadata,
        chapter_filter=request.chapter_filter
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/download/{filename}")
async def download_export(filename: str):
    """下载导出文件"""
    from pathlib import Path
    import re

    # 安全检查：防止路径遍历攻击
    # 只允许字母数字、下划线、连字符和点
    if not re.match(r'^[\w\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="非法文件名")

    export_dir = Path("exports")
    filepath = export_dir / filename

    # 确保解析后的路径仍在 exports 目录内
    try:
        resolved_path = filepath.resolve()
        resolved_export_dir = export_dir.resolve()
        if not str(resolved_path).startswith(str(resolved_export_dir)):
            raise HTTPException(status_code=400, detail="非法文件路径")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="非法文件路径")

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    media_types = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".epub": "application/epub+zip",
        ".pdf": "application/pdf",
        ".json": "application/json",
    }

    media_type = media_types.get(filepath.suffix, "application/octet-stream")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type
    )


@router.get("/history")
async def get_export_history(
    project_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取导出历史"""
    service = ExportService(db)
    history = service.get_export_history(project_id, limit)

    return {
        "count": len(history),
        "exports": history
    }


@router.delete("/{filename}")
async def delete_export(
    filename: str,
    db: Session = Depends(get_db)
):
    """删除导出文件"""
    import re

    # 安全检查：防止路径遍历攻击
    if not re.match(r'^[\w\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="非法文件名")

    service = ExportService(db)
    success = service.delete_export(filename)

    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")

    return {"message": "文件已删除"}


# ============== 统计 API ==============

@router.get("/stats/word-count/{project_id}")
async def get_word_count_stats(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取项目字数统计"""
    service = ExportService(db)
    stats = service.get_word_count_stats(project_id)

    return stats


# ============== 格式列表 API ==============

@router.get("/formats")
async def get_export_formats():
    """获取支持的导出格式"""
    return {
        "formats": [
            {
                "id": "md",
                "name": "Markdown",
                "description": "带格式标记的文本，适合进一步编辑",
                "extension": ".md",
            },
            {
                "id": "txt",
                "name": "纯文本",
                "description": "无任何格式的纯文本",
                "extension": ".txt",
            },
            {
                "id": "docx",
                "name": "Word 文档",
                "description": "Microsoft Word 格式",
                "extension": ".docx",
            },
            {
                "id": "epub",
                "name": "EPUB 电子书",
                "description": "标准电子书格式",
                "extension": ".epub",
            },
            {
                "id": "pdf",
                "name": "PDF 文档",
                "description": "适合打印和分享",
                "extension": ".pdf",
            },
            {
                "id": "json",
                "name": "JSON 数据",
                "description": "结构化数据，包含完整元信息",
                "extension": ".json",
            },
        ]
    }
