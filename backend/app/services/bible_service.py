"""
Novel Bible Service - 小说圣经服务
处理世界观、人物、大纲的生成和管理
"""

import json
import logging
import re
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.project import NovelBible, Project
from app.services.openai_llm_service import llm_manager

logger = logging.getLogger(__name__)


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
        response = await llm_manager.generate(prompt=prompt, role="planner")
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
        response = await llm_manager.generate(prompt=prompt, role="planner")
        # 尝试解析 JSON
        content = response["content"]
        try:
            # 提取 JSON 部分
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                char_data = json.loads(json_match.group())
                char_data["role_type"] = role
                return char_data
        except Exception as e:
            logger.warning(f"人物 JSON 解析失败: {e}")

        return {
            "name": role,
            "raw_content": content,
            "role_type": role,
        }

    @staticmethod
    async def generate_outline(
        project: Project,
        volume_count: int = 3,
        chapters_per_volume: int = 30,
        target_words_per_chapter: int = None,
        genre: str = None,
        style_profile: Dict = None
    ) -> Dict:
        """
        生成三层大纲：全书主线 Arc → 分卷 Arc → 章节 Arc

        Args:
            project: 项目对象
            volume_count: 分卷数量
            chapters_per_volume: 每卷章节数
            target_words_per_chapter: 每章目标字数（可选）
            genre: 题材类型（可选，默认使用 project.genre）
            style_profile: 风格档约束（可选）

        Returns:
            三层大纲结构字典
        """
        # 初始化 LLM 管理器
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            await llm_manager.init_from_db(db)
        finally:
            db.close()

        # 使用项目默认值
        genre = genre or project.genre
        target_words = target_words_per_chapter or project.chapter_word_goal or 2500
        total_chapters = volume_count * chapters_per_volume

        # 准备风格档约束文本
        style_constraints = ""
        if style_profile:
            style_constraints = f"""
风格档约束（必须遵守）：
- 平均每章字数: {style_profile.get('avg_chapter_words', '无要求')} 字
- 钩子频率: {style_profile.get('hook_rate', '无要求')}
- 爽点间隔: 每 {style_profile.get('payoff_cadence_chapters', '无要求')} 章
- 情绪曲线模板: {style_profile.get('emotion_curve_template', '无要求')}
- 开头模式: {style_profile.get('opening_patterns', '无要求')}
- 结尾模式: {style_profile.get('ending_patterns', '无要求')}
- 节奏规则: {style_profile.get('pacing_rules', '无要求')}
"""

        prompt = f"""你是长篇网文总编剧。请为下面这个小说项目生成可执行的三层大纲：全书主线 Arc、分卷 Arc、章节 Arc。

要求：
1. 不要写空泛概念，每一章必须有明确目标、冲突、爽点、章末钩子
2. 每一卷必须有卷内主冲突、卷末高潮、卷间钩子
3. 全书必须有主角成长线、主线矛盾、终局方向
4. 如果提供了结构指纹/风格档，必须遵守其中的节奏、钩子、爽点频率约束
5. 输出必须是严格 JSON，不要 Markdown，不要解释
6. 所有章节必须包含完整的字段，不要省略

项目信息：
- 题材: {genre}
- 总章节数: {total_chapters}
- 分卷数: {volume_count}
- 每卷章节数: {chapters_per_volume}
- 每章目标字数: {target_words} 字
- 项目描述: {project.description or '暂无描述'}
- 目标读者: {project.target_reader or '一般读者'}

{style_constraints}

请输出以下格式的 JSON（确保格式正确，可以被解析）：
{{
  "book_arc": {{
    "core_conflict": "全书核心矛盾",
    "protagonist_arc": "主角成长线",
    "finale_direction": "终局方向",
    "main_power_progression": "主线力量/能力成长",
    "reader_promise": "给读者的核心承诺"
  }},
  "volumes": [
    {{
      "volume_index": 1,
      "title": "卷标题",
      "core_conflict": "卷内主冲突",
      "volume_climax": "卷末高潮",
      "ending_hook": "卷间钩子",
      "chapters": [
        {{
          "chapter_index": 1,
          "title": "章标题",
          "goal": "本章目标",
          "conflict": "本章冲突",
          "plot_points": ["情节点1", "情节点2", "情节点3"],
          "payoff_beat": {{
            "type": "爽点类型（打脸/升级/揭秘/反转/情感爆点/获得资源）",
            "setup": "前置铺垫",
            "trigger": "触发点",
            "delivery_scene": "具体落地点",
            "reader_emotion": "期待读者产生的情绪"
          }},
          "ending_hook": "章末钩子",
          "foreshadow_to_plant": ["要埋设的伏笔"],
          "foreshadow_to_payoff": ["要回收的伏笔"],
          "target_words": {target_words}
        }}
      ]
    }}
  ]
}}

请为所有 {total_chapters} 章生成完整内容。"""

        # 第一次尝试生成
        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role="planner",
                temperature=0.7,
                max_tokens=8000
            )
            content = response["content"]
            outline = BibleService._parse_outline_json(content)

            # 验证结构完整性
            if BibleService._validate_outline_structure(outline, volume_count, chapters_per_volume):
                logger.info(f"大纲生成成功: {total_chapters} 章")
                return outline
            else:
                raise ValueError("大纲结构验证失败")

        except Exception as e:
            logger.warning(f"大纲生成第一次尝试失败: {e}，尝试修复...")

            # 第二次尝试：要求修复 JSON
            repair_prompt = f"""之前生成的大纲格式有误，请重新生成。

错误信息: {str(e)}

请严格输出合法的 JSON 格式，不要有任何 Markdown 标记或解释性文字。

{prompt}"""

            try:
                response = await llm_manager.generate(
                    prompt=repair_prompt,
                    role="planner",
                    temperature=0.5,
                    max_tokens=8000
                )
                content = response["content"]
                outline = BibleService._parse_outline_json(content)

                if BibleService._validate_outline_structure(outline, volume_count, chapters_per_volume):
                    logger.info(f"大纲修复成功: {total_chapters} 章")
                    return outline
                else:
                    raise ValueError("大纲结构验证仍然失败")

            except Exception as e2:
                logger.error(f"大纲生成最终失败: {e2}")
                # 返回一个基础结构作为 fallback
                return BibleService._generate_fallback_outline(
                    volume_count, chapters_per_volume, target_words, genre
                )

    @staticmethod
    def _parse_outline_json(content: str) -> Dict:
        """解析大纲 JSON，处理各种格式问题"""
        # 去除 Markdown 代码块标记
        content = re.sub(r'^```json\s*', '', content.strip())
        content = re.sub(r'```\s*$', '', content.strip())

        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 部分（匹配花括号）
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 尝试修复常见的 JSON 错误
        fixed = content
        # 修复尾随逗号
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        # 修复单引号
        fixed = fixed.replace("'", '"')

        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")

    @staticmethod
    def _validate_outline_structure(outline: Dict, expected_volumes: int, expected_chapters_per_volume: int) -> bool:
        """验证大纲结构是否完整"""
        # 检查顶层结构
        if "book_arc" not in outline:
            logger.warning("缺少 book_arc")
            return False

        if "volumes" not in outline or not isinstance(outline["volumes"], list):
            logger.warning("缺少 volumes 或格式错误")
            return False

        if len(outline["volumes"]) != expected_volumes:
            logger.warning(f"卷数不匹配: {len(outline['volumes'])} != {expected_volumes}")
            return False

        # 检查每卷结构
        for vol_idx, volume in enumerate(outline["volumes"], 1):
            required_volume_fields = ["volume_index", "title", "core_conflict", "chapters"]
            for field in required_volume_fields:
                if field not in volume:
                    logger.warning(f"第 {vol_idx} 卷缺少字段: {field}")
                    return False

            if len(volume["chapters"]) != expected_chapters_per_volume:
                logger.warning(f"第 {vol_idx} 卷章节数不匹配: {len(volume['chapters'])} != {expected_chapters_per_volume}")
                return False

            # 检查每章结构
            for chap_idx, chapter in enumerate(volume["chapters"], 1):
                required_chapter_fields = [
                    "chapter_index", "title", "goal", "conflict",
                    "plot_points", "payoff_beat", "ending_hook", "target_words"
                ]
                for field in required_chapter_fields:
                    if field not in chapter:
                        logger.warning(f"第 {vol_idx} 卷第 {chap_idx} 章缺少字段: {field}")
                        return False

        return True

    @staticmethod
    def _generate_fallback_outline(volume_count: int, chapters_per_volume: int, target_words: int, genre: str) -> Dict:
        """生成 fallback 大纲结构（当 LLM 失败时使用）"""
        logger.warning("使用 fallback 大纲结构")

        volumes = []
        chapter_index = 1

        for vol_num in range(1, volume_count + 1):
            chapters = []
            for _ in range(chapters_per_volume):
                chapters.append({
                    "chapter_index": chapter_index,
                    "title": f"第{chapter_index}章",
                    "goal": "推进剧情",
                    "conflict": "主要冲突",
                    "plot_points": ["情节点1", "情节点2"],
                    "payoff_beat": {
                        "type": "剧情推进",
                        "setup": "铺垫内容",
                        "trigger": "触发点",
                        "delivery_scene": "交付场景",
                        "reader_emotion": "期待"
                    },
                    "ending_hook": "下章预告",
                    "foreshadow_to_plant": [],
                    "foreshadow_to_payoff": [],
                    "target_words": target_words
                })
                chapter_index += 1

            volumes.append({
                "volume_index": vol_num,
                "title": f"第{vol_num}卷",
                "core_conflict": f"第{vol_num}卷核心冲突",
                "volume_climax": f"第{vol_num}卷高潮",
                "ending_hook": f"第{vol_num}卷结尾钩子",
                "chapters": chapters
            })

        return {
            "book_arc": {
                "core_conflict": "全书核心矛盾",
                "protagonist_arc": "主角成长线",
                "finale_direction": "终局方向",
                "main_power_progression": "主线力量成长",
                "reader_promise": "读者承诺"
            },
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
