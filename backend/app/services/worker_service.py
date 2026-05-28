"""
Worker Service - 24小时自动写作后台任务调度器 (P3版本)
基于 GenerationTask 的调度，支持 Darwin 进化
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
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
                chapter.final_content = result.get("final_content", "")
                chapter.final_word_count = len(result.get("final_content", ""))
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
        """
        steps_data = []
        total_tokens = 0
        total_cost = 0.0
        bible = project.bible

        try:
            # ===== Step 1: Planner =====
            logger.info(f"[Task {gen_task.id}] Step 1: Planner")
            planner_result = await self._run_planner(db, gen_task, chapter, bible)
            steps_data.append(planner_result)
            total_tokens += planner_result.get("tokens", 0)
            total_cost += planner_result.get("cost", 0.0)

            if not planner_result.get("success"):
                return {"success": False, "error": "Planner 失败", "step": "planner"}

            chapter_plan = planner_result.get("plan", {})

            # ===== Step 2: Draft =====
            logger.info(f"[Task {gen_task.id}] Step 2: Draft")
            draft_result = await self._run_draft(db, gen_task, chapter, bible, chapter_plan)
            steps_data.append(draft_result)
            total_tokens += draft_result.get("tokens", 0)
            total_cost += draft_result.get("cost", 0.0)

            if not draft_result.get("success"):
                return {"success": False, "error": "Draft 失败", "step": "draft"}

            draft_content = draft_result.get("content", "")

            # ===== Step 3: Critic =====
            logger.info(f"[Task {gen_task.id}] Step 3: Critic")
            critic_result = await self._run_critic(db, gen_task, chapter, draft_content, bible)
            steps_data.append(critic_result)
            total_tokens += critic_result.get("tokens", 0)
            total_cost += critic_result.get("cost", 0.0)

            if not critic_result.get("success"):
                return {"success": False, "error": "Critic 失败", "step": "critic"}

            score = critic_result.get("score", 0)
            critique = critic_result.get("critique", "")

            # ===== Step 4: Rewrite (如果分数不够高) =====
            rewrite_result = None
            if score < 80:
                logger.info(f"[Task {gen_task.id}] Step 4: Rewrite (score={score})")
                rewrite_result = await self._run_rewrite(
                    db, gen_task, chapter, draft_content, critique, bible
                )
                steps_data.append(rewrite_result)
                total_tokens += rewrite_result.get("tokens", 0)
                total_cost += rewrite_result.get("cost", 0.0)

                if rewrite_result.get("success"):
                    draft_content = rewrite_result.get("content", draft_content)

                # Rewrite 后再次审稿
                logger.info(f"[Task {gen_task.id}] Step 4b: Re-Critic after rewrite")
                critic_result2 = await self._run_critic(db, gen_task, chapter, draft_content, bible)
                steps_data.append(critic_result2)
                total_tokens += critic_result2.get("tokens", 0)
                total_cost += critic_result2.get("cost", 0.0)
                score = critic_result2.get("score", score)

            # ===== Step 5: Continuity =====
            logger.info(f"[Task {gen_task.id}] Step 5: Continuity")
            continuity_result = await self._run_continuity(db, gen_task, chapter, draft_content, bible)
            steps_data.append(continuity_result)
            total_tokens += continuity_result.get("tokens", 0)
            total_cost += continuity_result.get("cost", 0.0)

            # ===== Darwin 进化决策 =====
            logger.info(f"[Task {gen_task.id}] Darwin 进化决策")
            evolution_decision = await self._darwin_decision(
                db, gen_task, chapter, steps_data, score
            )

            if not evolution_decision.get("keep", True):
                # 回滚 - 需要重写
                logger.info(f"[Task {gen_task.id}] Darwin 决定回滚，重新生成")
                # 使用进化服务获取改进建议
                improvements = evolution_decision.get("improvements", [])
                # 重新生成
                rewrite_result2 = await self._run_rewrite(
                    db, gen_task, chapter, draft_content,
                    "; ".join(improvements), bible, is_darwin=True
                )
                steps_data.append(rewrite_result2)
                total_tokens += rewrite_result2.get("tokens", 0)
                total_cost += rewrite_result2.get("cost", 0.0)

                if rewrite_result2.get("success"):
                    draft_content = rewrite_result2.get("content", draft_content)

            # ===== Step 6: Learning =====
            logger.info(f"[Task {gen_task.id}] Step 6: Learning")
            learning_result = await self._run_learning(db, gen_task, chapter, steps_data)
            steps_data.append(learning_result)
            total_tokens += learning_result.get("tokens", 0)
            total_cost += learning_result.get("cost", 0.0)

            # 更新章节内容
            chapter.draft_content = draft_content
            chapter.total_score = score
            chapter.continuity_score = continuity_result.get("score", 0)
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
                "steps": steps_data,
            }

        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            return {"success": False, "error": str(e)}

    # ===== 各 Agent 执行方法 =====

    async def _run_planner(self, db, gen_task, chapter, bible) -> dict:
        """执行 Planner Agent"""
        prompt = f"""请为以下章节进行详细规划：

章节标题: {chapter.title}
章节序号: {chapter.chapter_index}

世界观设定:
{bible.get('worldbuilding', '无') if bible else '无'}

人物设定:
{bible.get('characters', '无') if bible else '无'}

请输出：
1. 本章目标
2. 冲突设计（外部冲突、内部冲突）
3. 人物安排
4. 章节钩子（开头钩子、结尾钩子）
5. 情绪节奏设计
6. 关键剧情点（3-5个）"""

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

    async def _run_draft(self, db, gen_task, chapter, bible, chapter_plan) -> dict:
        """执行 Draft Agent"""
        prompt = f"""请根据以下规划起草章节内容：

章节标题: {chapter.title}
章节序号: {chapter.chapter_index}

章节规划:
{chapter_plan.get('content', '')}

世界观设定:
{bible.get('worldbuilding', '') if bible else ''}

写作要求：
- 使用中文写作
- 注意节奏控制
- 对话自然
- 场景描写生动

请直接输出章节正文内容："""

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

    async def _run_critic(self, db, gen_task, chapter, content, bible) -> dict:
        """执行 Critic Agent"""
        prompt = f"""请对以下章节进行多维度审稿评分：

章节标题: {chapter.title}

章节内容:
{content[:5000]}  # 限制长度避免过长

请从以下维度评分（每项满分100）：
1. 剧情推进
2. 人物一致性
3. 节奏控制
4. 章节钩子
5. 情绪回报
6. 文风稳定
7. 连续性
8. 信息清晰度
9. 商业可读性

请输出：
1. 综合评分
2. 各维度得分
3. 问题列表（如有）
4. 改进建议"""

        response = await llm_manager.generate(prompt=prompt, role="critic", temperature=0.3)

        # 解析评分（简单提取数字）
        content_text = response.get("content", "")
        score = self._extract_score(content_text)

        # 保存步骤
        step = self._save_step(db, gen_task, chapter, "Critic", prompt, response, score=score)

        return {
            "success": True,
            "agent": "Critic",
            "score": score,
            "critique": content_text,
            "tokens": response.get("total_tokens", 0),
            "cost": response.get("cost", 0.0),
        }

    async def _run_rewrite(self, db, gen_task, chapter, content, critique, bible, is_darwin=False) -> dict:
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
- 提高可读性和流畅度"""

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

    async def _run_continuity(self, db, gen_task, chapter, content, bible) -> dict:
        """执行 Continuity Agent"""
        prompt = f"""请检查以下章节的连续性：

章节标题: {chapter.title}
章节序号: {chapter.chapter_index}

章节内容:
{content[:3000]}

请检查：
1. 人设一致性
2. 设定一致性
3. 时间线连续性
4. 伏笔回收情况
5. 潜在问题

请输出检查结果和建议。"""

        response = await llm_manager.generate(prompt=prompt, role="continuity", temperature=0.3)

        # 简单评分
        score = 85 if "通过" in response.get("content", "") else 70

        # 保存步骤
        step = self._save_step(db, gen_task, chapter, "Continuity", prompt, response, score=score)

        return {
            "success": True,
            "agent": "Continuity",
            "score": score,
            "tokens": response.get("total_tokens", 0),
            "cost": response.get("cost", 0.0),
        }

    async def _run_learning(self, db, gen_task, chapter, steps_data) -> dict:
        """执行 Learning Agent"""
        prompt = f"""请总结本章写作过程的经验：

章节标题: {chapter.title}

写作流程回顾:
{json.dumps([{"agent": s.get("agent"), "score": s.get("score")} for s in steps_data], ensure_ascii=False)}

请提取：
1. 本章成功经验
2. 改进空间
3. 可复用的技巧（3-5个技巧卡片）"""

        response = await llm_manager.generate(prompt=prompt, role="learning", temperature=0.5)

        # 保存步骤
        step = self._save_step(db, gen_task, chapter, "Learning", prompt, response)

        return {
            "success": True,
            "agent": "Learning",
            "tokens": response.get("total_tokens", 0),
            "cost": response.get("cost", 0.0),
        }

    async def _darwin_decision(self, db, gen_task, chapter, steps_data, final_score) -> dict:
        """
        Darwin 进化决策
        评估是否保留当前结果，还是回滚重新生成
        """
        # 使用进化服务评估
        try:
            decision = await self.evolution_service.evaluate_generation(
                db=db,
                chapter_id=chapter.id,
                steps_data=steps_data,
                final_score=final_score
            )
            return decision
        except Exception as e:
            logger.warning(f"Darwin 决策失败: {e}，默认保留")
            return {"keep": True, "reason": "评估失败，默认保留"}

    def _save_step(self, db, gen_task, chapter, agent_name, prompt, response, score=None):
        """保存生成步骤"""
        step_index = db.query(GenerationStep).filter(
            GenerationStep.task_id == gen_task.id
        ).count() + 1

        step = GenerationStep(
            task_id=gen_task.id,
            chapter_id=chapter.id,
            step_index=step_index,
            agent_name=agent_name,
            input_prompt=prompt[:5000],  # 限制长度
            raw_output=response.get("content", ""),
            parsed_output=response.get("content", ""),
            score=score,
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
        # 尝试匹配 "综合评分: XX" 或 "总分: XX" 或 "XX/100"
        patterns = [
            r'综合评分[:：]\s*(\d+)',
            r'总分[:：]\s*(\d+)',
            r'(\d+)\s*分',
            r'(\d+)/100',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                score = int(match.group(1))
                return min(100, max(0, score))
        # 默认返回 75
        return 75

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
