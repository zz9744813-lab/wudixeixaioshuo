"""
Novel Bible Service - 小说圣经服务
处理世界观、人物、大纲的生成和管理
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.project import NovelBible, Project
from app.services.mock_llm_service import mock_llm_service


class BibleService:
    """小说圣经服务"""

    @staticmethod
    async def generate_world_setting(
        project: Project,
        prompt_hint: str = ""
    ) -> str:
        """生成世界观设定"""
        prompt = f"""
基于以下信息，生成详细的世界观设定：

题材: {project.genre}
目标读者: {project.target_reader or '一般读者'}
项目描述: {project.description or '暂无描述'}

用户提示: {prompt_hint or '创建一个丰富、有深度的世界观'}

请输出：
1. 世界背景（历史、地理、文化）
2. 力量体系/规则（如果有超自然元素）
3. 社会结构
4. 时代特征
"""
        response = await mock_llm_service.generate(prompt=prompt, role="planner")
        return response["content"]

    @staticmethod
    async def generate_character(
        project: Project,
        role: str = "主角",
        traits_hint: str = ""
    ) -> Dict:
        """生成人物卡"""
        prompt = f"""
为{project.genre}类型的小说创建一个{role}人物卡。

目标读者: {project.target_reader or '一般读者'}
题材特点: {project.description or '暂无描述'}
人物特点要求: {traits_hint or '根据题材自动生成'}

请输出以下信息（JSON格式）：
{{
    "name": "姓名",
    "age": "年龄",
    "appearance": "外貌特征",
    "personality": "性格特点",
    "desires": "核心欲望",
    "flaws": "性格缺陷",
    "background": "背景故事",
    "abilities": "能力/技能",
    "relationships": "重要关系"
}}
"""
        response = await mock_llm_service.generate(prompt=prompt, role="planner")
        # 简单解析，实际应该更健壮
        content = response["content"]
        return {
            "name": role,
            "raw_content": content,
            "role_type": role,
        }

    @staticmethod
    async def generate_outline(
        project: Project,
        volume_count: int = 3,
        chapters_per_volume: int = 30
    ) -> Dict:
        """生成卷纲和章纲"""
        prompt = f"""
为{project.genre}类型的小说生成完整大纲。

总字数目标: {project.total_word_goal}
卷数: {volume_count}
每卷章节数: {chapters_per_volume}

请输出：
1. 主线剧情概述
2. 每卷的核心冲突和爽点
3. 关键转折点
4. 结局方向
"""
        response = await mock_llm_service.generate(prompt=prompt, role="planner")

        # 生成卷纲结构
        volumes = []
        for i in range(1, volume_count + 1):
            volume = {
                "volume_number": i,
                "title": f"第{i}卷",
                "summary": f"第{i}卷的核心剧情...",
                "chapters": []
            }
            for j in range(1, chapters_per_volume + 1):
                chapter_index = (i - 1) * chapters_per_volume + j
                volume["chapters"].append({
                    "chapter_index": chapter_index,
                    "title": f"第{chapter_index}章",
                    "summary": "",
                    "plot_points": [],
                    "hooks": {}
                })
            volumes.append(volume)

        return {
            "main_plot": response["content"],
            "volumes": volumes,
            "total_chapters": volume_count * chapters_per_volume
        }

    @staticmethod
    def update_bible(
        db: Session,
        project_id: int,
        updates: Dict
    ) -> NovelBible:
        """更新小说圣经"""
        bible = db.query(NovelBible).filter(
            NovelBible.project_id == project_id
        ).first()

        if not bible:
            bible = NovelBible(project_id=project_id)
            db.add(bible)

        if "world_setting" in updates:
            bible.world_setting = updates["world_setting"]
        if "world_rules" in updates:
            bible.world_rules = updates["world_rules"]
        if "characters" in updates:
            bible.characters = updates["characters"]
        if "character_relationships" in updates:
            bible.character_relationships = updates["character_relationships"]
        if "main_plot" in updates:
            bible.main_plot = updates["main_plot"]
        if "sub_plots" in updates:
            bible.sub_plots = updates["sub_plots"]
        if "foreshadowing" in updates:
            bible.foreshadowing = updates["foreshadowing"]
        if "style_boundaries" in updates:
            bible.style_boundaries = updates["style_boundaries"]
        if "forbidden_items" in updates:
            bible.forbidden_items = updates["forbidden_items"]
        if "volume_outline" in updates:
            bible.volume_outline = updates["volume_outline"]
        if "chapter_outline" in updates:
            bible.chapter_outline = updates["chapter_outline"]

        db.commit()
        db.refresh(bible)
        return bible

    @staticmethod
    def get_bible(db: Session, project_id: int) -> Optional[NovelBible]:
        """获取小说圣经"""
        return db.query(NovelBible).filter(
            NovelBible.project_id == project_id
        ).first()

    @staticmethod
    def add_character(
        db: Session,
        project_id: int,
        character: Dict
    ) -> NovelBible:
        """添加人物"""
        bible = BibleService.get_bible(db, project_id)
        if not bible:
            bible = NovelBible(project_id=project_id, characters=[])
            db.add(bible)

        if not bible.characters:
            bible.characters = []

        character["id"] = len(bible.characters) + 1
        bible.characters.append(character)

        db.commit()
        db.refresh(bible)
        return bible

    @staticmethod
    def update_character(
        db: Session,
        project_id: int,
        character_id: int,
        updates: Dict
    ) -> Optional[NovelBible]:
        """更新人物"""
        bible = BibleService.get_bible(db, project_id)
        if not bible or not bible.characters:
            return None

        for i, char in enumerate(bible.characters):
            if char.get("id") == character_id:
                bible.characters[i].update(updates)
                break

        db.commit()
        db.refresh(bible)
        return bible

    @staticmethod
    def delete_character(
        db: Session,
        project_id: int,
        character_id: int
    ) -> bool:
        """删除人物"""
        bible = BibleService.get_bible(db, project_id)
        if not bible or not bible.characters:
            return False

        bible.characters = [
            c for c in bible.characters
            if c.get("id") != character_id
        ]

        db.commit()
        return True
