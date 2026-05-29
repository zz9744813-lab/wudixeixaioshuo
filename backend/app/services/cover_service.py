"""
Cover Generator Service - 封面和元数据生成服务 (C2)
生成小说封面图片和元数据
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.chapter import Chapter

logger = logging.getLogger(__name__)


class CoverGeneratorService:
    """封面生成服务"""

    def __init__(self, db: Session):
        self.db = db
        self.covers_dir = Path("exports/covers")
        self.covers_dir.mkdir(parents=True, exist_ok=True)

    def generate_cover_prompt(
        self,
        project_id: int,
        style: str = "anime",
        composition: str = "character_focus"
    ) -> Dict[str, Any]:
        """
        生成封面图片描述（用于AI绘图）

        Args:
            project_id: 项目ID
            style: 风格（anime, realistic, ink, watercolor）
            composition: 构图（character_focus, scene, abstract, typography）

        Returns:
            封面生成prompt和元数据
        """
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        # 获取项目信息
        genre = project.genre or "玄幻"
        description = project.description or ""

        # 从圣经获取人物和世界观信息
        characters = []
        world_setting = ""
        if project.bible:
            characters = project.bible.characters or []
            world_setting = project.bible.world_setting or ""

        # 构建prompt
        prompt_data = self._build_cover_prompt(
            project_name=project.name,
            genre=genre,
            description=description,
            characters=characters,
            world_setting=world_setting,
            style=style,
            composition=composition
        )

        # 生成元数据
        metadata = self._generate_metadata(project)

        result = {
            "project_id": project_id,
            "project_name": project.name,
            "style": style,
            "composition": composition,
            "prompt": prompt_data["prompt"],
            "negative_prompt": prompt_data["negative_prompt"],
            "parameters": prompt_data["parameters"],
            "metadata": metadata,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(f"封面prompt生成: project_id={project_id}, style={style}")
        return result

    def _build_cover_prompt(
        self,
        project_name: str,
        genre: str,
        description: str,
        characters: List[Dict],
        world_setting: str,
        style: str,
        composition: str
    ) -> Dict[str, Any]:
        """构建封面生成prompt"""

        # 风格定义
        style_prompts = {
            "anime": "anime style, manga illustration, vibrant colors, detailed character design",
            "realistic": "photorealistic, cinematic lighting, highly detailed, professional photography",
            "ink": "traditional Chinese ink painting, watercolor wash, artistic brush strokes, elegant",
            "watercolor": "watercolor painting, soft colors, dreamy atmosphere, artistic illustration",
            "fantasy": "fantasy art, magical atmosphere, ethereal lighting, intricate details",
        }

        # 构图定义
        composition_prompts = {
            "character_focus": "character in center, portrait composition, facing viewer",
            "scene": "wide landscape, environmental scene, establishing shot",
            "action": "dynamic pose, action scene, energy and movement",
            "abstract": "symbolic elements, abstract representation, artistic composition",
            "typography": "title prominent, text integrated, book cover design",
        }

        # 题材元素
        genre_elements = {
            "玄幻": "cultivation, mystical energy, ancient Chinese fantasy, magical aura",
            "都市": "modern city, urban environment, contemporary setting",
            "仙侠": "immortal cultivation, flying swords, ethereal mountains, xianxia",
            "科幻": "futuristic, sci-fi elements, advanced technology, space",
            "悬疑": "mysterious atmosphere, dark tones, enigmatic elements",
            "恋爱": "romantic atmosphere, emotional, soft lighting, intimate",
            "历史": "historical setting, ancient architecture, period costume",
            "游戏": "game elements, level up indicators, gaming interface",
        }

        # 提取主要人物特征
        character_desc = ""
        if characters:
            main_char = characters[0]
            if isinstance(main_char, dict):
                char_name = main_char.get("name") or main_char.get("姓名", "")
                char_appearance = main_char.get("外貌", "")
                char_style = main_char.get("风格", "")
                if char_appearance:
                    character_desc = f"main character: {char_appearance}"
                elif char_style:
                    character_desc = f"main character: {char_style}"

        # 构建主prompt
        parts = [
            f"book cover for novel \"{project_name}\"",
            style_prompts.get(style, style_prompts["anime"]),
            composition_prompts.get(composition, composition_prompts["character_focus"]),
            genre_elements.get(genre, genre_elements["玄幻"]),
        ]

        if character_desc:
            parts.append(character_desc)

        if description:
            # 提取关键词
            keywords = self._extract_keywords(description)
            if keywords:
                parts.append(", ".join(keywords[:5]))

        # 负向prompt
        negative_prompt = (
            "low quality, blurry, distorted, deformed, ugly, duplicate, "
            "watermark, signature, text, logo, cropped, out of frame, "
            "worst quality, low resolution, error"
        )

        # 参数建议
        parameters = {
            "aspect_ratio": "2:3",  # 书籍封面常见比例
            "resolution": "1024x1536",
            "steps": 30,
            "cfg_scale": 7.0,
            "sampler": "DPM++ 2M Karras",
        }

        return {
            "prompt": ", ".join(filter(None, parts)),
            "negative_prompt": negative_prompt,
            "parameters": parameters,
        }

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """从描述中提取关键词"""
        # 简单的关键词提取（实际可以使用NLP库）
        # 移除常见停用词
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}

        # 分词并统计
        words = []
        for word in text.split():
            word = word.strip("，。！？、\"'\"()[]{}《》【】")
            if len(word) > 1 and word not in stopwords:
                words.append(word)

        # 去重并限制数量
        unique_words = list(dict.fromkeys(words))
        return unique_words[:max_keywords]

    def _generate_metadata(self, project: Project) -> Dict[str, Any]:
        """生成书籍元数据"""

        # 获取章节统计
        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project.id
        ).all()

        total_words = sum(c.word_count or 0 for c in chapters)
        completed_chapters = sum(1 for c in chapters if c.status.value == "completed")

        # 获取主要人物
        main_characters = []
        if project.bible and project.bible.characters:
            for char in project.bible.characters[:5]:
                if isinstance(char, dict):
                    main_characters.append(char.get("name") or char.get("姓名", ""))

        metadata = {
            "title": project.name,
            "subtitle": "",
            "author": project.config.get("author", "AI生成") if project.config else "AI生成",
            "genre": project.genre or "玄幻",
            "description": project.description or "",
            "keywords": self._extract_keywords(project.description or ""),
            "language": "zh-CN",
            "word_count": total_words,
            "chapter_count": len(chapters),
            "completed_chapters": completed_chapters,
            "main_characters": main_characters,
            "world_setting": project.bible.world_setting[:200] if project.bible and project.bible.world_setting else "",
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }

        return metadata

    def generate_simple_cover_html(
        self,
        project_id: int,
        template: str = "default"
    ) -> Dict[str, Any]:
        """
        生成简单封面 HTML（用于在线预览）

        Args:
            project_id: 项目ID
            template: 模板名称

        Returns:
            HTML 内容和元数据
        """
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        metadata = self._generate_metadata(project)

        # 简单的 HTML 模板
        html_templates = {
            "default": self._get_default_cover_template(),
            "minimal": self._get_minimal_cover_template(),
            "dramatic": self._get_dramatic_cover_template(),
        }

        template_html = html_templates.get(template, html_templates["default"])

        # 填充数据
        html_content = template_html.format(
            title=metadata["title"],
            author=metadata["author"],
            genre=metadata["genre"],
            description=metadata["description"][:100] + "..." if len(metadata["description"]) > 100 else metadata["description"],
            word_count=f"{metadata['word_count']:,}",
        )

        # 保存 HTML 文件
        filename = f"cover_{project_id}_{template}.html"
        filepath = self.covers_dir / filename
        filepath.write_text(html_content, encoding='utf-8')

        return {
            "project_id": project_id,
            "template": template,
            "html_content": html_content,
            "filepath": str(filepath),
            "metadata": metadata,
        }

    def _get_default_cover_template(self) -> str:
        """默认封面模板"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: 600px;
            height: 900px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            color: white;
            text-align: center;
            box-sizing: border-box;
            padding: 40px;
        }}
        .title {{
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            line-height: 1.3;
        }}
        .author {{
            font-size: 24px;
            margin-bottom: 40px;
            opacity: 0.9;
        }}
        .genre {{
            font-size: 18px;
            padding: 8px 24px;
            border: 2px solid rgba(255,255,255,0.5);
            border-radius: 20px;
            margin-bottom: 30px;
        }}
        .description {{
            font-size: 16px;
            line-height: 1.6;
            opacity: 0.8;
            max-width: 480px;
        }}
        .word-count {{
            position: absolute;
            bottom: 40px;
            font-size: 14px;
            opacity: 0.6;
        }}
    </style>
</head>
<body>
    <div class="genre">{genre}</div>
    <div class="title">{title}</div>
    <div class="author">作者：{author}</div>
    <div class="description">{description}</div>
    <div class="word-count">{word_count} 字</div>
</body>
</html>"""

    def _get_minimal_cover_template(self) -> str:
        """极简封面模板"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: 600px;
            height: 900px;
            background: #1a1a1a;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-family: "Microsoft YaHei", serif;
            color: #f0f0f0;
            text-align: center;
        }}
        .title {{
            font-size: 56px;
            font-weight: 300;
            letter-spacing: 8px;
            margin-bottom: 30px;
        }}
        .divider {{
            width: 100px;
            height: 2px;
            background: #f0f0f0;
            margin: 30px 0;
        }}
        .author {{
            font-size: 20px;
            letter-spacing: 4px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div class="title">{title}</div>
    <div class="divider"></div>
    <div class="author">{author}</div>
</body>
</html>"""

    def _get_dramatic_cover_template(self) -> str:
        """戏剧性封面模板"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: 600px;
            height: 900px;
            background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
            font-family: "Microsoft YaHei", sans-serif;
            color: white;
            text-align: center;
            padding-bottom: 100px;
            box-sizing: border-box;
            position: relative;
        }}
        body::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 50%;
            background: radial-gradient(ellipse at center, rgba(255,255,255,0.1) 0%, transparent 70%);
        }}
        .genre {{
            font-size: 16px;
            letter-spacing: 6px;
            text-transform: uppercase;
            margin-bottom: 20px;
            opacity: 0.7;
        }}
        .title {{
            font-size: 52px;
            font-weight: bold;
            margin-bottom: 15px;
            text-shadow: 0 0 30px rgba(255,255,255,0.3);
            z-index: 1;
        }}
        .author {{
            font-size: 20px;
            opacity: 0.8;
            z-index: 1;
        }}
    </style>
</head>
<body>
    <div class="genre">{genre}</div>
    <div class="title">{title}</div>
    <div class="author">{author} 著</div>
</body>
</html>"""

    def export_cover_metadata(
        self,
        project_id: int,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        导出封面元数据

        Args:
            project_id: 项目ID
            format: 导出格式（json, yaml, xml）

        Returns:
            元数据和文件路径
        """
        project = self.db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return {"error": "项目不存在"}

        metadata = self._generate_metadata(project)

        filename = f"metadata_{project_id}.{format}"
        filepath = self.covers_dir / filename

        if format == "json":
            content = json.dumps(metadata, ensure_ascii=False, indent=2)
        elif format == "yaml":
            try:
                import yaml
                content = yaml.dump(metadata, allow_unicode=True, default_flow_style=False)
            except ImportError:
                content = json.dumps(metadata, ensure_ascii=False, indent=2)
                filename = f"metadata_{project_id}.json"
                filepath = self.covers_dir / filename
        elif format == "xml":
            content = self._dict_to_xml(metadata, "book")
        else:
            return {"error": f"不支持的格式: {format}"}

        filepath.write_text(content, encoding='utf-8')

        return {
            "project_id": project_id,
            "format": format,
            "filepath": str(filepath),
            "filename": filename,
            "metadata": metadata,
        }

    def _dict_to_xml(self, data: Dict, root_name: str) -> str:
        """将字典转换为 XML"""
        def _to_xml(d, indent=0):
            lines = []
            for key, value in d.items():
                if isinstance(value, dict):
                    lines.append("  " * indent + f"<{key}>")
                    lines.append(_to_xml(value, indent + 1))
                    lines.append("  " * indent + f"</{key}>")
                elif isinstance(value, list):
                    lines.append("  " * indent + f"<{key}>")
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(_to_xml(item, indent + 1))
                        else:
                            lines.append("  " * (indent + 1) + f"<item>{item}</item>")
                    lines.append("  " * indent + f"</{key}>")
                else:
                    value_str = str(value) if value is not None else ""
                    lines.append("  " * indent + f"<{key}>{value_str}</{key}>")
            return "\n".join(lines)

        xml_content = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<{root_name}>\n"
        xml_content += _to_xml(data, 1)
        xml_content += f"\n</{root_name}>"

        return xml_content
