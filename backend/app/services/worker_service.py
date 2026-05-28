"""
Worker Service - 24小时自动写作后台任务调度器 (修复版)
基于 GenerationTask 的调度，支持 Darwin 进化
修复: bible ORM 访问, ChapterVersion 使用, 评分保存
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.chapter import Chapter, ChapterStatus, ChapterVersion
from app.models.project import Project, NovelBible
from app.models.task import GenerationTask, GenerationStep, TaskStatus, TaskPriority, TaskType
from app.services.openai_llm_service import llm_manager
from app.services.evolution_service import EvolutionService

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Worker 状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 暂停
    STOPPED = "stopped"     # 停止


class WritingWorker:
    """
    24小时自动写作 Worker

    功能：
    - 扫描 GenerationTask 队列
    - 执行完整写作流水线 (Planner → Draft → Critic → Rewrite → Continuity)
    - Darwin 进化：评估 → 改进 → 测试 → keep/rollback
    - 自动触发下一任务
    """

    def __init__(self):
        self.status = WorkerStatus.STOPPED
        self.current_task: Optional[dict] = None
        self.daily_stats = {
            "words_written": 0,
            "chapters_completed": 0,
            "tokens_used": 0,
            "cost": 0.0,
            "start_time": None,
        }
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.evolution_service = EvolutionService()

    async def start(self):
        """启动 Worker"""
        if self.status == WorkerStatus.RUNNING:
            logger.info("Worker 已在运行中")
            return

        self.status = WorkerStatus.RUNNING
        self._stop_event.clear()
        self.daily_stats["start_time"] = datetime.now()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Worker 已启动")

    async def stop(self):
        """停止 Worker"""
        self.status = WorkerStatus.STOPPED
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.current_task = None
        logger.info("Worker 已停止")

    async def pause(self):
        """暂停 Worker"""
        if self.status == WorkerStatus.RUNNING:
            self.status = WorkerStatus.PAUSED
            logger.info("Worker 已暂停")

    async def resume(self):
        """恢复 Worker"""
        if self.status == WorkerStatus.PAUSED:
            self.status = WorkerStatus.RUNNING
            logger.info("Worker 已恢复")

    async def _run_loop(self):
        """主循环 - 扫描 GenerationTask"""
        while not self._stop_event.is_set():
            try:
                if self.status == WorkerStatus.RUNNING:
                    await self._process_next_task()

                # 等待一段时间再检查
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=5.0  # 每5秒检查一次
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker 循环出错: {e}")
                await asyncio.sleep(10)

    async def _process_next_task(self):
        """处理下一个 GenerationTask"""
        db = SessionLocal()
        try:
            # 初始化 LLM
            llm_manager.init_from_db(db)

            # 查找待处理的任务 - 按优先级排序
            gen_task = db.query(GenerationTask).filter(
                GenerationTask.status == TaskStatus.PENDING
            ).order_by(
                GenerationTask.priority.desc(),
                GenerationTask.created_at.asc()
            ).first()

            if not gen_task:
                return

            # 获取关联的章节和项目
            chapter = db.query(Chapter).filter(
                Chapter.id == gen_task.chapter_id
            ).first()

            project = db.query(Project).filter(
                Project.id == gen_task.project_id
            ).first()

            if not chapter or not project:
                logger.error(f"任务 {gen_task.id} 关联的章节或项目不存在")
                gen_task.status = TaskStatus.FAILED
                gen_task.error_message = "关联的章节或项目不存在"
                db.commit()
                return

            # 检查预算限制
            if not self._check_budget(project):
                logger.info("已达到每日预算限制，暂停写作")
                await self.pause()
                return

            # 设置当前任务
            self.current_task = {
                "task_id": gen_task.id,
                "chapter_id": chapter.id,
                "project_id": project.id,
                "chapter_title": chapter.title,
                "task_type": gen_task.task_type,
                "start_time": datetime.now().isoformat(),
            }

            logger.info(f"开始处理任务 {gen_task.id}: {chapter.title}")

            # 执行任务
            result = await self._execute_task(db, gen_task, chapter, project)

            # 更新统计
            if result["success"]:
                self.daily_stats["chapters_completed"] += 1
                self.daily_stats["words_written"] += result.get("word_count", 0)
                self.daily_stats["tokens_used"] += result.get("tokens_used", 0)
                self.daily_stats["cost"] += result.get("cost", 0.0)

            self.current_task = None

        finally:
            db.close()

    async def _execute_task(
        self,
        db: Session,
        gen_task: GenerationTask,
        chapter: Chapter,
        project: Project
    ) -> dict:
        """执行写作任务 - 完整流水线"""
        try:
            # 更新任务状态
            gen_task.status = TaskStatus.RUNNING
            gen_task.started_at = datetime.utcnow()
            chapter.status = ChapterStatus.DRAFTING
            db.commit()

            # 执行完整流水线
            result = await self._run_writing_pipeline(db, gen_task, chapter, project)

            if result["success"]:
                gen_task.status = TaskStatus.COMPLETED
                gen_task.finished_at = datetime.utcnow()
                chapter.status = ChapterStatus.COMPLETED
                # 最终稿保存到 Chapter.final_content
                chapter.final_content = result.get("final_content", "")
                chapter.final_word_count = len(result.get("final_content", ""))
                chapter.total_score = result.get("final_score", 0)
                chapter.completed_at = datetime.utcnow()
            else:
                gen_task.status = TaskStatus.FAILED
                gen_task.error_message = result.get("error", "未知错误")
                chapter.status = ChapterStatus.FAILED
                gen_task.retry_count += 1

            # 更新任务统计
            gen_task.completed_steps = result.get("completed_steps", 0)
            gen_task.total_steps = result.get("total_steps", 0)
            gen_task.token_used = result.get("tokens_used", 0)
            gen_task.actual_cost = result.get("cost", 0.0)

            db.commit()
            return result

        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            gen_task.status = TaskStatus.FAILED
            gen_task.error_message = str(e)
            chapter.status = ChapterStatus.FAILED
            gen_task.retry_count += 1
            db.commit()
            return {"success": False, "error": str(e)}

    async def _run_writing_pipeline(
        self,
        db: Session,
        gen_task: GenerationTask,
        chapter: Chapter,
        project: Project
    ) -> dict:
        """
        执行写作流水线
        Planner → Draft → Critic → [Rewrite → Critic] → Continuity → Learning
        每个 Draft/Rewrite 生成 ChapterVersion
        """
        steps_data = []
        total_tokens = 0
        total_cost = 0.0

        # 获取 Bible - 正确访问 ORM 对象
        bible = project.bible
        bible_data = self._bible_to_dict(bible) if bible else {}

        # 创建初始版本
        current_version = self._get_or_create_version(db, chapter, 1)

        try:
            # ===== Step 1: Planner =====
            logger.info(f"[Task {gen_task.id}] Step 1: Planner")
            planner_result = await self._run_planner(db, gen_task, chapter, bible_data)
            steps_data.append(planner_result)
            total_tokens += planner_result.get("tokens", 0)
            total_cost += planner_result.get("cost", 0.0)

            if not planner_result.get("success"):
                return {"success": False, "error": "Planner 失败", "step": "planner"}

            chapter_plan = planner_result.get("plan", {})
            current_version.plan_content = json.dumps(chapter_plan, ensure_ascii=False)
            db.commit()

            # ===== Step 2: Draft =====
            logger.info(f"[Task {gen_task.id}] Step 2: Draft")
            draft_result = await self._run_draft(db, gen_task, chapter, bible_data, chapter_plan)
            steps_data.append(draft_result)
            total_tokens += draft_result.get("tokens", 0)
            total_cost += draft_result.get("cost", 0.0)

            if not draft_result.get("success"):
                return {"success": False, "error": "Draft 失败", "step": "draft"}

            draft_content = draft_result.get("content", "")
            # 保存草稿到 ChapterVersion
            current_version.draft_content = draft_content
            db.commit()

            # ===== Step 3: Critic =====
            logger.info(f"[Task {gen_task.id}] Step 3: Critic")
            critic_result = await self._run_critic(db, gen_task, chapter, draft_content, bible_data)
            steps_data.append(critic_result)
            total_tokens += critic_result.get("tokens", 0)
            total_cost += critic_result.get("cost", 0.0)

            if not critic_result.get("success"):
                return {"success": False, "error": "Critic 失败", "step": "critic"}

            score = critic_result.get("score", 0)
            score_breakdown = critic_result.get("score_breakdown", {})
            critique = critic_result.get("critique", "")

            # 保存评分到版本
            current_version.total_score = score
            current_version.critic_report = critique
            db.commit()

            # ===== Step 4: Rewrite (如果分数不够高) =====
            rewrite_count = 0
            while score < 80 and rewrite_count < 2:  # 最多重写2次
                rewrite_count += 1
                logger.info(f"[Task {gen_task.id}] Step 4: Rewrite #{rewrite_count} (score={score})")

                # 创建新版本
                new_version = self._get_or_create_version(db, chapter, current_version.version_number + 1)
                new_version.plan_content = current_version.plan_content

                rewrite_result = await self._run_rewrite(
                    db, gen_task, chapter, draft_content, critique, bible_data
                )
                steps_data.append(rewrite_result)
                total_tokens += rewrite_result.get("tokens", 0)
                total_cost += rewrite_result.get("cost", 0.0)

                if rewrite_result.get("success"):
                    new_draft = rewrite_result.get("content", draft_content)
                    new_version.draft_content = new_draft
                    db.commit()

                    # Rewrite 后再次审稿
                    logger.info(f"[Task {gen_task.id}] Step 4b: Re-Critic after rewrite")
                    critic_result2 = await self._run_critic(db, gen_task, chapter, new_draft, bible_data)
                    steps_data.append(critic_result2)
                    total_tokens += critic_result2.get("tokens", 0)
                    total_cost += critic_result2.get("cost", 0.0)

                    new_score = critic_result2.get("score", score)
                    new_critique = critic_result2.get("critique", critique)

                    # 保存新版本的评分
                    new_version.total_score = new_score
                    new_version.critic_report = new_critique
                    db.commit()

                    # Darwin 决策: 比较新旧版本
                    if new_score > score:
                        # 新版本更好，接受
                        logger.info(f"[Task {gen_task.id}] 新版本评分提升: {score} -> {new_score}")
                        draft_content = new_draft
                        score = new_score
                        critique = new_critique
                        score_breakdown = critic_result2.get("score_breakdown", score_breakdown)
                        current_version = new_version
                    else:
                        # 新版本没有改进，回滚
                        logger.info(f"[Task {gen_task.id}] 新版本未改进 ({new_score} vs {score})，保留旧版本")
                        new_version.is_accepted = 0
                        db.commit()
                else:
                    break

            # ===== Step 5: Continuity =====
            logger.info(f"[Task {gen_task.id}] Step 5: Continuity")
            continuity_result = await self._run_continuity(db, gen_task, chapter, draft_content, bible_data)
            steps_data.append(continuity_result)
            total_tokens += continuity_result.get("tokens", 0)
            total_cost += continuity_result.get("cost", 0.0)

            continuity_score = continuity_result.get("score", 0)
            continuity_report = continuity_result.get("report", "")
            current_version.continuity_report = continuity_report
            db.commit()

            # ===== Step 6: Learning =====
            logger.info(f"[Task {gen_task.id}] Step 6: Learning")
            learning_result = await self._run_learning(db, gen_task, chapter, steps_data)
            steps_data.append(learning_result)
            total_tokens += learning_result.get("tokens", 0)
            total_cost += learning_result.get("cost", 0.0)

            # 接受最终版本
            current_version.is_accepted = 1
            current_version.acceptance_reason = f"最终评分: {score}, 连续性评分: {continuity_score}"
            current_version.final_content = draft_content
            chapter.current_version = current_version.version_number

            # 更新章节评分
            chapter.total_score = score
            chapter.continuity_score = continuity_score
            if score_breakdown:
                chapter.plot_progress_score = score_breakdown.get("plot_progress", 0)
                chapter.character_consistency_score = score_breakdown.get("character_consistency", 0)
                chapter.pacing_score = score_breakdown.get("pacing", 0)
                chapter.hook_score = score_breakdown.get("hook", 0)
                chapter.emotional_reward_score = score_breakdown.get("emotional_reward", 0)
                chapter.style_consistency_score = score_breakdown.get("style_consistency", 0)
                chapter.clarity_score = score_breakdown.get("clarity", 0)
                chapter.readability_score = score_breakdown.get("readability", 0)

            db.commit()

            return {
                "success": True,
                "completed_steps": len(steps_data),
                "total_steps": len(steps_data),
                "tokens_used": total_tokens,
                "cost": total_cost,
                "word_count": len(draft_content),
                "final_content": draft_content,
                "final_score": score,
                "version_number": current_version.version_number,
                "steps": steps_data,
            }

        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            return {"success": False, "error": str(e)}

    def _bible_to_dict(self, bible: Optional[NovelBible]) -> dict:
        """将 Bible ORM 对象转换为字典"""
        if not bible:
            return {}
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

    def _get_or_create_version(self, db: Session, chapter: Chapter, version_number: int) -> ChapterVersion:
        """获取或创建章节版本"""
        version = db.query(ChapterVersion).filter(
            ChapterVersion.chapter_id == chapter.id,
            ChapterVersion.version_number == version_number
        ).first()

        if not version:
            version = ChapterVersion(
                chapter_id=chapter.id,
                version_number=version_number,
            )
            db.add(version)
            db.commit()
            db.refresh(version)

        return version

    async def _run_planner(self, db, gen_task, chapter, bible_data: dict) -> dict:
        """执行 Planner Agent"""
        prompt = f"""请为以下章节进行详细规划：

章节标题: {chapter.title}
章节序号: {chapter.chapter_index}

世界观设定:
{bible_data.get('world_setting', '无')}

人物设定:
{json.dumps(bible_data.get('characters', []), ensure_ascii=False, indent=2)}

主线剧情:
{bible_data.get('main_plot', '无')}

章纲:
{json.dumps(bible_data.get('chapter_outline', []), ensure_ascii=False, indent=2)}

请输出：
1. 本章目标
2. 冲突设计（外部冲突、内部冲突）
3. 人物安排
4. 章节钩子（开头钩子、结尾钩子）
5. 情绪节奏设计
6. 关键剧情点（3-5个）"""

        try:
            response = await llm_manager.generate(prompt=prompt, role="planner", temperature=0.7)

            # 保存步骤
            step = self._save_step(db, gen_task, chapter, "Planner", prompt, response)

            return {
                "success": True,
                "agent": "Planner",
                "plan": {"content": response.get("content", "")},
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }
        except Exception as e:
            logger.error(f"Planner 执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _run_draft(self, db, gen_task, chapter, bible_data: dict, chapter_plan: dict) -> dict:
        """执行 Draft Agent"""
        prompt = f"""请根据以下规划起草章节内容：

章节标题: {chapter.title}
章节序号: {chapter.chapter_index}

章节规划:
{json.dumps(chapter_plan, ensure_ascii=False, indent=2)}

世界观设定:
{bible_data.get('world_setting', '')}

人物设定:
{json.dumps(bible_data.get('characters', []), ensure_ascii=False, indent=2)}

风格边界:
{json.dumps(bible_data.get('style_boundaries', []), ensure_ascii=False, indent=2)}

写作要求：
- 使用中文写作
- 注意节奏控制
- 对话自然
- 场景描写生动
- 避免使用禁止设定: {json.dumps(bible_data.get('forbidden_items', []), ensure_ascii=False)}

请直接输出章节正文内容："""

        try:
            response = await llm_manager.generate(prompt=prompt, role="draft", temperature=0.8)

            # 保存步骤
            step = self._save_step(db, gen_task, chapter, "Draft", prompt, response)

            return {
                "success": True,
                "agent": "Draft",
                "content": response.get("content", ""),
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }
        except Exception as e:
            logger.error(f"Draft 执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _run_critic(self, db, gen_task, chapter, content: str, bible_data: dict) -> dict:
        """执行 Critic Agent"""
        prompt = f"""请对以下章节进行多维度审稿评分：

章节标题: {chapter.title}

章节内容:
{content[:5000]}

请从以下维度评分（每项满分100）：
1. 剧情推进 (plot_progress)
2. 人物一致性 (character_consistency)
3. 节奏控制 (pacing)
4. 章节钩子 (hook)
5. 情绪回报 (emotional_reward)
6. 文风稳定 (style_consistency)
7. 连续性 (continuity)
8. 信息清晰度 (clarity)
9. 商业可读性 (readability)

请输出：
1. 综合评分（满分100）
2. 各维度得分（JSON格式）
3. 问题列表（如有）
4. 改进建议"""

        try:
            response = await llm_manager.generate(prompt=prompt, role="critic", temperature=0.3)

            content_text = response.get("content", "")
            score = self._extract_score(content_text)
            score_breakdown = self._extract_score_breakdown(content_text)

            # 保存步骤
            step = self._save_step(db, gen_task, chapter, "Critic", prompt, response, score=score, score_breakdown=score_breakdown)

            return {
                "success": True,
                "agent": "Critic",
                "score": score,
                "score_breakdown": score_breakdown,
                "critique": content_text,
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }
        except Exception as e:
            logger.error(f"Critic 执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _run_rewrite(self, db, gen_task, chapter, content: str, critique: str, bible_data: dict, is_darwin: bool = False) -> dict:
        """执行 Rewrite Agent"""
        darwin_note = "【Darwin 进化迭代】" if is_darwin else ""

        prompt = f"""{darwin_note}
请根据审稿意见改写文章：

章节标题: {chapter.title}

原内容:
{content[:5000]}

审稿意见:
{critique}

请输出改写后的完整章节内容，注意：
- 保持原有情节和风格
- 针对审稿意见进行改进
- 提高可读性和流畅度
- 章节字数保持在2000-5000字之间"""

        try:
            response = await llm_manager.generate(prompt=prompt, role="rewrite", temperature=0.7)

            # 保存步骤
            step = self._save_step(db, gen_task, chapter, "Rewrite", prompt, response)

            return {
                "success": True,
                "agent": "Rewrite",
                "content": response.get("content", ""),
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }
        except Exception as e:
            logger.error(f"Rewrite 执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _run_continuity(self, db, gen_task, chapter, content: str, bible_data: dict) -> dict:
        """执行 Continuity Agent"""
        prompt = f"""请检查以下章节的连续性：

章节标题: {chapter.title}
章节序号: {chapter.chapter_index}

章节内容:
{content[:3000]}

人物设定:
{json.dumps(bible_data.get('characters', []), ensure_ascii=False, indent=2)}

伏笔列表:
{json.dumps(bible_data.get('foreshadowing', []), ensure_ascii=False, indent=2)}

请检查：
1. 人设一致性
2. 设定一致性
3. 时间线连续性
4. 伏笔回收情况
5. 潜在问题

请输出检查结果和建议。如检查通过，请说明"通过"。"""

        try:
            response = await llm_manager.generate(prompt=prompt, role="continuity", temperature=0.3)

            content_text = response.get("content", "")
            score = 90 if "通过" in content_text else 75

            # 保存步骤
            step = self._save_step(db, gen_task, chapter, "Continuity", prompt, response, score=score)

            return {
                "success": True,
                "agent": "Continuity",
                "score": score,
                "report": content_text,
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }
        except Exception as e:
            logger.error(f"Continuity 执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _run_learning(self, db, gen_task, chapter, steps_data: list) -> dict:
        """执行 Learning Agent"""
        prompt = f"""请总结本章写作过程的经验：

章节标题: {chapter.title}

写作流程回顾:
{json.dumps([{"agent": s.get("agent"), "score": s.get("score")} for s in steps_data], ensure_ascii=False)}

请提取：
1. 本章成功经验
2. 改进空间
3. 可复用的技巧（3-5个技巧卡片）"""

        try:
            response = await llm_manager.generate(prompt=prompt, role="learning", temperature=0.5)

            # 保存步骤
            step = self._save_step(db, gen_task, chapter, "Learning", prompt, response)

            return {
                "success": True,
                "agent": "Learning",
                "tokens": response.get("total_tokens", 0),
                "cost": response.get("cost", 0.0),
            }
        except Exception as e:
            logger.error(f"Learning 执行失败: {e}")
            return {"success": False, "error": str(e)}

    def _save_step(self, db, gen_task, chapter, agent_name, prompt, response, score=None, score_breakdown=None):
        """保存生成步骤"""
        step_index = db.query(GenerationStep).filter(
            GenerationStep.task_id == gen_task.id
        ).count() + 1

        step = GenerationStep(
            task_id=gen_task.id,
            chapter_id=chapter.id,
            step_index=step_index,
            agent_name=agent_name,
            input_prompt=prompt[:5000],
            raw_output=response.get("content", ""),
            parsed_output=response.get("content", ""),
            score=score,
            score_breakdown=score_breakdown,
            model_name=response.get("model", "unknown"),
            provider_name=response.get("provider", "unknown"),
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
            duration_seconds=int(response.get("duration_seconds", 0)),
        )
        db.add(step)
        db.commit()
        return step

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

    def _check_budget(self, project: Project) -> bool:
        """检查预算限制"""
        if not project.config:
            return True

        daily_word_goal = project.config.get("daily_word_goal", 10000)
        if self.daily_stats["words_written"] >= daily_word_goal:
            return False

        token_budget = project.config.get("daily_token_budget", 100000)
        if self.daily_stats["tokens_used"] >= token_budget:
            return False

        cost_budget = project.config.get("daily_cost_budget", 10.0)
        if self.daily_stats["cost"] >= cost_budget:
            return False

        return True

    def get_status(self) -> dict:
        """获取 Worker 状态"""
        return {
            "status": self.status.value,
            "current_task": self.current_task,
            "daily_stats": self.daily_stats,
            "uptime": (
                (datetime.now() - self.daily_stats["start_time"]).total_seconds()
                if self.daily_stats["start_time"]
                else 0
            ),
        }

    def reset_daily_stats(self):
        """重置每日统计"""
        self.daily_stats = {
            "words_written": 0,
            "chapters_completed": 0,
            "tokens_used": 0,
            "cost": 0.0,
            "start_time": datetime.now(),
        }


# 全局 Worker 实例
worker = WritingWorker()
