"""
Memory Service - 记忆系统服务
Phase 1: 支持角色、世界观、章节、关系记忆的CRUD和检索
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.memory import (
    CharacterMemory, WorldMemory, ChapterMemory,
    RelationshipMemory, MemoryQueryLog
)
from app.models.chapter import Chapter
from app.models.project import Project

logger = logging.getLogger(__name__)


class MemoryService:
    """记忆系统服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== Character Memory ==========

    def create_character_memory(
        self,
        project_id: int,
        name: str,
        role_type: str = "supporting",
        stable_profile: dict = None,
        dynamic_state: dict = None,
        personality: dict = None,
        goals: list = None,
        secrets: list = None,
        first_chapter: int = None,
        importance: float = 0.5
    ) -> CharacterMemory:
        """创建角色记忆"""
        memory = CharacterMemory(
            project_id=project_id,
            name=name,
            role_type=role_type,
            stable_profile=stable_profile or {},
            dynamic_state=dynamic_state or {},
            personality=personality or {},
            goals=goals or [],
            secrets=secrets or [],
            first_appearance_chapter=first_chapter,
            importance_score=importance
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        logger.info(f"[Memory] 创建角色记忆: {name} (project={project_id})")
        return memory

    def get_character_memory(self, memory_id: int) -> Optional[CharacterMemory]:
        """获取单个角色记忆"""
        return self.db.query(CharacterMemory).filter(
            CharacterMemory.id == memory_id
        ).first()

    def get_character_by_name(self, project_id: int, name: str) -> Optional[CharacterMemory]:
        """按名称获取角色"""
        return self.db.query(CharacterMemory).filter(
            CharacterMemory.project_id == project_id,
            CharacterMemory.name == name
        ).first()

    def list_characters(
        self,
        project_id: int,
        role_type: str = None,
        min_importance: float = 0.0,
        limit: int = 100
    ) -> List[CharacterMemory]:
        """列出项目角色"""
        query = self.db.query(CharacterMemory).filter(
            CharacterMemory.project_id == project_id,
            CharacterMemory.importance_score >= min_importance
        )
        if role_type:
            query = query.filter(CharacterMemory.role_type == role_type)
        return query.order_by(desc(CharacterMemory.importance_score)).limit(limit).all()

    def update_character_state(
        self,
        memory_id: int,
        state_updates: dict,
        reason: str = ""
    ) -> Optional[CharacterMemory]:
        """更新角色动态状态"""
        memory = self.get_character_memory(memory_id)
        if not memory:
            return None

        # 合并状态更新
        current_state = memory.dynamic_state or {}
        current_state.update(state_updates)
        memory.dynamic_state = current_state
        memory.latest_update_reason = reason
        memory.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(memory)
        logger.info(f"[Memory] 更新角色状态: {memory.name}, reason={reason}")
        return memory

    def update_character_last_seen(self, memory_id: int, chapter_index: int):
        """更新角色最后出现章节"""
        memory = self.get_character_memory(memory_id)
        if memory:
            memory.last_seen_chapter = chapter_index
            self.db.commit()

    # ========== World Memory ==========

    def create_world_memory(
        self,
        project_id: int,
        category: str,
        name: str,
        description: str = "",
        rules: list = None,
        constraints: list = None,
        related_chars: list = None,
        importance: float = 0.5,
        is_canon: int = 1
    ) -> WorldMemory:
        """创建世界观记忆"""
        memory = WorldMemory(
            project_id=project_id,
            category=category,
            name=name,
            description=description,
            rules=rules or [],
            constraints=constraints or [],
            related_characters=related_chars or [],
            importance_score=importance,
            is_canon=is_canon
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        logger.info(f"[Memory] 创建世界观记忆: {name} ({category})")
        return memory

    def get_world_memory(self, memory_id: int) -> Optional[WorldMemory]:
        """获取世界观记忆"""
        return self.db.query(WorldMemory).filter(
            WorldMemory.id == memory_id
        ).first()

    def list_world_memories(
        self,
        project_id: int,
        category: str = None,
        min_importance: float = 0.0,
        limit: int = 100
    ) -> List[WorldMemory]:
        """列出世世界观记忆"""
        query = self.db.query(WorldMemory).filter(
            WorldMemory.project_id == project_id,
            WorldMemory.importance_score >= min_importance
        )
        if category:
            query = query.filter(WorldMemory.category == category)
        return query.order_by(desc(WorldMemory.importance_score)).limit(limit).all()

    def search_world_by_name(
        self,
        project_id: int,
        name: str
    ) -> List[WorldMemory]:
        """按名称搜索世界观记忆"""
        return self.db.query(WorldMemory).filter(
            WorldMemory.project_id == project_id,
            WorldMemory.name.ilike(f"%{name}%")
        ).all()

    # ========== Chapter Memory ==========

    def create_chapter_memory(
        self,
        project_id: int,
        chapter_id: int,
        chapter_index: int,
        short_summary: str = "",
        detailed_summary: str = "",
        key_events: list = None,
        character_changes: list = None,
        world_updates: list = None,
        relationship_changes: list = None,
        unresolved_questions: list = None,
        foreshadow_updates: list = None
    ) -> ChapterMemory:
        """创建或更新章节记忆"""
        # 检查是否已存在
        existing = self.get_chapter_memory(chapter_id)
        if existing:
            # 更新现有记录
            existing.short_summary = short_summary
            existing.detailed_summary = detailed_summary
            existing.key_events = key_events or []
            existing.character_changes = character_changes or []
            existing.world_updates = world_updates or []
            existing.relationship_changes = relationship_changes or []
            existing.unresolved_questions = unresolved_questions or []
            existing.foreshadow_updates = foreshadow_updates or []
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"[Memory] 更新章节记忆: chapter {chapter_index}")
            return existing

        # 创建新记录
        memory = ChapterMemory(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_index=chapter_index,
            short_summary=short_summary,
            detailed_summary=detailed_summary,
            key_events=key_events or [],
            character_changes=character_changes or [],
            world_updates=world_updates or [],
            relationship_changes=relationship_changes or [],
            unresolved_questions=unresolved_questions or [],
            foreshadow_updates=foreshadow_updates or []
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        logger.info(f"[Memory] 创建章节记忆: chapter {chapter_index}")
        return memory

    def get_chapter_memory(self, chapter_id: int) -> Optional[ChapterMemory]:
        """获取章节记忆"""
        return self.db.query(ChapterMemory).filter(
            ChapterMemory.chapter_id == chapter_id
        ).first()

    def get_chapter_memory_by_index(
        self,
        project_id: int,
        chapter_index: int
    ) -> Optional[ChapterMemory]:
        """按章节序号获取记忆"""
        return self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == project_id,
            ChapterMemory.chapter_index == chapter_index
        ).first()

    def get_recent_chapter_memories(
        self,
        project_id: int,
        before_index: int,
        count: int = 5
    ) -> List[ChapterMemory]:
        """获取最近N章的记忆"""
        return self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == project_id,
            ChapterMemory.chapter_index < before_index
        ).order_by(desc(ChapterMemory.chapter_index)).limit(count).all()

    # ========== Relationship Memory ==========

    def create_relationship_memory(
        self,
        project_id: int,
        char_a: str,
        char_b: str,
        rel_type: str,
        status: str = "",
        tension: int = 0,
        trust: int = 0,
        history: list = None
    ) -> RelationshipMemory:
        """创建关系记忆"""
        memory = RelationshipMemory(
            project_id=project_id,
            character_a=char_a,
            character_b=char_b,
            relationship_type=rel_type,
            current_status=status,
            tension_level=tension,
            trust_level=trust,
            history=history or []
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        logger.info(f"[Memory] 创建关系记忆: {char_a} <-> {char_b} ({rel_type})")
        return memory

    def get_relationship(
        self,
        project_id: int,
        char_a: str,
        char_b: str
    ) -> Optional[RelationshipMemory]:
        """获取两个角色之间的关系"""
        # 双向查询
        rel = self.db.query(RelationshipMemory).filter(
            RelationshipMemory.project_id == project_id,
            RelationshipMemory.character_a == char_a,
            RelationshipMemory.character_b == char_b
        ).first()
        if not rel:
            rel = self.db.query(RelationshipMemory).filter(
                RelationshipMemory.project_id == project_id,
                RelationshipMemory.character_a == char_b,
                RelationshipMemory.character_b == char_a
            ).first()
        return rel

    def list_character_relationships(
        self,
        project_id: int,
        character_name: str
    ) -> List[RelationshipMemory]:
        """列出某角色的所有关系"""
        return self.db.query(RelationshipMemory).filter(
            RelationshipMemory.project_id == project_id,
            (RelationshipMemory.character_a == character_name) |
            (RelationshipMemory.character_b == character_name)
        ).all()

    def update_relationship(
        self,
        rel_id: int,
        status: str = None,
        tension_delta: int = 0,
        trust_delta: int = 0,
        event: dict = None,
        chapter_index: int = None
    ) -> Optional[RelationshipMemory]:
        """更新关系状态"""
        rel = self.db.query(RelationshipMemory).filter(
            RelationshipMemory.id == rel_id
        ).first()
        if not rel:
            return None

        if status:
            rel.current_status = status
        rel.tension_level = max(-100, min(100, rel.tension_level + tension_delta))
        rel.trust_level = max(-100, min(100, rel.trust_level + trust_delta))

        if event:
            history = rel.history or []
            history.append(event)
            rel.history = history

        if chapter_index:
            rel.last_changed_chapter = chapter_index

        rel.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rel)
        return rel

    # ========== Context Assembly ==========

    def assemble_context_for_chapter(
        self,
        project_id: int,
        chapter_index: int,
        mentioned_chars: List[str] = None
    ) -> Dict[str, Any]:
        """
        为章节生成组装上下文记忆
        Phase 1 最小实现：
        - 最近3章摘要
        - 相关角色记忆
        - 高重要世界观设定
        """
        context = {
            "recent_chapters": [],
            "relevant_characters": [],
            "key_world_elements": [],
            "relationships": []
        }

        # 1. 最近3章记忆
        recent = self.get_recent_chapter_memories(project_id, chapter_index, count=3)
        context["recent_chapters"] = [
            {
                "index": m.chapter_index,
                "short_summary": m.short_summary,
                "key_events": m.key_events
            }
            for m in reversed(recent)  # 按正序
        ]

        # 2. 相关角色
        if mentioned_chars:
            for char_name in mentioned_chars:
                char = self.get_character_by_name(project_id, char_name)
                if char:
                    context["relevant_characters"].append({
                        "name": char.name,
                        "role_type": char.role_type,
                        "dynamic_state": char.dynamic_state,
                        "summary": char.summary
                    })
        else:
            # 默认取重要角色
            important_chars = self.list_characters(project_id, min_importance=0.7, limit=5)
            context["relevant_characters"] = [
                {
                    "name": c.name,
                    "role_type": c.role_type,
                    "dynamic_state": c.dynamic_state,
                    "summary": c.summary
                }
                for c in important_chars
            ]

        # 3. 高重要世界观
        key_world = self.list_world_memories(project_id, min_importance=0.8, limit=5)
        context["key_world_elements"] = [
            {
                "category": w.category,
                "name": w.name,
                "description": w.description[:200] if w.description else ""
            }
            for w in key_world
        ]

        # 4. 相关关系
        if mentioned_chars and len(mentioned_chars) >= 2:
            for i, char_a in enumerate(mentioned_chars):
                for char_b in mentioned_chars[i+1:]:
                    rel = self.get_relationship(project_id, char_a, char_b)
                    if rel:
                        context["relationships"].append({
                            "char_a": char_a,
                            "char_b": char_b,
                            "type": rel.relationship_type,
                            "status": rel.current_status,
                            "tension": rel.tension_level,
                            "trust": rel.trust_level
                        })

        return context

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """将上下文格式化为Prompt文本"""
        sections = []

        # 最近章节
        if context.get("recent_chapters"):
            sections.append("## 最近章节摘要\n")
            for ch in context["recent_chapters"]:
                sections.append(f"第{ch['index']}章: {ch['short_summary'][:100]}...")
                if ch.get("key_events"):
                    sections.append(f"  关键事件: {', '.join(ch['key_events'][:3])}")
            sections.append("")

        # 角色状态
        if context.get("relevant_characters"):
            sections.append("## 相关角色状态\n")
            for char in context["relevant_characters"]:
                sections.append(f"**{char['name']}** ({char['role_type']})")
                if char.get("dynamic_state"):
                    state = char["dynamic_state"]
                    state_str = ", ".join([f"{k}={v}" for k, v in list(state.items())[:3]])
                    sections.append(f"  状态: {state_str}")
                if char.get("summary"):
                    sections.append(f"  简介: {char['summary'][:80]}...")
            sections.append("")

        # 世界观
        if context.get("key_world_elements"):
            sections.append("## 关键设定\n")
            for elem in context["key_world_elements"]:
                sections.append(f"**{elem['name']}** ({elem['category']})")
                if elem.get("description"):
                    sections.append(f"  {elem['description'][:100]}...")
            sections.append("")

        # 关系
        if context.get("relationships"):
            sections.append("## 人物关系\n")
            for rel in context["relationships"]:
                sections.append(f"**{rel['char_a']}** 与 **{rel['char_b']}**: {rel['type']}")
                sections.append(f"  状态: {rel['status'][:50]}...  紧张度:{rel['tension']} 信任度:{rel['trust']}")
            sections.append("")

        return "\n".join(sections)

    # ========== Memory Update from Chapter ==========

    def update_memory_from_chapter(
        self,
        project_id: int,
        chapter_id: int,
        chapter_index: int,
        final_content: str,
        plan: dict = None,
        critic_report: dict = None
    ) -> Dict[str, Any]:
        """
        从章节内容更新记忆
        Phase 1: 基础实现，后续接入 LLM Agent
        """
        result = {
            "chapter_memory_created": False,
            "characters_updated": [],
            "world_updated": [],
            "relationships_updated": []
        }

        # 1. 创建章节记忆（简化版）
        chapter_mem = self.create_chapter_memory(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_index=chapter_index,
            short_summary=f"第{chapter_index}章内容摘要（待LLM生成）",
            detailed_summary=final_content[:2000] if final_content else "",
            key_events=[]
        )
        result["chapter_memory_created"] = True

        # 2. 更新角色最后出现（简单匹配）
        characters = self.list_characters(project_id, limit=50)
        for char in characters:
            if char.name in final_content:
                self.update_character_last_seen(char.id, chapter_index)
                result["characters_updated"].append(char.name)

        logger.info(f"[Memory] 章节 {chapter_index} 记忆更新完成")
        return result
