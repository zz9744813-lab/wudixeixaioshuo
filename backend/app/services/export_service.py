"""
Export Service - 小说导出服务
支持多种格式导出
"""

import json
import logging
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """导出格式"""
    MARKDOWN = "md"
    TXT = "txt"
    DOCX = "docx"
    EPUB = "epub"
    PDF = "pdf"
    JSON = "json"


class ExportService:
    """
    小说导出服务

    支持格式：
    - Markdown: 带格式标记的文本
    - TXT: 纯文本
    - DOCX: Word 文档
    - EPUB: 电子书格式
    - PDF: 打印格式
    - JSON: 结构化数据
    """

    def __init__(self, db: Session):
        self.db = db
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)

    def export_project(
        self,
        project_id: int,
        format: ExportFormat,
        include_outline: bool = True,
        include_metadata: bool = True,
        chapter_filter: Optional[str] = "completed"  # all, completed, reviewed
    ) -> dict:
        """
        导出项目

        Args:
            project_id: 项目ID
            format: 导出格式
            include_outline: 是否包含大纲
            include_metadata: 是否包含元数据
            chapter_filter: 章节过滤条件
        """
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        # 获取章节
        query = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        )

        if chapter_filter == "completed":
            query = query.filter(Chapter.status == ChapterStatus.COMPLETED)
        elif chapter_filter == "reviewed":
            query = query.filter(Chapter.status.in_([
                ChapterStatus.REVIEW,
                ChapterStatus.COMPLETED
            ]))

        chapters = query.order_by(Chapter.order_num.asc()).all()

        if not chapters:
            return {"error": "没有可导出的章节"}

        # 根据格式导出
        exporters = {
            ExportFormat.MARKDOWN: self._export_markdown,
            ExportFormat.TXT: self._export_txt,
            ExportFormat.DOCX: self._export_docx,
            ExportFormat.EPUB: self._export_epub,
            ExportFormat.PDF: self._export_pdf,
            ExportFormat.JSON: self._export_json,
        }

        exporter = exporters.get(format)
        if not exporter:
            return {"error": f"不支持的格式: {format}"}

        try:
            result = exporter(project, chapters, include_outline, include_metadata)
            return result
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return {"error": f"导出失败: {str(e)}"}

    def _export_markdown(
        self,
        project: Project,
        chapters: List[Chapter],
        include_outline: bool,
        include_metadata: bool
    ) -> dict:
        """导出为 Markdown"""
        lines = []

        # 标题
        lines.append(f"# {project.name}")
        lines.append("")

        # 元数据
        if include_metadata:
            lines.append("---")
            lines.append(f"作者: {project.config.get('author', 'AI生成')}")
            lines.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"总章节数: {len(chapters)}")
            lines.append(f"总字数: {sum(c.word_count or 0 for c in chapters)}")
            lines.append("---")
            lines.append("")

        # 大纲
        if include_outline and project.outline:
            lines.append("## 大纲")
            lines.append(project.outline)
            lines.append("")
            lines.append("---")
            lines.append("")

        # 目录
        lines.append("## 目录")
        for i, ch in enumerate(chapters, 1):
            lines.append(f"{i}. {ch.title}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 章节内容
        for ch in chapters:
            lines.append(f"## {ch.title}")
            lines.append("")
            if ch.content:
                lines.append(ch.content)
            else:
                lines.append("*章节内容待生成*")
            lines.append("")
            lines.append("---")
            lines.append("")

        content = "\n".join(lines)

        # 保存文件
        filename = f"{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.export_dir / filename
        filepath.write_text(content, encoding='utf-8')

        return {
            "format": "markdown",
            "filename": filename,
            "filepath": str(filepath),
            "chapter_count": len(chapters),
            "word_count": sum(c.word_count or 0 for c in chapters),
        }

    def _export_txt(
        self,
        project: Project,
        chapters: List[Chapter],
        include_outline: bool,
        include_metadata: bool
    ) -> dict:
        """导出为纯文本"""
        lines = []

        lines.append(project.name)
        lines.append("=" * len(project.name))
        lines.append("")

        if include_metadata:
            lines.append(f"作者: {project.config.get('author', 'AI生成')}")
            lines.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append("")

        if include_outline and project.outline:
            lines.append("【大纲】")
            lines.append(project.outline)
            lines.append("")

        for ch in chapters:
            lines.append(f"\n{'='*40}")
            lines.append(f"第 {ch.order_num} 章")
            lines.append(ch.title)
            lines.append(f"{'='*40}\n")

            if ch.content:
                # 移除 Markdown 标记
                text = re.sub(r'#+ ', '', ch.content)
                text = re.sub(r'\*\*|__', '', text)
                text = re.sub(r'`', '', text)
                lines.append(text)
            else:
                lines.append("【章节内容待生成】")

            lines.append("")

        content = "\n".join(lines)

        filename = f"{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.export_dir / filename
        filepath.write_text(content, encoding='utf-8')

        return {
            "format": "txt",
            "filename": filename,
            "filepath": str(filepath),
            "chapter_count": len(chapters),
            "word_count": sum(c.word_count or 0 for c in chapters),
        }

    def _export_json(
        self,
        project: Project,
        chapters: List[Chapter],
        include_outline: bool,
        include_metadata: bool
    ) -> dict:
        """导出为 JSON"""
        data = {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "genre": project.genre,
                "target_words": project.target_words,
                "config": project.config if include_metadata else None,
            },
            "export_info": {
                "format": "json",
                "exported_at": datetime.now().isoformat(),
                "chapter_count": len(chapters),
                "total_word_count": sum(c.word_count or 0 for c in chapters),
            },
            "outline": project.outline if include_outline else None,
            "chapters": [
                {
                    "id": ch.id,
                    "order_num": ch.order_num,
                    "title": ch.title,
                    "content": ch.content,
                    "word_count": ch.word_count,
                    "status": ch.status.value if ch.status else None,
                    "metadata": ch.metadata,
                }
                for ch in chapters
            ]
        }

        content = json.dumps(data, ensure_ascii=False, indent=2)

        filename = f"{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.export_dir / filename
        filepath.write_text(content, encoding='utf-8')

        return {
            "format": "json",
            "filename": filename,
            "filepath": str(filepath),
            "chapter_count": len(chapters),
            "word_count": sum(c.word_count or 0 for c in chapters),
        }

    def _export_docx(
        self,
        project: Project,
        chapters: List[Chapter],
        include_outline: bool,
        include_metadata: bool
    ) -> dict:
        """导出为 Word 文档（简化版，返回 Markdown 作为中间格式）"""
        # 实际项目中使用 python-docx
        # 这里返回 Markdown，由前端转换
        result = self._export_markdown(
            project, chapters, include_outline, include_metadata
        )
        result["format"] = "docx"
        result["filename"] = result["filename"].replace(".md", ".docx")
        result["note"] = "请使用 Markdown 转换工具生成 DOCX"
        return result

    def _export_epub(
        self,
        project: Project,
        chapters: List[Chapter],
        include_outline: bool,
        include_metadata: bool
    ) -> dict:
        """导出为 EPUB（简化版）"""
        result = self._export_markdown(
            project, chapters, include_outline, include_metadata
        )
        result["format"] = "epub"
        result["filename"] = result["filename"].replace(".md", ".epub")
        result["note"] = "请使用 pandoc 等工具转换为 EPUB"
        return result

    def _export_pdf(
        self,
        project: Project,
        chapters: List[Chapter],
        include_outline: bool,
        include_metadata: bool
    ) -> dict:
        """导出为 PDF（简化版）"""
        result = self._export_markdown(
            project, chapters, include_outline, include_metadata
        )
        result["format"] = "pdf"
        result["filename"] = result["filename"].replace(".md", ".pdf")
        result["note"] = "请使用 pandoc 或 Markdown 转 PDF 工具"
        return result

    def get_export_history(
        self,
        project_id: Optional[int] = None,
        limit: int = 20
    ) -> List[dict]:
        """获取导出历史"""
        exports = []

        for filepath in sorted(self.export_dir.glob("*"), reverse=True)[:limit]:
            if filepath.is_file():
                stat = filepath.stat()
                exports.append({
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "format": filepath.suffix.lstrip("."),
                })

        return exports

    def delete_export(self, filename: str) -> bool:
        """删除导出文件"""
        filepath = self.export_dir / filename
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def get_word_count_stats(self, project_id: int) -> dict:
        """获取字数统计"""
        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        ).all()

        total = sum(c.word_count or 0 for c in chapters)
        completed = sum(
            c.word_count or 0 for c in chapters
            if c.status == ChapterStatus.COMPLETED
        )

        return {
            "total_chapters": len(chapters),
            "total_word_count": total,
            "completed_word_count": completed,
            "average_per_chapter": round(total / len(chapters), 0) if chapters else 0,
            "by_status": {
                "completed": sum(1 for c in chapters if c.status == ChapterStatus.COMPLETED),
                "writing": sum(1 for c in chapters if c.status == ChapterStatus.WRITING),
                "pending": sum(1 for c in chapters if c.status == ChapterStatus.PENDING),
            }
        }
