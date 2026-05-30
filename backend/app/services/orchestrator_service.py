"""Orchestrator Service - 主 Agent 编排服务。"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_run import (
    AgentPlan,
    AgentPlanStatus,
    AgentRun,
    AgentRunStatus,
    AgentStep,
    AgentStepStatus,
)
from app.models.chapter import Chapter, ChapterStatus
from app.models.project import NovelBible, Project, ProjectStatus
from app.services.task_queue_service import TaskQueueService
from app.utils.time_utils import utc_now


class AgentToolRegistry:
    """第一版工具注册表：全部工具都落到真实数据库对象。"""

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

    async def plan_outline(self, args: dict, context: dict) -> dict:
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


class OrchestratorService:
    def __init__(self, db: Session):
        self.db = db
        self.registry = AgentToolRegistry(db)

    async def start_run(
        self,
        user_request: str,
        project_id: Optional[int] = None,
        mode: str = "autonomous",
        budget_tokens: Optional[int] = None,
        budget_cost: Optional[float] = None,
        max_steps: int = 30,
        max_retries: int = 2,
        max_concurrency: int = 3,
    ) -> AgentRun:
        run = AgentRun(
            project_id=project_id,
            user_request=user_request,
            mode=mode,
            status=AgentRunStatus.PENDING,
            budget_tokens=budget_tokens,
            budget_cost=budget_cost,
            max_steps=max_steps,
            max_retries=max_retries,
            max_concurrency=max_concurrency,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_run(self, run_id: int) -> AgentRun:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            raise ValueError(f"运行记录不存在: {run_id}")
        if run.status == AgentRunStatus.CANCELLED:
            return run

        run.status = AgentRunStatus.RUNNING
        run.started_at = utc_now()
        self.db.commit()

        try:
            plan = self._create_plan(run)
            if run.mode == "require_approval":
                run.status = AgentRunStatus.PAUSED
                run.final_report = json.dumps({"paused_reason": "等待用户确认计划", "plan_id": plan.id}, ensure_ascii=False)
                self.db.commit()
                return run

            await self._execute_plan(run, plan)
            if run.status == AgentRunStatus.RUNNING:
                run.status = AgentRunStatus.SUCCEEDED
                run.finished_at = utc_now()
        except Exception as e:
            self.db.rollback()
            run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
            run.status = AgentRunStatus.FAILED
            run.error_message = str(e)
            run.finished_at = utc_now()
        finally:
            self.db.commit()
        return run

    def _create_plan(self, run: AgentRun) -> AgentPlan:
        existing = self.db.query(AgentPlan).filter(AgentPlan.run_id == run.id).first()
        if existing:
            return existing

        plan_json = {
            "title": "小说自主立项 P0 主干计划",
            "summary": "解析需求、创建项目、生成 Bible、规划大纲、入队章节、创建子 Agent、生成报告",
            "steps": [
                {"step_key": "parse_request", "title": "解析用户需求", "tool_name": "parse_novel_request", "args": {}, "depends_on": []},
                {"step_key": "create_project", "title": "创建小说项目", "tool_name": "create_project", "args": {}, "depends_on": ["parse_request"]},
                {"step_key": "generate_bible", "title": "生成项目 Bible", "tool_name": "generate_bible", "args": {}, "depends_on": ["create_project"]},
                {"step_key": "plan_outline", "title": "生成首批章节大纲", "tool_name": "plan_outline", "args": {"chapter_count": 3}, "depends_on": ["generate_bible"]},
                {"step_key": "enqueue_chapters", "title": "创建章节生成任务", "tool_name": "enqueue_chapters", "args": {}, "depends_on": ["plan_outline"]},
                {"step_key": "spawn_subagents", "title": "创建子 Agent 检查任务", "tool_name": "spawn_subagents", "args": {}, "depends_on": ["enqueue_chapters"]},
                {"step_key": "build_report", "title": "生成立项报告", "tool_name": "build_report", "args": {}, "depends_on": ["spawn_subagents"]},
            ],
        }
        plan = AgentPlan(
            run_id=run.id,
            title=plan_json["title"],
            summary=plan_json["summary"],
            plan_json=plan_json,
            planner_model="rule-based-p0",
            status=AgentPlanStatus.CREATED,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        for spec in plan_json["steps"]:
            self.db.add(AgentStep(
                run_id=run.id,
                plan_id=plan.id,
                step_key=spec["step_key"],
                title=spec["title"],
                tool_name=spec["tool_name"],
                args_json=spec.get("args") or {},
                depends_on=spec.get("depends_on") or [],
                status=AgentStepStatus.PENDING,
                created_at=utc_now(),
            ))
        self.db.commit()
        return plan

    async def _execute_plan(self, run: AgentRun, plan: AgentPlan):
        plan.status = AgentPlanStatus.EXECUTING
        self.db.commit()

        context: Dict[str, Any] = {
            "run_id": run.id,
            "project_id": run.project_id,
            "user_request": run.user_request,
            "steps_executed": [],
            "outputs": {},
        }
        steps = self.db.query(AgentStep).filter(AgentStep.plan_id == plan.id).order_by(AgentStep.id.asc()).all()
        executed = set()

        for step in steps:
            if not self._check_budget(run, len(executed)):
                run.status = AgentRunStatus.PAUSED
                run.error_message = "预算或最大步骤数超限，已暂停"
                break
            missing = [dep for dep in (step.depends_on or []) if dep not in executed]
            if missing:
                step.status = AgentStepStatus.SKIPPED
                step.error_message = f"依赖未完成: {missing}"
                self.db.commit()
                continue

            step.status = AgentStepStatus.RUNNING
            step.started_at = utc_now()
            step.attempt_count += 1
            step.input_snapshot = {"context_keys": list(context.keys()), "args": step.args_json or {}}
            self.db.commit()

            try:
                context["current_step_id"] = step.id
                output = await self.registry.call(step.tool_name, step.args_json or {}, context)
                step.output_json = output
                step.status = AgentStepStatus.SUCCEEDED
                step.finished_at = utc_now()
                executed.add(step.step_key)
                context["steps_executed"].append(step.step_key)
                context["outputs"][step.step_key] = output
                if context.get("project_id") and run.project_id != context.get("project_id"):
                    run.project_id = context.get("project_id")
                if step.step_key == "build_report":
                    run.final_report = json.dumps(output, ensure_ascii=False, indent=2)
                self.db.commit()
            except Exception as exc:
                step.status = AgentStepStatus.FAILED
                step.error_message = str(exc)
                step.finished_at = utc_now()
                run.status = AgentRunStatus.FAILED
                run.error_message = f"步骤 {step.step_key} 失败: {exc}"
                self.db.commit()
                return

        if run.status == AgentRunStatus.RUNNING:
            plan.status = AgentPlanStatus.DONE
        elif run.status == AgentRunStatus.FAILED:
            plan.status = AgentPlanStatus.FAILED
        self.db.commit()

    def _check_budget(self, run: AgentRun, executed_steps: int) -> bool:
        if run.max_steps is not None and executed_steps >= run.max_steps:
            return False
        if run.budget_tokens is not None and (run.used_tokens or 0) >= run.budget_tokens:
            return False
        if run.budget_cost is not None and (run.used_cost or 0) >= run.budget_cost:
            return False
        return True

    async def cancel_run(self, run_id: int) -> bool:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run or run.status in [AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]:
            return False
        run.status = AgentRunStatus.CANCELLED
        run.finished_at = utc_now()
        self.db.commit()
        return True

    def get_run_status(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return None
        plans = self.db.query(AgentPlan).filter(AgentPlan.run_id == run_id).order_by(AgentPlan.id.asc()).all()
        steps = self.db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.id.asc()).all()
        return {
            "id": run.id,
            "status": run.status,
            "mode": run.mode,
            "user_request": run.user_request,
            "project_id": run.project_id,
            "budget_tokens": run.budget_tokens,
            "budget_cost": run.budget_cost,
            "used_tokens": run.used_tokens,
            "used_cost": run.used_cost,
            "max_steps": run.max_steps,
            "max_retries": run.max_retries,
            "max_concurrency": run.max_concurrency,
            "plans": [{"id": p.id, "title": p.title, "summary": p.summary, "status": p.status, "plan_json": p.plan_json} for p in plans],
            "steps": [{
                "id": s.id,
                "step_key": s.step_key,
                "title": s.title,
                "tool_name": s.tool_name,
                "status": s.status,
                "attempt_count": s.attempt_count,
                "depends_on": s.depends_on,
                "input_snapshot": s.input_snapshot,
                "output_json": s.output_json,
                "error_message": s.error_message,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            } for s in steps],
            "final_report": run.final_report,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }

    def get_runs(self, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        query = self.db.query(AgentRun)
        if status:
            query = query.filter(AgentRun.status == status)
        runs = query.order_by(AgentRun.created_at.desc()).offset(offset).limit(limit).all()
        return [{
            "id": r.id,
            "status": r.status,
            "mode": r.mode,
            "user_request": r.user_request,
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        } for r in runs]


def get_orchestrator_service(db: Session) -> OrchestratorService:
    return OrchestratorService(db)
