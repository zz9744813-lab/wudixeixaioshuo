"""Agent Planner Service - 主 Agent 动态计划生成与校验。"""

import json
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.services.llm_router import LLMRouter, LLMRouterAllProvidersFailed


class AgentPlanValidationError(ValueError):
    """Agent 计划格式或依赖关系非法。"""


class AgentPlannerService:
    """根据用户需求生成可执行计划，LLM 不可用时回退到确定性规则计划。"""

    ALLOWED_TOOLS: Set[str] = {
        "parse_novel_request",
        "create_project",
        "generate_bible",
        "plan_outline",
        "enqueue_chapters",
        "spawn_subagents",
        "build_report",
    }

    def __init__(self, db: Session):
        self.db = db

    async def create_plan(
        self,
        user_request: str,
        project_id: Optional[int] = None,
        max_steps: int = 30,
    ) -> Dict[str, Any]:
        """优先使用 planner 路由生成计划，失败时使用本地规则计划。"""
        try:
            plan = await self._create_llm_plan(
                user_request=user_request,
                project_id=project_id,
                max_steps=max_steps,
            )
            plan = self.validate_plan(plan, max_steps=max_steps)
            plan["planner_model"] = plan.get("planner_model") or "llm-router:planner"
            plan["planner_source"] = "llm"
            return plan
        except (LLMRouterAllProvidersFailed, AgentPlanValidationError, json.JSONDecodeError, TypeError, ValueError):
            plan = self.build_rule_based_plan(user_request=user_request)
            plan["planner_model"] = "rule-based-p0"
            plan["planner_source"] = "fallback"
            return plan

    async def _create_llm_plan(
        self,
        user_request: str,
        project_id: Optional[int],
        max_steps: int,
    ) -> Dict[str, Any]:
        """通过 LLMRouter 请求严格 JSON 计划。"""
        allowed_tools = ", ".join(sorted(self.ALLOWED_TOOLS))
        result = await LLMRouter(self.db).generate(
            role="planner",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是小说自主创作系统的 Planner。只能输出严格 JSON，不要输出解释。"
                        "计划必须可执行，steps 中每个步骤必须包含 step_key/title/tool_name/args/depends_on。"
                        f"tool_name 只能从以下列表选择：{allowed_tools}。"
                        "必须包含 create_project、generate_bible、plan_outline、enqueue_chapters、build_report，"
                        "如需要风险检查可加入 spawn_subagents。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_request": user_request,
                            "project_id": project_id,
                            "max_steps": max_steps,
                            "output_schema": {
                                "title": "计划标题",
                                "summary": "计划摘要",
                                "steps": [
                                    {
                                        "step_key": "唯一英文标识",
                                        "title": "步骤标题",
                                        "tool_name": "允许工具名",
                                        "args": {},
                                        "depends_on": [],
                                    }
                                ],
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            max_tokens=1800,
            temperature=0.2,
            trace={"component": "agent_planner"},
        )
        return self._extract_json_object(result.content)

    def _extract_json_object(self, content: str) -> Dict[str, Any]:
        """从模型输出中解析 JSON 对象，兼容误包裹的代码块。"""
        text = (content or "").strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise AgentPlanValidationError("Planner 输出不是 JSON 对象")
        return parsed

    def validate_plan(self, plan: Dict[str, Any], max_steps: int = 30) -> Dict[str, Any]:
        """校验计划结构、工具白名单、依赖 DAG 与步骤上限。"""
        if not isinstance(plan, dict):
            raise AgentPlanValidationError("计划必须是对象")
        steps = plan.get("steps")
        if not isinstance(steps, list) or not steps:
            raise AgentPlanValidationError("计划必须包含非空 steps")
        if max_steps and len(steps) > max_steps:
            raise AgentPlanValidationError("计划步骤数超过 max_steps")

        seen: Set[str] = set()
        normalized_steps: List[Dict[str, Any]] = []
        for index, raw_step in enumerate(steps):
            if not isinstance(raw_step, dict):
                raise AgentPlanValidationError("step 必须是对象")
            step_key = str(raw_step.get("step_key") or "").strip()
            title = str(raw_step.get("title") or step_key or f"步骤 {index + 1}").strip()
            tool_name = str(raw_step.get("tool_name") or "").strip()
            depends_on = raw_step.get("depends_on") or []
            args = raw_step.get("args") or {}

            if not step_key:
                raise AgentPlanValidationError("step_key 不能为空")
            if step_key in seen:
                raise AgentPlanValidationError(f"step_key 重复: {step_key}")
            if tool_name not in self.ALLOWED_TOOLS:
                raise AgentPlanValidationError(f"不允许的工具: {tool_name}")
            if not isinstance(depends_on, list):
                raise AgentPlanValidationError(f"depends_on 必须是列表: {step_key}")
            if not isinstance(args, dict):
                raise AgentPlanValidationError(f"args 必须是对象: {step_key}")
            missing = [dep for dep in depends_on if dep not in seen]
            if missing:
                raise AgentPlanValidationError(f"依赖必须指向前置步骤: {step_key} -> {missing}")

            seen.add(step_key)
            normalized_steps.append({
                "step_key": step_key,
                "title": title,
                "tool_name": tool_name,
                "args": args,
                "depends_on": depends_on,
            })

        required_tools = {"create_project", "generate_bible", "plan_outline", "enqueue_chapters", "build_report"}
        used_tools = {step["tool_name"] for step in normalized_steps}
        missing_tools = required_tools - used_tools
        if missing_tools:
            raise AgentPlanValidationError(f"计划缺少必要工具: {sorted(missing_tools)}")

        return {
            "title": str(plan.get("title") or "小说自主立项计划"),
            "summary": str(plan.get("summary") or "解析需求并完成小说项目立项。"),
            "steps": normalized_steps,
        }

    def build_rule_based_plan(self, user_request: str) -> Dict[str, Any]:
        """本地规则计划，保证没有 planner 路由时仍能产生真实可执行 DAG。"""
        chapter_count = 5 if any(key in user_request for key in ["5章", "五章"]) else 3
        plan = {
            "title": "小说自主立项 P0 动态兜底计划",
            "summary": "解析需求、创建项目、生成 Bible、规划大纲、入队章节、创建子 Agent、生成报告。",
            "steps": [
                {"step_key": "parse_request", "title": "解析用户需求", "tool_name": "parse_novel_request", "args": {}, "depends_on": []},
                {"step_key": "create_project", "title": "创建小说项目", "tool_name": "create_project", "args": {}, "depends_on": ["parse_request"]},
                {"step_key": "generate_bible", "title": "生成项目 Bible", "tool_name": "generate_bible", "args": {}, "depends_on": ["create_project"]},
                {"step_key": "plan_outline", "title": "生成首批章节大纲", "tool_name": "plan_outline", "args": {"chapter_count": chapter_count}, "depends_on": ["generate_bible"]},
                {"step_key": "enqueue_chapters", "title": "创建章节生成任务", "tool_name": "enqueue_chapters", "args": {}, "depends_on": ["plan_outline"]},
                {"step_key": "spawn_subagents", "title": "创建子 Agent 检查任务", "tool_name": "spawn_subagents", "args": {}, "depends_on": ["enqueue_chapters"]},
                {"step_key": "build_report", "title": "生成立项报告", "tool_name": "build_report", "args": {}, "depends_on": ["spawn_subagents"]},
            ],
        }
        return plan
