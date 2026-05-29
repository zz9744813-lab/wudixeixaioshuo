"""
Pipeline Service - 写作流水线服务
WORKER-002: 抽离写作流水线，实现短事务架构

职责：
- 执行完整的写作流水线 (Planner → Draft → Critic → Rewrite → Continuity → Learning)
- 每个 Agent step 使用独立的数据库 session
- 不维护内存状态，所有统计通过 DailyUsageStatsService 持久化
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

from app.database import SessionLocal
from app.models.chapter import Chapter, ChapterStatus, ChapterVersion
from app.models.project import Project, NovelBible
from app.models.task import GenerationTask, GenerationStep, TaskStatus
from app.services.openai_llm_service import llm_manager
from app.services.memory_service import MemoryService
from app.services.prompt_template_service import PromptTemplateService
from app.services.daily_usage_stats_service import DailyUsageStatsService
from app.services.book_analysis_service import BookAnalysisService
from app.services.event_bus import event_bus
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class PipelineService:
    """
    写作流水线服务 - 独立的流水线执行器

    设计原则：
    1. 无状态：不维护内存状态
    2. 短事务：每个 Agent step 独立 session
    3. 纯执行：只负责执行，不负责任务生命周期管理
    """

    async def run(self, task_id: int) -> Dict[str, Any]:
        """
        执行完整写作流水线

        Args:
            task_id: 任务ID

        Returns:
            {
                "success": bool,
                "error": str,
                "tokens_used": int,
                "cost": float,
                "word_count": int,
                "final_content": str,
                "final_score": int,
                ...
            }
        """
        # 使用短事务获取任务信息
        db = SessionLocal()
        try:
            gen_task = db.query(GenerationTask).filter(
                GenerationTask.id == task_id
            ).first()

            if not gen_task:
                return {"success": False, "error": f"任务 {task_id} 不存在"}

            chapter = db.query(Chapter).filter(
                Chapter.id == gen_task.chapter_id
            ).first()

            project = db.query(Project).filter(
                Project.id == gen_task.project_id
            ).first()

            if not chapter or not project:
                return {"success": False, "error": "关联的章节或项目不存在"}

            # 初始化 LLM
            await llm_manager.init_from_db(db)

            # 更新任务状态为运行中
            gen_task.status = TaskStatus.RUNNING
            gen_task.started_at = utc_now()
            chapter.status = ChapterStatus.DRAFTING
            db.commit()

            # 保存必要信息用于后续步骤
            task_info = {
                "task_id": gen_task.id,
                "chapter_id": chapter.id,
                "project_id": project.id,
                "chapter_title": chapter.title,
                "chapter_index": chapter.chapter_index,
            }
        finally:
            db.close()

        # 执行流水线（每个 step 独立 session）
        try:
            result = await self._run_pipeline_steps(task_info)

            # 短事务保存最终结果
            db = SessionLocal()
            try:
                self._save_pipeline_result(db, task_info, result)
            finally:
                db.close()

            return result

        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            # 短事务保存失败状态
            db = SessionLocal()
            try:
                gen_task = db.query(GenerationTask).filter(
                    GenerationTask.id == task_id
                ).first()
                if gen_task:
                    gen_task.status = TaskStatus.FAILED
                    gen_task.error_message = str(e)
                chapter = db.query(Chapter).filter(
                    Chapter.id == task_info["chapter_id"]
                ).first()
                if chapter:
                    chapter.status = ChapterStatus.FAILED
                db.commit()
            finally:
                db.close()

            return {"success": False, "error": str(e)}

    async def _run_pipeline_steps(self, task_info: Dict) -> Dict[str, Any]:
        """执行流水线各步骤，每个 step 独立 session"""
        steps_data = []
        total_tokens = 0
        total_cost = 0.0

        # 并行获取 Bible 数据、记忆上下文、风格档案上下文
        # 三个操作相互独立，可以并行执行以减少等待时间
        bible_task = self._get_bible_data(task_info["project_id"])
        memory_task = self._get_memory_context(
            task_info["project_id"],
            task_info["chapter_index"]
        )
        style_task = self._get_style_profile_context(
            task_info["project_id"],
            task_info["chapter_index"]
        )

        bible_data, memory_context, style_profile_context = await asyncio.gather(
            bible_task, memory_task, style_task
        )

        # ===== Step 1: Planner =====
        logger.info(f"[Task {task_info['task_id']}] Step 1: Planner")
        await event_bus.publish("agent.step.started", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Planner",
            "step_index": 1,
        })

        planner_result = await self._run_planner(
            task_info, bible_data, memory_context, style_profile_context
        )

        await event_bus.publish("agent.step.completed", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Planner",
            "step_index": 1,
            "tokens": planner_result.get("tokens", 0),
            "cost": planner_result.get("cost", 0.0),
        })

        steps_data.append(planner_result)
        total_tokens += planner_result.get("tokens", 0)
        total_cost += planner_result.get("cost", 0.0)

        if not planner_result.get("success"):
            return {"success": False, "error": "Planner 失败", "step": "planner"}

        chapter_plan = planner_result.get("plan", {})

        # ===== Step 2: Draft =====
        logger.info(f"[Task {task_info['task_id']}] Step 2: Draft")
        await event_bus.publish("agent.step.started", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Draft",
            "step_index": 2,
        })

        draft_result = await self._run_draft(
            task_info, bible_data, chapter_plan, memory_context, style_profile_context
        )

        await event_bus.publish("agent.step.completed", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Draft",
            "step_index": 2,
            "word_count": draft_result.get("word_count", 0),
            "target_words": draft_result.get("target_words", 0),
            "tokens": draft_result.get("tokens", 0),
            "cost": draft_result.get("cost", 0.0),
        })

        steps_data.append(draft_result)
        total_tokens += draft_result.get("tokens", 0)
        total_cost += draft_result.get("cost", 0.0)

        if not draft_result.get("success"):
            return {"success": False, "error": "Draft 失败", "step": "draft"}

        draft_content = draft_result.get("content", "")
        draft_word_count = draft_result.get("word_count", 0)

        # 保存草稿版本（独立 session）
        await self._save_draft_version(task_info, draft_content, chapter_plan, draft_word_count)

        # ===== Step 3: Critic =====
        logger.info(f"[Task {task_info['task_id']}] Step 3: Critic")
        await event_bus.publish("agent.step.started", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Critic",
            "step_index": 3,
        })

        critic_result = await self._run_critic(task_info, draft_content, bible_data)

        await event_bus.publish("agent.step.completed", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Critic",
            "step_index": 3,
            "tokens": critic_result.get("tokens", 0),
            "cost": critic_result.get("cost", 0.0),
        })

        steps_data.append(critic_result)
        total_tokens += critic_result.get("tokens", 0)
        total_cost += critic_result.get("cost", 0.0)

        if not critic_result.get("success"):
            return {"success": False, "error": "Critic 失败", "step": "critic"}

        score = critic_result.get("score", 0)
        score_breakdown = critic_result.get("score_breakdown", {})
        critique = critic_result.get("critique", "")

        # 保存评分（独立 session）
        await self._save_critic_result(task_info, score, critique)

        # ===== Step 4: Rewrite (如果分数不够) =====
        final_content = draft_content
        final_score = score

        if score < 80:
            rewrite_result = await self._run_rewrite_if_needed(
                task_info, draft_content, critic_result, bible_data, score, memory_context
            )

            if rewrite_result.get("success"):
                steps_data.extend(rewrite_result.get("steps", []))
                total_tokens += rewrite_result.get("tokens", 0)
                total_cost += rewrite_result.get("cost", 0.0)
                final_content = rewrite_result.get("final_content", draft_content)
                final_score = rewrite_result.get("final_score", score)

        # ===== Step 5: Continuity =====
        logger.info(f"[Task {task_info['task_id']}] Step 5: Continuity")
        await event_bus.publish("agent.step.started", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Continuity",
            "step_index": 5,
        })

        continuity_result = await self._run_continuity(
            task_info, final_content, bible_data, memory_context
        )

        await event_bus.publish("agent.step.completed", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Continuity",
            "step_index": 5,
            "tokens": continuity_result.get("tokens", 0),
            "cost": continuity_result.get("cost", 0.0),
        })

        steps_data.append(continuity_result)
        total_tokens += continuity_result.get("tokens", 0)
        total_cost += continuity_result.get("cost", 0.0)

        continuity_score = continuity_result.get("score", 0)

        # ===== Step 6: Learning =====
        logger.info(f"[Task {task_info['task_id']}] Step 6: Learning")
        await event_bus.publish("agent.step.started", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Learning",
            "step_index": 6,
        })

        learning_result = await self._run_learning(task_info, steps_data)

        await event_bus.publish("agent.step.completed", {
            "task_id": task_info["task_id"],
            "chapter_id": task_info["chapter_id"],
            "agent": "Learning",
            "step_index": 6,
            "tokens": learning_result.get("tokens", 0),
            "cost": learning_result.get("cost", 0.0),
        })

        steps_data.append(learning_result)
        total_tokens += learning_result.get("tokens", 0)
        total_cost += learning_result.get("cost", 0.0)

        return {
            "success": True,
            "completed_steps": len(steps_data),
            "total_steps": len(steps_data),
            "tokens_used": total_tokens,
            "cost": total_cost,
            "word_count": len(final_content),
            "final_content": final_content,
            "final_score": final_score,
            "continuity_score": continuity_score,
            "score_breakdown": score_breakdown,
            "steps": steps_data,
        }

    # ===== 各 Agent 执行方法 =====

    async def _run_planner(
        self, task_info: Dict, bible_data: Dict, memory_context: str, style_profile_context: Optional[Dict] = None
    ) -> Dict:
        """执行 Planner Agent"""
        db = SessionLocal()
        try:
            # 获取技巧卡、手册等
            techniques = self._get_project_techniques(db, task_info["project_id"])
            playbook = self._get_project_playbook(db, task_info["project_id"])

            tech_instructions = self._format_techniques_for_prompt(techniques)

            # 格式化风格档案规则
            style_rules = self._format_style_profile_for_planner(style_profile_context)

            # 渲染 Prompt
            template_service = PromptTemplateService(db)
            variables = {
                "chapter_title": task_info["chapter_title"],
                "chapter_index": task_info["chapter_index"],
                "world_setting": bible_data.get("world_setting", "无"),
                "characters": json.dumps(bible_data.get("characters", []), ensure_ascii=False),
                "main_plot": bible_data.get("main_plot", "无"),
                "chapter_outline": json.dumps(bible_data.get("chapter_outline", []), ensure_ascii=False),
                "memory_context": memory_context,
                "tech_instructions": tech_instructions,
                "playbook_rules": "\n".join(playbook.get("rules", ["无"])),
                "style_rules": style_rules,
            }

            prompt = template_service.render(
                role="planner",
                variables=variables,
                fallback=self._build_planner_fallback(variables),
                project_id=task_info["project_id"],
            )

            # 调用 LLM
            started_at = utc_now()
            response = await llm_manager.generate(
                prompt=prompt,
                role="planner",
                temperature=0.7,
                db=db,
                request_type="worker_planner",
                project_id=task_info["project_id"],
            )

            # 保存步骤
            self._save_step(db, task_info, "Planner", prompt, response)

            return {
                "success": True,
                "agent": "Planner",
                "plan": {"content": response.get("content", "")},
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }

        except Exception as e:
            logger.error(f"Planner 失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    async def _run_draft(
        self, task_info: Dict, bible_data: Dict, chapter_plan: Dict, memory_context: str, style_profile_context: Optional[Dict] = None
    ) -> Dict:
        """执行 Draft Agent - 支持目标字数和长章分段生成"""
        db = SessionLocal()
        try:
            techniques = self._get_project_techniques(db, task_info["project_id"])
            playbook = self._get_project_playbook(db, task_info["project_id"])

            tech_instructions = self._format_techniques_for_prompt(techniques)

            # 格式化风格档案规则
            style_rules = self._format_style_profile_for_draft(style_profile_context)

            # 获取目标字数
            target_words = self._get_target_words(task_info, bible_data, chapter_plan)
            max_words = int(target_words * 1.1)  # +10%
            min_words = int(target_words * 0.85)  # -15%

            # 判断是否需要分段生成
            if target_words > 4000:
                # 长章分段生成
                content = await self._run_segmented_draft(
                    task_info, bible_data, chapter_plan, memory_context,
                    tech_instructions, playbook, target_words
                )
            else:
                # 普通单次生成
                template_service = PromptTemplateService(db)
                variables = {
                    "chapter_title": task_info["chapter_title"],
                    "chapter_index": task_info["chapter_index"],
                    "chapter_plan": json.dumps(chapter_plan, ensure_ascii=False),
                    "memory_context": memory_context,
                    "world_setting": bible_data.get("world_setting", ""),
                    "characters": json.dumps(bible_data.get("characters", []), ensure_ascii=False),
                    "tech_instructions": tech_instructions,
                    "playbook_rules": "\n".join(playbook.get("rules", ["无"])),
                    "style_rules": style_rules,
                    "target_words": target_words,
                    "min_words": min_words,
                    "max_words": max_words,
                }

                prompt = template_service.render(
                    role="draft",
                    variables=variables,
                    fallback=self._build_draft_fallback(variables),
                    project_id=task_info["project_id"],
                )

                # 确保 prompt 中包含字数要求
                if "目标字数" not in prompt:
                    prompt = self._inject_word_count_requirement(
                        prompt, target_words, min_words, max_words, chapter_plan
                    )

                response = await llm_manager.generate(
                    prompt=prompt,
                    role="draft",
                    temperature=0.8,
                    max_tokens=min(4000, target_words * 2),  # 根据字数调整 max_tokens
                    db=db,
                    request_type="worker_draft",
                    project_id=task_info["project_id"],
                )

                content = response.get("content", "")

            # 计算实际字数（中文字数）
            actual_word_count = self._count_chinese_words(content)

            # 保存步骤
            self._save_step(db, task_info, "Draft", "", {"content": content[:500]})

            # 保存字数信息到结果
            return {
                "success": True,
                "agent": "Draft",
                "content": content,
                "word_count": actual_word_count,
                "target_words": target_words,
                "word_count_pass": actual_word_count >= min_words,
                "tokens": 0,  # 分段生成时统计复杂，简化处理
                "cost": 0.0,
            }

        except Exception as e:
            logger.error(f"Draft 失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def _get_target_words(self, task_info: Dict, bible_data: Dict, chapter_plan: Dict) -> int:
        """获取目标字数 - 优先级：章节大纲 > 项目默认 > 系统默认"""
        # 1. 尝试从章节规划中获取
        if isinstance(chapter_plan, dict):
            # 直接获取 target_words
            if "target_words" in chapter_plan:
                return chapter_plan["target_words"]
            # 从 plan content 中解析
            plan_content = chapter_plan.get("content", "")
            match = re.search(r'目标字数[:：]\s*(\d+)', plan_content)
            if match:
                return int(match.group(1))

        # 2. 从 bible 的 chapter_outline 中查找
        chapter_outline = bible_data.get("chapter_outline", [])
        for chap in chapter_outline:
            if isinstance(chap, dict) and chap.get("chapter_index") == task_info["chapter_index"]:
                if "target_words" in chap:
                    return chap["target_words"]

        # 3. 使用项目默认值（从数据库获取）
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == task_info["project_id"]).first()
            if project and project.chapter_word_goal:
                return project.chapter_word_goal
        finally:
            db.close()

        # 4. 系统默认
        return 2500

    def _count_chinese_words(self, text: str) -> int:
        """计算中文字数（不含标点和空格）"""
        import re
        # 匹配中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        # 匹配英文单词
        english_words = re.findall(r'[a-zA-Z]+', text)
        return len(chinese_chars) + len(english_words)

    def _inject_word_count_requirement(self, prompt: str, target: int, min_w: int, max_w: int, chapter_plan: Dict) -> str:
        """向 prompt 中注入字数要求"""
        ending_hook = ""
        if isinstance(chapter_plan, dict):
            ending_hook = chapter_plan.get("ending_hook", "")

        word_count_section = f"""

## 本章硬性长度要求（必须遵守）
- 目标字数：{target} 中文字
- 合格范围：{min_w} - {max_w} 中文字
- 如果内容不足，不允许用总结式结尾凑数，必须扩展冲突、动作、对话或心理变化
- 禁止使用"总之"、"综上所述"等总结性词语草草收尾
{('- 章末必须留下钩子：' + ending_hook) if ending_hook else ''}

请确保生成内容达到字数要求。"""

        # 在 "请直接输出" 之前插入
        if "请直接输出" in prompt:
            prompt = prompt.replace("请直接输出", word_count_section + "\n\n请直接输出")
        else:
            prompt += word_count_section

        return prompt

    async def _run_segmented_draft(
        self, task_info: Dict, bible_data: Dict, chapter_plan: Dict,
        memory_context: str, tech_instructions: str, playbook: Dict, target_words: int
    ) -> str:
        """分段生成长章 - beat sheet → 逐段扩写 → 合并 → 自检 → 补写"""
        logger.info(f"[Task {task_info['task_id']}] 启用分段生成，目标字数: {target_words}")

        # Step 1: 生成 beat sheet（段落规划）
        beats = await self._generate_beat_sheet(
            task_info, chapter_plan, target_words
        )

        # Step 2: 逐段生成
        segments = []
        previous_ending = ""

        for i, beat in enumerate(beats):
            segment = await self._generate_segment(
                task_info, bible_data, chapter_plan, memory_context,
                tech_instructions, playbook, beat, i, len(beats),
                previous_ending, target_words
            )
            segments.append(segment)
            # 保存最后 200 字作为下一段的上下文
            previous_ending = segment[-200:] if len(segment) > 200 else segment

        # Step 3: 合并
        full_content = "\n\n".join(segments)

        # Step 4: 自检字数缺口
        actual_words = self._count_chinese_words(full_content)
        if actual_words < target_words * 0.9:  # 少于 90% 需要补写
            logger.info(f"[Task {task_info['task_id']}] 字数不足 ({actual_words}/{target_words})，启动补写")
            supplement = await self._generate_supplement(
                task_info, full_content, target_words - actual_words, chapter_plan
            )
            full_content += "\n\n" + supplement

        return full_content

    async def _generate_beat_sheet(self, task_info: Dict, chapter_plan: Dict, target_words: int) -> List[Dict]:
        """生成本章的 beat sheet（段落规划）"""
        # 根据目标字数决定分段数
        segments_count = max(3, target_words // 1500)  # 每段约 1500 字

        db = SessionLocal()
        try:
            prompt = f"""请将以下章节规划拆分为 {segments_count} 个写作段落（beats），每个段落对应一个完整的小场景或情节单元。

章节标题: {task_info['chapter_title']}
章节序号: {task_info['chapter_index']}

章节规划:
{json.dumps(chapter_plan, ensure_ascii=False) if isinstance(chapter_plan, dict) else str(chapter_plan)}

目标总字数: {target_words} 字

请输出 JSON 格式：
{{
  "beats": [
    {{
      "index": 1,
      "title": "段落标题",
      "content": "本段要写的具体内容",
      "estimated_words": 1500,
      "key_elements": ["关键元素1", "关键元素2"]
    }}
  ]
}}

要求：
1. 每段必须有明确的起止点
2. 段与段之间要有自然过渡
3. 最后一段必须包含章末钩子"""

            response = await llm_manager.generate(
                prompt=prompt,
                role="planner",
                temperature=0.7,
                max_tokens=2000,
                db=db,
                request_type="worker_beat_sheet",
                project_id=task_info["project_id"],
            )

            content = response.get("content", "")
            # 解析 JSON
            try:
                data = json.loads(content)
                return data.get("beats", [])
            except:
                # 解析失败时创建默认 beats
                return [{"index": i+1, "title": f"段落{i+1}", "estimated_words": target_words//segments_count}
                        for i in range(segments_count)]

        finally:
            db.close()

    async def _generate_segment(
        self, task_info: Dict, bible_data: Dict, chapter_plan: Dict,
        memory_context: str, tech_instructions: str, playbook: Dict,
        beat: Dict, beat_index: int, total_beats: int,
        previous_ending: str, total_target_words: int
    ) -> str:
        """生成单个段落"""
        db = SessionLocal()
        try:
            estimated_words = beat.get("estimated_words", 1500)

            prompt = f"""请撰写本章的第 {beat_index + 1}/{total_beats} 个段落。

章节标题: {task_info['chapter_title']}
本段落职责: {beat.get('title', '')}
本段落内容要求: {beat.get('content', '')}
目标字数: {estimated_words} 字

{f'前一段结尾（请自然承接，不要重复开头）:\n{previous_ending}\n' if previous_ending else ''}

世界观设定:
{bible_data.get('world_setting', '')}

人物设定:
{json.dumps(bible_data.get('characters', []), ensure_ascii=False)}

记忆上下文:
{memory_context}

{tech_instructions}

写作手册规则:
{"\\n".join(playbook.get('rules', ['无']))}

重要提示：
1. 这是第 {beat_index + 1} 段，本章共 {total_beats} 段
2. 本章总目标字数: {total_target_words} 字
3. {'如果这是第一段，请直接切入场景，不要铺垫。' if beat_index == 0 else '请自然承接上一段结尾，不要重复介绍。'}
4. {'这是最后一段，必须包含章末钩子。' if beat_index == total_beats - 1 else '段末要有自然过渡，引导到下一段。'}
5. 直接输出段落正文，不要标注"第X段"。

请开始写作："""

            response = await llm_manager.generate(
                prompt=prompt,
                role="draft",
                temperature=0.8,
                max_tokens=min(4000, estimated_words * 2),
                db=db,
                request_type="worker_draft_segment",
                project_id=task_info["project_id"],
            )

            return response.get("content", "")

        finally:
            db.close()

    async def _generate_supplement(self, task_info: Dict, existing_content: str, words_needed: int, chapter_plan: Dict) -> str:
        """生成补写内容"""
        db = SessionLocal()
        try:
            ending_hook = chapter_plan.get("ending_hook", "") if isinstance(chapter_plan, dict) else ""

            prompt = f"""现有章节内容字数不足，需要补充约 {words_needed} 字。

现有内容结尾:
{existing_content[-500:]}

补充要求：
1. 扩展冲突细节、动作描写、对话或心理活动
2. 不要改变已有情节
3. 不要重复已有内容
4. {'必须包含章末钩子：' + ending_hook if ending_hook else '要有章末钩子'}

请直接输出需要补充的内容："""

            response = await llm_manager.generate(
                prompt=prompt,
                role="draft",
                temperature=0.8,
                max_tokens=min(4000, words_needed * 2),
                db=db,
                request_type="worker_draft_supplement",
                project_id=task_info["project_id"],
            )

            return response.get("content", "")

        finally:
            db.close()

    async def _run_critic(
        self, task_info: Dict, content: str, bible_data: Dict
    ) -> Dict:
        """执行 Critic Agent - 九维 Rubric 锚点评分 + 行级批注 + 一致性检查"""
        db = SessionLocal()
        try:
            # 获取模板服务
            template_service = PromptTemplateService(db)

            # 生成一致性检查prompt片段 (B4)
            consistency_prompt = ""
            try:
                from app.services.consistency_service import ConsistencyService
                consistency_service = ConsistencyService(db)
                consistency_prompt = consistency_service.generate_consistency_prompt(
                    task_info["project_id"],
                    task_info["chapter_id"]
                )
            except Exception as e:
                logger.warning(f"生成一致性检查prompt失败: {e}")

            # 准备变量
            variables = {
                "chapter_title": task_info['chapter_title'],
                "content": content,
                "consistency_requirements": consistency_prompt,
            }

            # 使用模板或 fallback
            prompt = template_service.render(
                role="critic",
                variables=variables,
                fallback=self._build_critic_rubric_prompt(task_info['chapter_title'], content, consistency_prompt),
                project_id=task_info["project_id"],
            )

            response = await llm_manager.generate(
                prompt=prompt,
                role="critic",
                temperature=0.3,
                max_tokens=4000,
                db=db,
                request_type="worker_critic",
                project_id=task_info["project_id"],
            )

            content_text = response.get("content", "")

            # 解析结构化输出
            structured_result = self._parse_critic_structured_output(content_text)

            # 验证结构化输出，如果无效则重试一次
            if not self._validate_critic_output(structured_result):
                logger.warning("Critic 输出验证失败，尝试修复...")
                repair_prompt = f"""之前的输出格式不正确，请严格按照要求的 JSON 格式重新输出。

{prompt}

错误信息：输出缺少必需的字段或格式不正确。

请只输出合法的 JSON，不要添加 Markdown 标记或解释。"""

                response = await llm_manager.generate(
                    prompt=repair_prompt,
                    role="critic",
                    temperature=0.2,
                    max_tokens=4000,
                    db=db,
                    request_type="worker_critic_repair",
                    project_id=task_info["project_id"],
                )
                content_text = response.get("content", "")
                structured_result = self._parse_critic_structured_output(content_text)

            # 保存详细结果
            self._save_step(
                db, task_info, "Critic", prompt, response,
                score=structured_result.get("overall_score", 0),
                score_breakdown=structured_result.get("dimension_scores", {})
            )

            return {
                "success": True,
                "agent": "Critic",
                "score": structured_result.get("overall_score", 0),
                "score_breakdown": structured_result.get("dimension_scores", {}),
                "anchored_comments": structured_result.get("anchored_comments", {}),
                "line_comments": structured_result.get("line_comments", []),
                "must_fix_items": structured_result.get("must_fix_items", []),
                "nice_to_have_items": structured_result.get("nice_to_have_items", []),
                "rewrite_plan": structured_result.get("rewrite_plan", []),
                "critique": content_text,  # 保留原始文本用于调试
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }

        except Exception as e:
            logger.error(f"Critic 失败: {e}")
            # 返回降级结果
            return {
                "success": True,  # 让流程继续
                "agent": "Critic",
                "score": 75,
                "score_breakdown": {},
                "must_fix_items": [],
                "rewrite_plan": [],
                "error": str(e),
            }
        finally:
            db.close()

    def _build_critic_rubric_prompt(self, chapter_title: str, content: str, consistency_prompt: str = "") -> str:
        """构建 Critic Rubric Prompt（当模板不可用时使用）"""
        consistency_section = f"\n\n## 一致性检查要求 (B4)\n{consistency_prompt}\n" if consistency_prompt else ""
        return f"""请对以下章节进行严格的多维度审稿评分。

章节标题: {chapter_title}

章节内容:
{content[:8000]}{consistency_section}

请严格按照以下九维 Rubric 进行评分，每维度必须引用原文证据。

## 评分锚点（Rubric）

### 1. 剧情推进 (plot_progress, 满分100)
- 90: 主线显著推进，有明确的冲突升级和剧情转折
- 70: 主线有推进，但节奏平缓或转折力度不足
- 50: 推进有限，信息重复或原地踏步
- 30: 无明显推进，读者无法获得新信息

### 2. 节奏控制 (pacing, 满分100)
- 90: 信息密度高，冲突推进和喘息段落张弛有度，无明显注水
- 70: 整体流畅，但存在 1-2 处可压缩段落
- 50: 多处重复解释或情绪停滞，影响阅读推进
- 30: 章节缺乏推进，主要由说明、回忆、重复心理活动构成

### 3. 人物一致性 (character_consistency, 满分100)
- 90: 所有角色言行符合设定，情绪转变有充分铺垫
- 70: 主角一致，配角偶有偏差，情绪转变略快
- 50: 存在人设偏离或 OOC 现象
- 30: 人物行为逻辑混乱，读者无法理解动机

### 4. 对话辨识度 (dialogue_distinction, 满分100)
- 90: 每个角色语言风格独特，即使不标注也能分辨说话人
- 70: 主角有辨识度，配角区分度一般
- 50: 对话风格趋同，多个角色说话方式类似
- 30: 所有角色说话一个调，如同同一个人

### 5. 爽点达成度 (payoff_delivery, 满分100)
- 90: 爽点设计精巧，铺垫充分，释放时机精准，情绪到位
- 70: 有爽点但铺垫不足或释放略显仓促
- 50: 爽点平淡，缺乏高潮感，或强行塞入
- 30: 无爽点或爽点与主线无关

### 6. 章末钩子 (ending_hook, 满分100)
- 90: 钩子强烈，引发强烈追更欲望，与下一章紧密关联
- 70: 有悬念但力度中等，读者有一定期待
- 50: 钩子弱或过于套路，读者兴趣不大
- 30: 无钩子，章节结束得过于"圆满"

### 7. 文风稳定性 (style_stability, 满分100)
- 90: 全文风格统一，用词、句式、描写手法一致
- 70: 整体统一，偶有段落风格偏离
- 50: 前后风格明显不一致，仿佛不同作者
- 30: 风格混乱，影响阅读体验

### 8. 连续性/设定一致 (continuity, 满分100)
- 90: 无设定冲突，伏笔呼应到位，与前文衔接流畅
- 70: minor 设定问题但不影响理解
- 50: 存在设定矛盾或伏笔丢失
- 30: 严重设定冲突或逻辑错误

### 9. 商业可读性 (commercial_readability, 满分100)
- 90: 开头抓人，节奏明快，有追更动力，符合网文套路但不俗套
- 70: 可读性良好，但缺乏亮点
- 50: 平铺直叙，缺乏吸引力
- 30: 晦涩难懂或过于文艺，不符合网文调性

## 输出要求（严格 JSON 格式）

必须输出以下结构的 JSON，不要 Markdown 代码块标记，不要解释：

{{
  "overall_score": 78,
  "dimension_scores": {{
    "plot_progress": 80,
    "pacing": 72,
    "character_consistency": 75,
    "dialogue_distinction": 62,
    "payoff_delivery": 70,
    "ending_hook": 85,
    "style_stability": 77,
    "continuity": 90,
    "commercial_readability": 76
  }},
  "anchored_comments": {{
    "pacing": "按 rubric 属于 70 档：整体流畅，但中段重复解释主角动机。"
  }},
  "line_comments": [
    {{
      "quote": "原文短句，不超过 60 字",
      "line_number": 123,
      "issue_type": "telling_not_showing",
      "severity": "medium",
      "comment": "这里直接说明情绪，建议改成动作和对话体现。",
      "rewrite_suggestion": "建议改写方向"
    }}
  ],
  "must_fix_items": [
    "问题1: 描述...",
    "问题2: 描述..."
  ],
  "nice_to_have_items": [
    "建议1: 描述..."
  ],
  "rewrite_plan": [
    "第1轮：修复设定冲突和连续性问题",
    "第2轮：加强爽点铺垫和释放",
    "第3轮：优化对话辨识度"
  ]
}}

要求：
1. 每个低于 70 分的维度必须在 anchored_comments 中解释原因，并引用 rubric 档位
2. line_comments 至少包含 3-5 条，引用具体原文片段作为证据
3. must_fix_items 按优先级排序，必须是具体可执行的问题
4. rewrite_plan 必须是分轮次的改稿策略"""

    async def _run_rewrite_if_needed(
        self, task_info: Dict, content: str, critic_result: Dict,
        bible_data: Dict, current_score: int, memory_context: str
    ) -> Dict:
        """如果需要，执行 Rewrite - 使用 must_fix_items 和 rewrite_plan"""
        steps = []
        total_tokens = 0
        total_cost = 0.0
        final_content = content
        final_score = current_score

        # 提取结构化 Critic 结果
        must_fix_items = critic_result.get("must_fix_items", [])
        rewrite_plan = critic_result.get("rewrite_plan", [])
        line_comments = critic_result.get("line_comments", [])

        rewrite_count = 0
        max_rewrites = min(2, len(rewrite_plan)) if rewrite_plan else 2

        while final_score < 80 and rewrite_count < max_rewrites:
            rewrite_count += 1
            logger.info(f"[Task {task_info['task_id']}] Rewrite #{rewrite_count} (score={final_score})")

            # 获取当前轮次的改稿重点
            current_round_plan = rewrite_plan[rewrite_count - 1] if rewrite_count <= len(rewrite_plan) else f"改稿轮次 {rewrite_count}"
            current_must_fix = must_fix_items[:3] if must_fix_items else []  # 每次处理前3个

            await event_bus.publish("agent.step.started", {
                "task_id": task_info["task_id"],
                "chapter_id": task_info["chapter_id"],
                "agent": "Rewrite",
                "step_index": 4,
                "rewrite_round": rewrite_count,
                "rewrite_plan": current_round_plan,
            })

            db = SessionLocal()
            try:
                # 构建有针对性的 Rewrite prompt
                prompt = self._build_rewrite_prompt(
                    task_info['chapter_title'],
                    final_content,
                    current_must_fix,
                    line_comments,
                    current_round_plan,
                    bible_data
                )

                response = await llm_manager.generate(
                    prompt=prompt,
                    role="rewrite",
                    temperature=0.7,
                    max_tokens=6000,
                    db=db,
                    request_type="worker_rewrite",
                    project_id=task_info["project_id"],
                )

                self._save_step(db, task_info, "Rewrite", prompt, response)

                steps.append({
                    "agent": "Rewrite",
                    "rewrite_round": rewrite_count,
                    "rewrite_plan": current_round_plan,
                    "tokens": response.get("total_tokens", 0),
                    "cost": response.get("cost", 0.0),
                })
                total_tokens += response.get("total_tokens", 0)
                total_cost += response.get("cost", 0.0)

                new_content = response.get("content", final_content)

                # 重新审稿
                await event_bus.publish("agent.step.started", {
                    "task_id": task_info["task_id"],
                    "chapter_id": task_info["chapter_id"],
                    "agent": "Re-Critic",
                    "step_index": 4,
                    "rewrite_round": rewrite_count,
                })

                new_critic_result = await self._run_critic(task_info, new_content, bible_data)
                new_score = new_critic_result.get("score", final_score)

                steps.append({
                    "agent": "Re-Critic",
                    "rewrite_round": rewrite_count,
                    "new_score": new_score,
                    "tokens": new_critic_result.get("tokens", 0),
                    "cost": new_critic_result.get("cost", 0.0),
                })
                total_tokens += new_critic_result.get("tokens", 0)
                total_cost += new_critic_result.get("cost", 0.0)

                await event_bus.publish("agent.step.completed", {
                    "task_id": task_info["task_id"],
                    "chapter_id": task_info["chapter_id"],
                    "agent": "Re-Critic",
                    "step_index": 4,
                    "rewrite_round": rewrite_count,
                    "new_score": new_score,
                })

                # Darwin 决策
                if new_score > final_score:
                    logger.info(f"[Task {task_info['task_id']}] 新版本评分提升: {final_score} -> {new_score}")
                    final_content = new_content
                    final_score = new_score
                else:
                    logger.info(f"[Task {task_info['task_id']}] 新版本未改进，保留旧版本")
                    break

            except Exception as e:
                logger.error(f"Rewrite 失败: {e}")
                break
            finally:
                db.close()

        return {
            "success": True,
            "steps": steps,
            "tokens": total_tokens,
            "cost": total_cost,
            "final_content": final_content,
            "final_score": final_score,
        }

    def _build_rewrite_prompt(
        self, chapter_title: str, content: str,
        must_fix_items: list, line_comments: list, rewrite_plan: str, bible_data: Dict
    ) -> str:
        """构建有针对性的 Rewrite prompt"""

        # 构建 must_fix 部分
        must_fix_section = ""
        if must_fix_items:
            must_fix_section = "## 必须修复的问题（按优先级）\n" + "\n".join([f"{i+1}. {item}" for i, item in enumerate(must_fix_items)]) + "\n"

        # 构建 line_comments 部分
        line_comments_section = ""
        if line_comments:
            line_comments_section = "## 行级批注\n"
            for comment in line_comments[:5]:  # 最多5条
                if isinstance(comment, dict):
                    line_comments_section += f"\n原文: \"{comment.get('quote', '')}\"\n"
                    line_comments_section += f"问题: {comment.get('issue_type', '')} - {comment.get('comment', '')}\n"
                    if comment.get('rewrite_suggestion'):
                        line_comments_section += f"改写建议: {comment.get('rewrite_suggestion')}\n"

        return f"""请根据审稿意见改写文章。

章节标题: {chapter_title}

## 本轮改稿重点
{rewrite_plan}

{must_fix_section}
{line_comments_section}

## 原文
{content[:6000]}

## 改写要求
1. 优先修复上述"必须修复的问题"
2. 针对行级批注中的具体问题进行修改
3. 保持原有情节主线不变
4. 提高可读性和流畅度
5. 输出完整的改写后章节内容

请输出改写后的完整章节内容："""
                )

                self._save_step(db, task_info, "Rewrite", prompt, response)

                steps.append({
                    "agent": "Rewrite",
                    "tokens": response.get("total_tokens", 0),
                    "cost": response.get("cost", 0.0),
                })
                total_tokens += response.get("total_tokens", 0)
                total_cost += response.get("cost", 0.0)

                new_content = response.get("content", final_content)

                # 重新审稿
                await event_bus.publish("agent.step.started", {
                    "task_id": task_info["task_id"],
                    "chapter_id": task_info["chapter_id"],
                    "agent": "Re-Critic",
                    "step_index": 4,
                    "rewrite_round": rewrite_count,
                })

                critic_prompt = f"""请对改写后的章节进行审稿评分：

章节标题: {task_info['chapter_title']}

章节内容:
{new_content[:5000]}

请输出：1.综合评分 2.各维度得分 3.改进建议"""

                critic_response = await llm_manager.generate(
                    prompt=critic_prompt,
                    role="critic",
                    temperature=0.3,
                    db=db,
                    request_type="worker_critic",
                    project_id=task_info["project_id"],
                )

                new_score = self._extract_score(critic_response.get("content", ""))

                self._save_step(db, task_info, "Re-Critic", critic_prompt, critic_response, score=new_score)

                steps.append({
                    "agent": "Re-Critic",
                    "tokens": critic_response.get("total_tokens", 0),
                    "cost": critic_response.get("cost", 0.0),
                })
                total_tokens += critic_response.get("total_tokens", 0)
                total_cost += critic_response.get("cost", 0.0)

                await event_bus.publish("agent.step.completed", {
                    "task_id": task_info["task_id"],
                    "chapter_id": task_info["chapter_id"],
                    "agent": "Re-Critic",
                    "step_index": 4,
                    "rewrite_round": rewrite_count,
                    "new_score": new_score,
                })

                # Darwin 决策
                if new_score > final_score:
                    logger.info(f"[Task {task_info['task_id']}] 新版本评分提升: {final_score} -> {new_score}")
                    final_content = new_content
                    final_score = new_score
                else:
                    logger.info(f"[Task {task_info['task_id']}] 新版本未改进，保留旧版本")
                    break

            except Exception as e:
                logger.error(f"Rewrite 失败: {e}")
                break
            finally:
                db.close()

        return {
            "success": True,
            "steps": steps,
            "tokens": total_tokens,
            "cost": total_cost,
            "final_content": final_content,
            "final_score": final_score,
        }

    async def _run_continuity(
        self, task_info: Dict, content: str, bible_data: Dict, memory_context: str
    ) -> Dict:
        """执行 Continuity Agent - TASK-C3: 增加上一章衔接检查"""
        db = SessionLocal()
        try:
            # TASK-C3: 获取上一章结尾用于检查
            memory_service = MemoryService(db)
            previous_ending = memory_service.get_previous_chapter_ending(
                project_id=task_info["project_id"],
                current_chapter_index=task_info["chapter_index"],
                ending_length=300
            )

            template_service = PromptTemplateService(db)
            variables = {
                "chapter_title": task_info["chapter_title"],
                "chapter_index": task_info["chapter_index"],
                "content_preview": content[:3000],
                "characters": json.dumps(bible_data.get("characters", []), ensure_ascii=False),
                "foreshadowing": json.dumps(bible_data.get("foreshadowing", []), ensure_ascii=False),
                "memory_context": memory_context,
                "previous_ending": previous_ending.get("ending_excerpt", ""),
                "open_hooks": json.dumps(previous_ending.get("open_hooks", []), ensure_ascii=False),
            }

            fallback = f"""请检查以下章节的连续性：

章节标题: {task_info['chapter_title']}
章节序号: {task_info['chapter_index']}

章节内容:
{content[:3000]}

人物设定:
{json.dumps(bible_data.get('characters', []), ensure_ascii=False)}

伏笔列表:
{json.dumps(bible_data.get('foreshadowing', []), ensure_ascii=False)}

{f"上一章结尾:\n{previous_ending.get('ending_excerpt', '')}\n\n待解悬念: {previous_ending.get('open_hooks', [])}\n" if task_info['chapter_index'] > 1 else ""}

记忆上下文:
{memory_context}

请检查：
1. 人设一致性
2. 设定一致性
3. 时间线连续性
4. 伏笔回收
5. 与前文连续性
{f"6. 本章开头是否承接上一章结尾（重要）" if task_info['chapter_index'] > 1 else ""}
7. 潜在问题

{f"特别检查：本章开头是否自然承接上一章结尾？是否回应了待解悬念？" if task_info['chapter_index'] > 1 else ""}

如检查通过，请说明"通过"。"""

            prompt = template_service.render(
                role="continuity",
                variables=variables,
                fallback=fallback,
                project_id=task_info["project_id"],
            )

            response = await llm_manager.generate(
                prompt=prompt,
                role="continuity",
                temperature=0.3,
                db=db,
                request_type="worker_continuity",
                project_id=task_info["project_id"],
            )

            content_text = response.get("content", "")
            score = 90 if "通过" in content_text else 75

            # TASK-C3: 如果本章不是第一章，检查是否承接上一章
            if task_info["chapter_index"] > 1:
                if "承接" in content_text and ("不" in content_text or "未" in content_text or "问题" in content_text):
                    score = max(60, score - 15)  # 承接有问题扣分

            self._save_step(db, task_info, "Continuity", prompt, response, score=score)

            return {
                "success": True,
                "agent": "Continuity",
                "score": score,
                "report": content_text,
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }

        except Exception as e:
            logger.error(f"Continuity 失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    async def _run_learning(self, task_info: Dict, steps_data: list) -> Dict:
        """执行 Learning Agent"""
        db = SessionLocal()
        try:
            prompt = f"""请总结本章写作过程的经验：

章节标题: {task_info['chapter_title']}

写作流程回顾:
{json.dumps([{"agent": s.get("agent"), "score": s.get("score")} for s in steps_data], ensure_ascii=False)}

请提取：1.本章成功经验 2.改进空间 3.可复用的技巧"""

            started_at = utc_now()
            response = await llm_manager.generate(
                prompt=prompt,
                role="learning",
                temperature=0.5,
                db=db,
                request_type="worker_learning",
                project_id=task_info["project_id"],
            )

            self._save_step(db, task_info, "Learning", prompt, response)

            return {
                "success": True,
                "agent": "Learning",
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }

        except Exception as e:
            logger.error(f"Learning 失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def _parse_critic_structured_output(self, content: str) -> Dict:
        """解析 Critic 的结构化 JSON 输出"""
        import re

        # 去除 Markdown 代码块标记
        content = re.sub(r'^```json\s*', '', content.strip())
        content = re.sub(r'```\s*$', '', content.strip())

        # 尝试直接解析
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 部分
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                data = json.loads(match.group())
                return data
            except json.JSONDecodeError:
                pass

        # 解析失败，返回空结构
        return {
            "overall_score": 0,
            "dimension_scores": {},
            "anchored_comments": {},
            "line_comments": [],
            "must_fix_items": [],
            "nice_to_have_items": [],
            "rewrite_plan": [],
        }

    def _validate_critic_output(self, result: Dict) -> bool:
        """验证 Critic 输出是否有效"""
        # 检查必需字段
        required_fields = ["overall_score", "dimension_scores", "must_fix_items", "rewrite_plan"]
        for field in required_fields:
            if field not in result:
                logger.warning(f"Critic 输出缺少字段: {field}")
                return False

        # 检查 dimension_scores 是否包含九维
        dimensions = [
            "plot_progress", "pacing", "character_consistency",
            "dialogue_distinction", "payoff_delivery", "ending_hook",
            "style_stability", "continuity", "commercial_readability"
        ]
        dim_scores = result.get("dimension_scores", {})
        for dim in dimensions:
            if dim not in dim_scores:
                logger.warning(f"Critic 输出缺少维度评分: {dim}")
                # 不强制要求所有维度，但记录警告

        # 检查 line_comments 是否包含 quote
        line_comments = result.get("line_comments", [])
        for comment in line_comments:
            if isinstance(comment, dict) and "quote" not in comment:
                logger.warning("line_comment 缺少 quote 字段")

        return True

    # ===== 辅助方法 =====

    async def _get_bible_data(self, project_id: int) -> Dict:
        """获取 Bible 数据（独立 session）"""
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project or not project.bible:
                return {}

            bible = project.bible
            return {
                "world_setting": bible.world_setting or "",
                "world_rules": bible.world_rules or [],
                "timeline": bible.timeline or [],
                "characters": bible.characters or [],
                "character_relationships": bible.character_relationships or [],
                "main_plot": bible.main_plot or "",
                "sub_plots": bible.sub_plots or [],
                "foreshadowing": bible.foreshadowing or [],
                "style_boundaries": bible.style_boundaries or [],
                "tone_guidelines": bible.tone_guidelines or "",
                "forbidden_items": bible.forbidden_items or [],
                "volume_outline": bible.volume_outline or [],
                "chapter_outline": bible.chapter_outline or [],
            }
        finally:
            db.close()

    async def _get_memory_context(self, project_id: int, chapter_index: int) -> str:
        """获取记忆上下文（独立 session）- TASK-C3: 增加上一章结尾"""
        db = SessionLocal()
        try:
            memory_service = MemoryService(db)

            # 1. 获取基础上下文
            context_data = memory_service.assemble_context_for_chapter(
                project_id=project_id,
                chapter_index=chapter_index
            )

            # 2. TASK-C3: 获取上一章结尾
            previous_ending = memory_service.get_previous_chapter_ending(
                project_id=project_id,
                current_chapter_index=chapter_index,
                ending_length=500
            )

            # 3. 格式化上下文
            base_context = memory_service.format_context_for_prompt(context_data)

            # 4. 添加上一章结尾信息
            if chapter_index > 1 and previous_ending.get("ending_excerpt"):
                ending_section = f"""
## 上一章结尾（必须自然承接）

上一章最后内容：
{previous_ending['ending_excerpt']}

待解悬念：
{chr(10).join(['- ' + hook for hook in previous_ending.get('open_hooks', [])]) if previous_ending.get('open_hooks') else '（无明确悬念）'}

承接要求：
- 本章开头必须自然承接上一章结尾，不允许像新故事一样重新开场
- 必须回应或延续上一章留下的悬念
- 人物情绪和状态要与上一章结尾保持一致

"""
                base_context = ending_section + base_context

            return base_context

        except Exception as e:
            logger.warning(f"记忆上下文获取失败: {e}")
            return "（记忆系统暂不可用）"
        finally:
            db.close()

    async def _save_draft_version(self, task_info: Dict, draft_content: str, chapter_plan: Dict, word_count: int = 0):
        """保存草稿版本（独立 session）"""
        db = SessionLocal()
        try:
            version = db.query(ChapterVersion).filter(
                ChapterVersion.chapter_id == task_info["chapter_id"],
                ChapterVersion.version_number == 1
            ).first()

            if not version:
                version = ChapterVersion(
                    chapter_id=task_info["chapter_id"],
                    version_number=1,
                )
                db.add(version)

            version.draft_content = draft_content
            version.plan_content = json.dumps(chapter_plan, ensure_ascii=False)
            # 保存字数信息
            if word_count > 0:
                # 可以在 metadata 或其他字段中保存，这里使用现有字段
                pass
            db.commit()
        finally:
            db.close()

    async def _save_critic_result(self, task_info: Dict, score: int, critique: str):
        """保存审稿结果（独立 session）"""
        db = SessionLocal()
        try:
            version = db.query(ChapterVersion).filter(
                ChapterVersion.chapter_id == task_info["chapter_id"],
                ChapterVersion.version_number == 1
            ).first()

            if version:
                version.total_score = score
                version.critic_report = critique
                db.commit()
        finally:
            db.close()

    def _save_pipeline_result(self, db, task_info: Dict, result: Dict):
        """保存流水线最终结果"""
        gen_task = db.query(GenerationTask).filter(
            GenerationTask.id == task_info["task_id"]
        ).first()

        chapter = db.query(Chapter).filter(
            Chapter.id == task_info["chapter_id"]
        ).first()

        if result["success"]:
            gen_task.status = TaskStatus.COMPLETED
            gen_task.finished_at = utc_now()
            gen_task.token_used = result.get("tokens_used", 0)
            gen_task.actual_cost = result.get("cost", 0.0)

            chapter.status = ChapterStatus.COMPLETED
            chapter.final_content = result.get("final_content", "")
            # TASK-C2: 保存实际字数
            chapter.final_word_count = result.get("word_count", len(result.get("final_content", "")))
            chapter.total_score = result.get("final_score", 0)
            chapter.completed_at = utc_now()

            # 更新版本
            version = db.query(ChapterVersion).filter(
                ChapterVersion.chapter_id == chapter.id,
                ChapterVersion.version_number == 1
            ).first()

            if version:
                version.is_accepted = 1
                version.final_content = result.get("final_content", "")
                version.acceptance_reason = f"最终评分: {result.get('final_score', 0)}"

            # STATS-001: 记录成功统计到 DailyUsageStats
            DailyUsageStatsService(db).record_usage(
                project_id=task_info["project_id"],
                provider="pipeline",
                model_name="mixed",
                input_tokens=0,
                output_tokens=0,
                cost=result.get("cost", 0.0),
                chapter_count=1,
                task_count=1,
                word_count=result.get("word_count", 0),
                success=True,
            )
        else:
            gen_task.status = TaskStatus.FAILED
            gen_task.error_message = result.get("error", "未知错误")
            chapter.status = ChapterStatus.FAILED

            # STATS-001: 记录失败统计到 DailyUsageStats
            DailyUsageStatsService(db).record_usage(
                project_id=task_info["project_id"],
                provider="pipeline",
                model_name="mixed",
                task_count=1,
                success=False,
            )

        db.commit()

    def _save_step(
        self, db, task_info: Dict, agent_name: str,
        prompt: str, response: Dict, score: int = None, score_breakdown: Dict = None
    ):
        """保存生成步骤"""
        # 计算步骤序号
        last_step = db.query(GenerationStep).filter(
            GenerationStep.task_id == task_info["task_id"]
        ).order_by(GenerationStep.step_index.desc()).first()

        step_index = (last_step.step_index + 1) if last_step else 1

        step = GenerationStep(
            task_id=task_info["task_id"],
            chapter_id=task_info["chapter_id"],
            step_index=step_index,
            agent_name=agent_name,
            input_prompt=prompt[:5000] if prompt else None,
            raw_output=response.get("content", ""),
            parsed_output=response.get("content", ""),
            score=score,
            score_breakdown=score_breakdown,
            model_name=response.get("model", "unknown"),
            provider_name=response.get("provider", "unknown"),
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
            duration_seconds=response.get("duration_seconds", 0),
            started_at=response.get("started_at", utc_now()),
            finished_at=response.get("finished_at", utc_now()),
        )

        db.add(step)
        db.commit()

    # ===== 工具方法 =====

    def _get_project_techniques(self, db, project_id: int) -> list:
        """获取项目技巧卡"""
        from app.models.technique import TechniqueCard

        techniques = db.query(TechniqueCard).filter(
            TechniqueCard.is_active == 1
        ).order_by(
            TechniqueCard.confidence_score.desc()
        ).limit(10).all()

        return [
            {
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "usage_instruction": t.usage_instruction or "",
                "prompt_instruction": t.prompt_instruction or "",
                "anti_pattern": t.anti_pattern or "",
                "prevention_rule": t.prevention_rule or "",
            }
            for t in techniques
        ]

    def _get_project_playbook(self, db, project_id: int) -> dict:
        """获取项目写作手册"""
        from app.models.technique import ProjectPlaybook

        playbook = db.query(ProjectPlaybook).filter(
            ProjectPlaybook.project_id == project_id
        ).first()

        if not playbook:
            return {"rules": []}

        return {
            "rules": playbook.rules or [],
            "style_boundaries": playbook.style_boundaries or "",
            "tone_guidelines": playbook.tone_guidelines or "",
        }

    def _format_techniques_for_prompt(self, techniques: list) -> str:
        """格式化技巧卡为 Prompt"""
        if not techniques:
            return "无特定技巧要求。"

        sections = ["## 必须使用的写作技巧"]
        for i, tech in enumerate(techniques[:5], 1):
            sections.append(f"\n### 技巧 {i}: {tech['title']}")
            if tech['usage_instruction']:
                sections.append(f"**使用指令**: {tech['usage_instruction']}")
            if tech['prompt_instruction']:
                sections.append(f"**Prompt**: {tech['prompt_instruction']}")

        return "\n".join(sections)

    def _build_planner_fallback(self, variables: Dict) -> str:
        """构建 Planner 的 fallback prompt"""
        style_section = variables.get('style_rules', '')
        return f"""请为以下章节进行详细规划：

章节标题: {variables['chapter_title']}
章节序号: {variables['chapter_index']}

世界观设定:
{variables['world_setting']}

人物设定:
{variables['characters']}

主线剧情:
{variables['main_plot']}

章纲:
{variables['chapter_outline']}

记忆上下文:
{variables['memory_context']}

{variables['tech_instructions']}

写作手册规则:
{variables['playbook_rules']}

{style_section}

请输出：1.本章目标 2.冲突设计 3.人物安排 4.章节钩子 5.情绪节奏 6.关键剧情点 7.使用技巧 8.避免错误 9.回顾伏笔"""

    def _build_draft_fallback(self, variables: Dict) -> str:
        """构建 Draft 的 fallback prompt - 合并 TASK-C3 上一章承接 和 TASK-B3 风格档案"""
        target_words = variables.get('target_words', 2500)
        min_words = variables.get('min_words', int(target_words * 0.85))
        max_words = variables.get('max_words', int(target_words * 1.1))
        chapter_index = variables.get('chapter_index', 1)
        style_section = variables.get('style_rules', '')

        # TASK-C3: 上一章承接部分
        previous_chapter_section = ""
        if chapter_index > 1:
            previous_chapter_section = """
## 上一章结尾（必须自然承接）
上一章留下的待解悬念和结尾状态必须在本章开头得到回应。

承接要求：
- 本章开头必须自然承接上一章结尾，不允许像新故事一样重新开场
- 必须回应或延续上一章留下的悬念
- 人物情绪和状态要与上一章结尾保持一致

"""

        return f"""请根据以下规划起草章节内容。

## 硬性长度要求（必须遵守）
- 目标字数：{target_words} 中文字
- 合格范围：{min_words} - {max_words} 中文字
- 如果内容不足，不允许用总结式结尾凑数，必须扩展冲突、动作、对话或心理变化
- 禁止使用"总之"、"综上所述"等总结性词语草草收尾

{previous_chapter_section}
章节标题: {variables['chapter_title']}
章节序号: {chapter_index}

章节规划:
{variables['chapter_plan']}

记忆上下文:
{variables['memory_context']}

世界观设定:
{variables['world_setting']}

人物设定:
{variables['characters']}

{variables['tech_instructions']}

写作手册规则:
{variables['playbook_rules']}

{style_section}

写作要求：使用中文，注意节奏，对话自然，场景生动，遵守技巧卡指令。必须达到字数要求。{" 必须承接上一章结尾。" if chapter_index > 1 else ""}

请直接输出章节正文内容："""

    def _extract_score(self, text: str) -> int:
        """从文本中提取评分"""
        import re
        patterns = [
            r'综合评分[:：]\s*(\d+)',
            r'总分[:：]\s*(\d+)',
            r'(\d+)\s*分',
            r'(\d+)/100',
            r'评分[:：]\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                score = int(match.group(1))
                return min(100, max(0, score))
        return 75

    def _extract_score_breakdown(self, text: str) -> dict:
        """从文本中提取各维度评分"""
        import re
        breakdown = {}
        dimensions = [
            ("plot_progress", r'剧情推进[:：]\s*(\d+)'),
            ("character_consistency", r'人物一致性[:：]\s*(\d+)'),
            ("pacing", r'节奏控制[:：]\s*(\d+)'),
            ("hook", r'章节钩子[:：]\s*(\d+)'),
            ("emotional_reward", r'情绪回报[:：]\s*(\d+)'),
            ("style_consistency", r'文风稳定[:：]\s*(\d+)'),
            ("continuity", r'连续性[:：]\s*(\d+)'),
            ("clarity", r'信息清晰度[:：]\s*(\d+)'),
            ("readability", r'商业可读性[:：]\s*(\d+)'),
        ]
        for key, pattern in dimensions:
            match = re.search(pattern, text)
            if match:
                breakdown[key] = int(match.group(1))
        return breakdown

    # ===== 风格档案方法 (B3: 结构指纹/爽点曲线) =====

    async def _get_style_profile_context(self, project_id: int, chapter_index: int) -> Dict[str, Any]:
        """获取风格档案上下文（独立 session）"""
        db = SessionLocal()
        try:
            analysis_service = BookAnalysisService(db)
            context = analysis_service.get_style_injection_context(project_id)

            # 添加当前章节的爽点位置预测
            if context.get("has_style_profile"):
                cadence = context.get("satisfaction_curve", {}).get("cadence", 5.0)
                is_peak_chapter = self._is_satisfaction_peak_chapter(chapter_index, cadence)
                context["is_peak_chapter"] = is_peak_chapter
                context["chapters_to_peak"] = self._chapters_to_next_peak(chapter_index, cadence)

            return context
        except Exception as e:
            logger.warning(f"风格档案获取失败: {e}")
            return {}
        finally:
            db.close()

    def _is_satisfaction_peak_chapter(self, chapter_index: int, cadence: float) -> bool:
        """判断当前章节是否为爽点章节"""
        if cadence <= 0:
            return False
        # 简单的模运算判断
        return chapter_index % int(cadence) == 0

    def _chapters_to_next_peak(self, chapter_index: int, cadence: float) -> int:
        """计算距离下一个爽点的章节数"""
        if cadence <= 0:
            return 5
        cadence_int = int(cadence)
        next_peak = ((chapter_index // cadence_int) + 1) * cadence_int
        return next_peak - chapter_index

    def _extract_style_sections(self, style_context: Dict) -> Dict[str, Any]:
        """提取风格档案的各个部分，供格式化方法使用"""
        if not style_context or not style_context.get("has_style_profile"):
            return {}

        return {
            "target_words": style_context.get("target_words", {}),
            "hook_rules": style_context.get("hook_rules", {}),
            "satisfaction_curve": style_context.get("satisfaction_curve", {}),
            "pacing_template": style_context.get("pacing_template", {}),
            "emotion_guidelines": style_context.get("emotion_guidelines", {}),
            "cliffhanger_rules": style_context.get("cliffhanger_rules", {}),
            "is_peak_chapter": style_context.get("is_peak_chapter", False),
            "chapters_to_peak": style_context.get("chapters_to_peak", 5),
        }

    def _format_style_profile_for_planner(self, style_context: Dict) -> str:
        """格式化风格档案为 Planner Prompt"""
        sections_data = self._extract_style_sections(style_context)
        if not sections_data:
            return ""

        sections = ["\n## 风格档案约束"]

        # 字数目标
        target_words = sections_data["target_words"]
        if target_words:
            sections.append(f"\n**字数控制**: 目标{target_words.get('optimal', 3000)}字，"
                           f"范围{target_words.get('min', 2500)}-{target_words.get('max', 3500)}字")

        # Hook规则
        hook_rules = sections_data["hook_rules"]
        if hook_rules.get("opening_hook"):
            sections.append(f"\n**开篇要求**: 必须使用{hook_rules.get('hook_intensity', 'moderate')}强度的钩子")
            hook_types = hook_rules.get("hook_types", ["冲突", "悬念", "反常"])
            sections.append(f"**钩子类型**: {', '.join(hook_types)}")

        # 爽点曲线
        satisfaction = sections_data["satisfaction_curve"]
        if satisfaction:
            if sections_data["is_peak_chapter"]:
                sections.append(f"\n**⚠️ 本章为爽点章节**: 必须安排高强度情绪回报")
                sections.append(f"**爽点强度**: {satisfaction.get('peak_intensity', 8.0)}/10")
            else:
                sections.append(f"\n**爽点曲线**: 距离下一个爽点还有{sections_data['chapters_to_peak']}章")
                sections.append(f"**当前阶段**: 铺垫期，注意情绪积累")

        # 节奏模板
        pacing = sections_data["pacing_template"]
        if pacing:
            sections.append(f"\n**节奏要求**: {pacing.get('opening_pace', 'medium')}开局，"
                           f"高潮密度{pacing.get('climax_density', 'medium')}")

        # 情绪指导
        emotion = sections_data["emotion_guidelines"]
        if emotion:
            variation = emotion.get("variation_range", [3.0, 8.0])
            sections.append(f"\n**情绪基线**: {emotion.get('baseline', 5.0)}/10，"
                           f"波动范围{variation[0]}-{variation[1]}")
            sections.append(f"**情绪节奏**: {emotion.get('rhythm', 'wave')}")

        return "\n".join(sections)

    def _format_style_profile_for_draft(self, style_context: Dict) -> str:
        """格式化风格档案为 Draft Prompt"""
        sections_data = self._extract_style_sections(style_context)
        if not sections_data:
            return ""

        sections = ["\n## 风格档案写作指导"]

        # 字数控制
        target_words = sections_data["target_words"]
        if target_words:
            sections.append(f"\n**字数目标**: {target_words.get('optimal', 3000)}字")
            sections.append(f"**字数范围**: {target_words.get('min', 2500)}-{target_words.get('max', 3500)}字")

        # Hook要求
        hook_rules = sections_data["hook_rules"]
        if hook_rules.get("opening_hook"):
            sections.append(f"\n**开篇钩子**: 必须在开头200字内建立{hook_rules.get('hook_intensity', 'moderate')}强度钩子")

        # 爽点写作
        if sections_data["is_peak_chapter"]:
            sections.append(f"\n**⚠️ 爽点章节写作要求**:")
            sections.append("- 本章必须达到情绪高潮")
            sections.append("- 冲突必须得到阶段性解决")
            sections.append("- 主角必须获得实质性回报")
            sections.append("- 结尾可留适度悬念")
        else:
            chapters_to_peak = sections_data["chapters_to_peak"]
            sections.append(f"\n**铺垫期写作要求**:")
            sections.append(f"- 距离爽点还有{chapters_to_peak}章，注意情绪积累")
            sections.append("- 埋下爽点所需的伏笔")
            sections.append("- 适度压制，为高潮蓄力")

        # 断章规则
        cliffhanger = sections_data["cliffhanger_rules"]
        if cliffhanger:
            freq = cliffhanger.get("frequency", 0.3)
            if freq > 0.5:
                sections.append(f"\n**断章要求**: 本章建议以悬念/冲突/转折结尾")

        # 节奏执行
        pacing = sections_data["pacing_template"]
        if pacing:
            sections.append(f"\n**节奏执行**: {pacing.get('opening_pace', 'medium')}开局，"
                           f"逐步加速，{pacing.get('resolution_brevity', 'concise')}收尾")

        return "\n".join(sections)
