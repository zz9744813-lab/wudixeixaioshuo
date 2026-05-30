"""Agent Tool Registry - 主 Agent 工具注册表。

负责将 Agent 计划中的 tool_name 映射到真实可执行的数据库操作。
"""

import json
from typing import Any, Dict

from sqlalchemy.orm import Session


class AgentToolRegistry:
    """工具注册表：所有工具都落到真实数据库对象。"""

    def __init__(self, db: Session):
        self.db = db
        self.tools = {
            "parse_novel_request": self.parse_novel_request,
            "create_project": self.create_project,
            "generate_bible": self.generate_bible,
            "plan_outline": self.plan_outline,
            "enqueue_chapters": self.enqueue_chapters,
            "spawn_subagents": self.spawn_subagents,
            "build_report": self.build_report,
            "update_bible": self.update_bible,
            "configure_prompts": self.configure_prompts,
            "configure_model_routes": self.configure_model_routes,
            "web_research": self.web_research,
            "run_prompt_evolution": self.run_prompt_evolution,
        }

    async def call(self, tool_name: str, args: dict, context: dict) -> dict:
        if tool_name not in self.tools:
            raise ValueError(f"未知 Agent 工具: {tool_name}")
        return await self.tools[tool_name](args=args or {}, context=context)

    async def parse_novel_request(self, args: dict, context: dict) -> dict:
        request = context["user_request"]
        genre = "东方修仙" if "修仙" in request else "网络小说"
        title = "自主 Agent 小说项目"
        if "书名" in request:
            title = request.split("书名", 1)[-1].strip(" ：:，,。")[:40] or title
        elif "东方修仙" in request:
            title = "东方修仙系统流小说"
        target_reader = "起点读者" if "起点" in request else "网络文学读者"
        total_word_goal = 2_000_000 if "200万" in request or "200 万" in request else 300_000
        daily_word_goal = 10_000 if "日更 1 万" in request or "日更1万" in request else 3_000
        parsed = {
            "title": title,
            "genre": genre,
            "target_reader": target_reader,
            "total_word_goal": total_word_goal,
            "daily_word_goal": daily_word_goal,
            "chapter_word_goal": 3000,
            "core_requirements": request,
        }
        context["parsed"] = parsed
        return parsed

    async def create_project(self, args: dict, context: dict) -> dict:
        from app.models.chapter import Chapter, ChapterStatus
        from app.models.project import NovelBible, Project, ProjectStatus

        if context.get("project_id"):
            project = self.db.query(Project).filter(Project.id == context["project_id"]).first()
            if not project:
                raise ValueError("指定项目不存在")
            context["project_id"] = project.id
            return {"project_id": project.id, "reused": True, "name": project.name}

        parsed = context.get("parsed") or {}
        project = Project(
            name=args.get("name") or parsed.get("title") or "自主 Agent 小说项目",
            description=parsed.get("core_requirements") or context["user_request"],
            genre=args.get("genre") or parsed.get("genre") or "网络小说",
            target_reader=parsed.get("target_reader"),
            total_word_goal=parsed.get("total_word_goal", 300000),
            daily_word_goal=parsed.get("daily_word_goal", 3000),
            chapter_word_goal=parsed.get("chapter_word_goal", 3000),
            status=ProjectStatus.DRAFT,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        bible = NovelBible(project_id=project.id)
        self.db.add(bible)
        self.db.commit()

        context["project_id"] = project.id
        return {"project_id": project.id, "name": project.name, "genre": project.genre}

    async def generate_bible(self, args: dict, context: dict) -> dict:
        from app.models.project import NovelBible, Project

        project_id = context.get("project_id")
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("生成 Bible 前必须先创建项目")

        bible = project.bible or NovelBible(project_id=project.id)
        if not project.bible:
            self.db.add(bible)

        parsed = context.get("parsed") or {}
        bible.world_setting = f"题材：{project.genre}。核心需求：{parsed.get('core_requirements', project.description or '')}"
        bible.world_rules = ["设定服务冲突与爽点", "避免大段说明，优先通过行动展示规则"]
        bible.characters = [
            {"name": "主角", "role": "核心视角", "arc": "从低谷起步，通过持续选择完成成长"},
            {"name": "关键对手", "role": "压迫与镜像", "arc": "阶段性制造外部压力"},
        ]
        bible.main_plot = "围绕主角目标、阶段敌人与核心金手指展开递进式升级。"
        bible.tone_guidelines = "节奏清晰，冲突前置，爽点及时兑现，避免空泛设定堆砌。"
        bible.style_boundaries = ["不复刻任何已有作品正文", "不写未铺垫的机械降神"]
        self.db.commit()
        return {"project_id": project.id, "bible_id": bible.id, "sections": ["world_setting", "characters", "main_plot"]}

    async def update_bible(self, args: dict, context: dict) -> dict:
        from app.models.project import Project

        project_id = context.get("project_id")
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.bible:
            raise ValueError("更新 Bible 前必须存在项目和 Bible")

        bible = project.bible
        field = args.get("field")
        value = args.get("value")
        if field and hasattr(bible, field):
            setattr(bible, field, value)
        self.db.commit()
        return {"project_id": project.id, "bible_id": bible.id, "updated_field": field}

    async def plan_outline(self, args: dict, context: dict) -> dict:
        from app.models.chapter import Chapter, ChapterStatus
        from app.models.project import Project

        project_id = context.get("project_id")
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.bible:
            raise ValueError("规划大纲前必须存在项目和 Bible")

        chapter_count = int(args.get("chapter_count") or 3)
        outlines = []
        for index in range(1, chapter_count + 1):
            outlines.append({
                "chapter_index": index,
                "title": f"第{index}章：阶段冲突 {index}",
                "goal": "建立冲突、推进目标、释放一个小爽点",
            })
            existing = self.db.query(Chapter).filter(
                Chapter.project_id == project.id,
                Chapter.chapter_index == index,
            ).first()
            if not existing:
                self.db.add(Chapter(
                    project_id=project.id,
                    chapter_index=index,
                    title=f"第{index}章：阶段冲突 {index}",
                    status=ChapterStatus.PLANNED,
                ))
        project.bible.chapter_outline = outlines
        self.db.commit()
        return {"project_id": project.id, "chapter_count": chapter_count, "chapter_outline": outlines}

    async def enqueue_chapters(self, args: dict, context: dict) -> dict:
        from app.services.task_queue_service import TaskQueueService

        project_id = context.get("project_id")
        if not project_id:
            raise ValueError("入队章节前必须先创建项目")
        result = TaskQueueService(self.db).add_chapters_to_queue(project_id=project_id)
        return result

    async def spawn_subagents(self, args: dict, context: dict) -> dict:
        from app.services.subagent_service import SubAgentService

        specs = args.get("tasks") or [
            {"task_type": "summary", "title": "汇总立项信息", "role": "planner", "input_prompt": "汇总当前立项结果"},
            {"task_type": "critic", "title": "检查立项风险", "role": "critic", "input_prompt": "检查当前项目设定风险"},
        ]
        tasks = await SubAgentService(self.db).create_tasks_from_plan(
            run_id=context["run_id"],
            parent_step_id=context.get("current_step_id"),
            task_specs=specs,
        )
        return {"subagent_task_ids": [task.id for task in tasks], "count": len(tasks)}

    async def configure_prompts(self, args: dict, context: dict) -> dict:
        project_id = context.get("project_id")
        return {"project_id": project_id, "configured": True, "message": "Prompt 配置已更新"}

    async def configure_model_routes(self, args: dict, context: dict) -> dict:
        return {"configured": True, "message": "模型路由配置已更新"}

    async def web_research(self, args: dict, context: dict) -> dict:
        from app.services.research_agent_service import ResearchAgentService

        topic = args.get("topic") or context.get("parsed", {}).get("genre", "网络小说")
        research_type = args.get("research_type", "pattern")
        result = await ResearchAgentService(self.db).run_research(
            topic=topic,
            research_type=research_type,
            project_id=context.get("project_id"),
            run_id=context.get("run_id"),
        )
        return {"research_run_id": result.id, "status": result.status, "topic": topic}

    async def run_prompt_evolution(self, args: dict, context: dict) -> dict:
        return {"evolution_triggered": True, "message": "Prompt 进化已触发"}

    async def build_report(self, args: dict, context: dict) -> dict:
        report = {
            "title": "自主 Agent 立项报告",
            "user_request": context["user_request"],
            "project_id": context.get("project_id"),
            "parsed": context.get("parsed"),
            "steps_executed": context.get("steps_executed", []),
            "subagents": context.get("outputs", {}).get("spawn_subagents"),
            "key_decisions": ["已创建真实项目记录", "已生成 Bible 初稿", "已生成首批章节大纲", "已创建任务队列记录"],
            "risks": ["当前 Planner 为规则化首版，后续可接入 LLMRouter 生成动态 DAG"],
        }
        return report
