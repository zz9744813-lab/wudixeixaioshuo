"""
Memory Update Agent - 每章完成后更新长期记忆
使用 LLM 从章节内容提取结构化记忆
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.memory import CharacterMemory, WorldMemory, ChapterMemory, RelationshipMemory
from app.models.task import GenerationTask, GenerationStep
from app.services.memory_service import MemoryService
from app.services.openai_llm_service import llm_manager

logger = logging.getLogger(__name__)


class MemoryUpdateAgent:
    """记忆更新 Agent - 从章节内容提取并更新长期记忆"""

    def __init__(self, db: Session = None):
        self.db = db
        self._memory_service = None

    def _get_memory_service(self, db: Session) -> MemoryService:
        """获取或创建 MemoryService 实例"""
        if self._memory_service is None or db is not self.db:
            self.db = db
            self._memory_service = MemoryService(db)
        return self._memory_service

    async def update_from_chapter(
        self,
        project_id: int,
        chapter_id: int,
        chapter_index: int,
        chapter_title: str = "",
        chapter_content: str = "",
        plan: dict = None,
        bible: dict = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        从章节内容更新所有记忆类型
        返回更新摘要
        """
        # 使用传入的db或实例db
        db = db or self.db
        if not db:
            raise ValueError("需要传入 db 参数或在初始化时提供")

        memory_service = self._get_memory_service(db)

        logger.info(f"[MemoryUpdate] 开始更新章节 {chapter_index} 记忆")

        result = {
            "chapter_memory": None,
            "character_updates": [],
            "world_updates": [],
            "relationship_updates": [],
            "new_characters": [],
            "new_world_elements": []
        }

        try:
            # 1. 生成章节记忆（使用 LLM）
            chapter_mem = await self._generate_chapter_memory(
                memory_service, project_id, chapter_id, chapter_index, chapter_title,
                chapter_content, plan
            )
            result["chapter_memory"] = chapter_mem

            # 2. 提取并更新角色记忆
            char_updates = await self._extract_character_updates(
                memory_service, project_id, chapter_index, chapter_content, bible
            )
            result["character_updates"] = char_updates["updated"]
            result["new_characters"] = char_updates["new"]

            # 3. 提取世界观更新
            world_updates = await self._extract_world_updates(
                memory_service, project_id, chapter_index, chapter_content, bible
            )
            result["world_updates"] = world_updates["updated"]
            result["new_world_elements"] = world_updates["new"]

            # 4. 提取关系变化
            rel_updates = await self._extract_relationship_changes(
                memory_service, project_id, chapter_index, chapter_content
            )
            result["relationship_updates"] = rel_updates

            logger.info(f"[MemoryUpdate] 章节 {chapter_index} 记忆更新完成")
            return result

        except Exception as e:
            logger.error(f"[MemoryUpdate] 记忆更新失败: {e}")
            return result

    async def _generate_chapter_memory(
        self,
        memory_service: MemoryService,
        project_id: int,
        chapter_id: int,
        chapter_index: int,
        chapter_title: str,
        final_content: str,
        plan: dict = None
    ) -> Dict[str, Any]:
        """生成章节记忆摘要"""

        content_preview = final_content[:3000] if final_content else ""
        plan_text = json.dumps(plan, ensure_ascii=False) if plan else "无"

        prompt = f"""请为以下章节生成结构化记忆摘要：

章节标题: {chapter_title}
章节序号: {chapter_index}

章节正文（前3000字）:
{content_preview}

章节规划:
{plan_text}

请输出JSON格式：
{{
    "short_summary": "200-500字的章节短摘要",
    "detailed_summary": "1000-2000字的详细摘要",
    "key_events": ["事件1", "事件2", ...],
    "character_changes": [{{"name": "角色名", "change": "变化描述"}}],
    "world_updates": ["世界观更新1", ...],
    "relationship_changes": ["关系变化1", ...],
    "unresolved_questions": ["未解之谜1", ...],
    "foreshadow_updates": ["伏笔更新1", ...]
}}"""

        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role="memory_update",
                temperature=0.5
            )

            content = response.get("content", "")
            # 尝试解析JSON
            try:
                # 查找JSON块
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].strip()
                else:
                    json_str = content

                memory_data = json.loads(json_str)
            except json.JSONDecodeError:
                # 解析失败，使用简化版本
                memory_data = {
                    "short_summary": content[:500],
                    "detailed_summary": content[:2000],
                    "key_events": [],
                    "character_changes": [],
                    "world_updates": [],
                    "relationship_changes": [],
                    "unresolved_questions": [],
                    "foreshadow_updates": []
                }

            # 保存到数据库
            chapter_mem = memory_service.create_chapter_memory(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_index=chapter_index,
                short_summary=memory_data.get("short_summary", ""),
                detailed_summary=memory_data.get("detailed_summary", ""),
                key_events=memory_data.get("key_events", []),
                character_changes=memory_data.get("character_changes", []),
                world_updates=memory_data.get("world_updates", []),
                relationship_changes=memory_data.get("relationship_changes", []),
                unresolved_questions=memory_data.get("unresolved_questions", []),
                foreshadow_updates=memory_data.get("foreshadow_updates", [])
            )

            return {
                "id": chapter_mem.id,
                "short_summary": chapter_mem.short_summary,
                "key_events_count": len(chapter_mem.key_events)
            }

        except Exception as e:
            logger.error(f"生成章节记忆失败: {e}")
            # 创建基础记忆
            chapter_mem = memory_service.create_chapter_memory(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_index=chapter_index,
                short_summary=f"第{chapter_index}章: {chapter_title}",
                detailed_summary=final_content[:2000] if final_content else ""
            )
            return {"id": chapter_mem.id, "short_summary": chapter_mem.short_summary}

    async def _extract_character_updates(
        self,
        memory_service: MemoryService,
        project_id: int,
        chapter_index: int,
        final_content: str,
        bible: dict = None
    ) -> Dict[str, List]:
        """提取角色更新"""
        result = {"updated": [], "new": []}

        # 获取现有角色
        existing_chars = memory_service.list_characters(project_id, limit=100)
        existing_names = {c.name for c in existing_chars}

        bible_chars = bible.get("characters", []) if bible else []

        # 简单匹配：检查角色名是否出现在内容中
        for char_name in existing_names:
            if char_name in final_content:
                char = memory_service.get_character_by_name(project_id, char_name)
                if char:
                    memory_service.update_character_last_seen(char.id, chapter_index)
                    result["updated"].append(char_name)

        # 从 Bible 检查是否有新角色首次出现
        for bible_char in bible_chars:
            name = bible_char.get("name", "")
            if name and name in final_content and name not in existing_names:
                # 创建新角色记忆
                new_char = memory_service.create_character_memory(
                    project_id=project_id,
                    name=name,
                    role_type=bible_char.get("role_type", "supporting"),
                    stable_profile=bible_char,
                    first_chapter=chapter_index,
                    importance=bible_char.get("importance", 0.5)
                )
                result["new"].append(name)

        return result

    async def _extract_world_updates(
        self,
        memory_service: MemoryService,
        project_id: int,
        chapter_index: int,
        final_content: str,
        bible: dict = None
    ) -> Dict[str, List]:
        """提取世界观更新"""
        result = {"updated": [], "new": []}

        # Phase 1: 简化实现，后续接入 LLM
        # 检查 Bible 中的关键设定是否首次出现

        if bible:
            world_rules = bible.get("world_rules", [])
            for rule in world_rules:
                if isinstance(rule, str) and len(rule) > 5:
                    # 简单匹配规则关键词
                    keywords = rule[:20]  # 取前20字作为关键词
                    if keywords in final_content:
                        # 检查是否已存在
                        existing = memory_service.search_world_by_name(project_id, keywords[:20])
                        if not existing:
                            # 创建新的世界观记忆
                            memory_service.create_world_memory(
                                project_id=project_id,
                                category="rule",
                                name=f"规则: {keywords[:30]}...",
                                description=rule,
                                importance=0.6
                            )
                            result["new"].append(keywords[:30])

        return result

    async def _extract_relationship_changes(
        self,
        memory_service: MemoryService,
        project_id: int,
        chapter_index: int,
        final_content: str
    ) -> List[Dict]:
        """提取关系变化"""
        # Phase 1: 简化实现
        # 后续使用 LLM 分析
        return []

    def format_memory_for_next_chapter(
        self,
        memory_service: MemoryService,
        project_id: int,
        next_chapter_index: int
    ) -> str:
        """
        为下一章生成记忆上下文
        用于注入到 Prompt 中
        """
        context = memory_service.assemble_context_for_chapter(
            project_id=project_id,
            chapter_index=next_chapter_index
        )

        return memory_service.format_context_for_prompt(context)
