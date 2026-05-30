"""
ChiefEditorAgent - 总编 Agent (P2)
不写正文，只为每章产出全局写作指令，并持久化到 EditorDirective。
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.editor import BookState, EditorDirective
from app.models.foreshadow import Foreshadow
from app.models.memory import ChapterMemory, CharacterMemory
from app.models.project import NovelBible, Project
from app.services.openai_llm_service import llm_manager
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class ChiefEditorAgent:
    """总编 Agent"""

    def __init__(self, db: Session):
        self.db = db

    async def build_chapter_directive(
        self,
        project_id: int,
        chapter_id: int,
        chapter_index: int,
        chapter_title: str = "",
    ) -> dict:
        context = self._gather_context(project_id, chapter_index)
        directive = await self._llm_build_directive(
            project_id, chapter_index, chapter_title, context
        )
        if not directive:
            directive = self._fallback_directive(chapter_index, chapter_title, context)

        formatted = self.format_directive_for_prompt(directive)
        self._persist(
            project_id, chapter_id, chapter_index, directive, formatted
        )
        return directive

    def _gather_context(self, project_id: int, chapter_index: int) -> dict:
        project = self.db.query(Project).filter(Project.id == project_id).first()
        bible = self.db.query(NovelBible).filter(
            NovelBible.project_id == project_id
        ).first()

        recent_mems = self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == project_id,
            ChapterMemory.chapter_index < chapter_index,
        ).order_by(ChapterMemory.chapter_index.desc()).limit(3).all()

        recent_chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status == ChapterStatus.COMPLETED,
            Chapter.total_score.isnot(None),
        ).order_by(Chapter.chapter_index.desc()).limit(5).all()
        recent_scores = [c.total_score for c in recent_chapters if c.total_score]

        active_fs = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status.in_(["planted", "developed", "ready_to_payoff"]),
        ).all()

        characters = self.db.query(CharacterMemory).filter(
            CharacterMemory.project_id == project_id,
        ).order_by(CharacterMemory.importance_score.desc()).limit(5).all()

        state = self.db.query(BookState).filter(
            BookState.project_id == project_id
        ).first()

        return {
            "genre": project.genre if project else "",
            "main_plot": (bible.main_plot if bible else "") or "",
            "volume_outline": (bible.volume_outline if bible else []) or [],
            "recent_summaries": [
                {"chapter_index": m.chapter_index, "summary": m.short_summary}
                for m in recent_mems
            ],
            "recent_scores": recent_scores,
            "avg_recent_score": (
                round(sum(recent_scores) / len(recent_scores), 1)
                if recent_scores else None
            ),
            "active_foreshadows": [
                {"id": f.id, "title": f.title, "status": f.status}
                for f in active_fs
            ],
            "ready_payoffs": [
                {"id": f.id, "title": f.title}
                for f in active_fs if f.status == "ready_to_payoff"
            ],
            "main_characters": [
                {"name": c.name, "summary": c.summary} for c in characters
            ],
            "book_state": {
                "current_volume": state.current_volume if state else None,
                "current_arc": state.current_arc if state else None,
                "current_stage": state.current_stage if state else None,
                "unresolved_conflicts": (state.unresolved_conflicts if state else []) or [],
            } if state else {},
        }

    async def _llm_build_directive(
        self, project_id, chapter_index, chapter_title, context
    ) -> Optional[dict]:
        prompt = self._build_prompt(chapter_index, chapter_title, context)
        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role="planner",
                temperature=0.6,
                db=self.db,
                request_type="chief_editor_directive",
                project_id=project_id,
            )
            content = response.get("content", "")
            return self._parse_json(content)
        except Exception as e:
            logger.warning(f"总编指令 LLM 调用失败: {e}")
            return None

    def _build_prompt(self, chapter_index, chapter_title, context) -> str:
        return (
            "你是网文总编，负责把控全书节奏。请基于全书状态，为下一章产出"
            "结构化的全局写作指令（不要写正文）。\n\n"
            f"题材：{context.get('genre')}\n"
            f"主线：{context.get('main_plot')[:500]}\n"
            f"当前章节序号：{chapter_index}  标题：{chapter_title}\n"
            f"近章摘要：{json.dumps(context.get('recent_summaries'), ensure_ascii=False)[:1200]}\n"
            f"近期评分：{context.get('recent_scores')} 均分：{context.get('avg_recent_score')}\n"
            f"活跃伏笔：{json.dumps(context.get('active_foreshadows'), ensure_ascii=False)[:800]}\n"
            f"可回收伏笔：{json.dumps(context.get('ready_payoffs'), ensure_ascii=False)[:400]}\n"
            f"主要角色：{json.dumps(context.get('main_characters'), ensure_ascii=False)[:800]}\n"
            f"全书状态：{json.dumps(context.get('book_state'), ensure_ascii=False)[:600]}\n\n"
            "严格输出如下 JSON（不要附加解释）：\n"
            "{\n"
            '  "global_position": {"volume": "", "arc": "", "stage": "", "chapter_role": ""},\n'
            '  "tension_target": {"start_level": 5, "peak_level": 7, "ending_level": 8, "emotion_curve": ""},\n'
            '  "plot_goals": [],\n'
            '  "payoff_goals": [],\n'
            '  "foreshadow_goals": [],\n'
            '  "character_arc_goals": {},\n'
            '  "commercial_goals": {"main_hook": "", "爽点类型": "", "avoid": []},\n'
            '  "risk_warnings": []\n'
            "}"
        )

    def _parse_json(self, content: str) -> Optional[dict]:
        if not content:
            return None
        text = content.strip()
        if "```" in text:
            parts = text.split("```")
            for p in parts:
                p = p.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    text = p
                    break
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None

    def _fallback_directive(self, chapter_index, chapter_title, context) -> dict:
        bs = context.get("book_state", {}) or {}
        return {
            "global_position": {
                "volume": bs.get("current_volume") or "",
                "arc": bs.get("current_arc") or "",
                "stage": bs.get("current_stage") or "",
                "chapter_role": f"推进主线，承接第{chapter_index - 1}章",
            },
            "tension_target": {
                "start_level": 5, "peak_level": 7, "ending_level": 8,
                "emotion_curve": "铺垫 → 升级 → 悬念",
            },
            "plot_goals": [],
            "payoff_goals": [p["title"] for p in context.get("ready_payoffs", [])],
            "foreshadow_goals": [
                f["title"] for f in context.get("active_foreshadows", [])
            ][:3],
            "character_arc_goals": {},
            "commercial_goals": {"main_hook": "", "爽点类型": "", "avoid": []},
            "risk_warnings": (
                ["近期评分偏低，需强化爽点与节奏"]
                if context.get("avg_recent_score") and context["avg_recent_score"] < 75
                else []
            ),
        }

    def format_directive_for_prompt(self, directive: dict) -> str:
        if not directive:
            return ""
        gp = directive.get("global_position", {}) or {}
        tt = directive.get("tension_target", {}) or {}
        cg = directive.get("commercial_goals", {}) or {}
        lines = []
        lines.append(
            f"- 全局定位：{gp.get('volume','')} / {gp.get('arc','')} / "
            f"{gp.get('stage','')}；本章作用：{gp.get('chapter_role','')}"
        )
        lines.append(
            f"- 张力目标：开 {tt.get('start_level','-')} → 峰 {tt.get('peak_level','-')} "
            f"→ 收 {tt.get('ending_level','-')}；情绪曲线：{tt.get('emotion_curve','')}"
        )
        if directive.get("plot_goals"):
            lines.append(f"- 剧情目标：{'；'.join(map(str, directive['plot_goals']))}")
        if directive.get("payoff_goals"):
            lines.append(f"- 回收目标：{'；'.join(map(str, directive['payoff_goals']))}")
        if directive.get("foreshadow_goals"):
            lines.append(f"- 伏笔目标：{'；'.join(map(str, directive['foreshadow_goals']))}")
        if directive.get("character_arc_goals"):
            lines.append(
                f"- 角色弧光：{json.dumps(directive['character_arc_goals'], ensure_ascii=False)}"
            )
        if cg:
            lines.append(
                f"- 商业目标：主钩子={cg.get('main_hook','')}；"
                f"爽点={cg.get('爽点类型','')}；避免={cg.get('avoid', [])}"
            )
        if directive.get("risk_warnings"):
            lines.append(f"- 风险提示：{'；'.join(map(str, directive['risk_warnings']))}")
        return "\n".join(lines)

    def _persist(self, project_id, chapter_id, chapter_index, directive, formatted):
        record = self.db.query(EditorDirective).filter(
            EditorDirective.chapter_id == chapter_id
        ).first()
        if record:
            record.directive = directive
            record.formatted_prompt = formatted
            record.chapter_index = chapter_index
            record.updated_at = utc_now()
        else:
            record = EditorDirective(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_index=chapter_index,
                directive=directive,
                formatted_prompt=formatted,
            )
            self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
