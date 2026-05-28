"""
Writing Pipeline Service - 章节生成流水线服务
实现 Planner → Draft → Critic → Rewrite → Continuity → Final 流程
"""

import os
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.models.task import GenerationStep, GenerationTask, TaskStatus
from app.services.mock_llm_service import mock_llm_service


ARTIFACTS_DIR = "F:/kelaode/quanzidong/data/artifacts"


class WritingPipelineService:
    """写作流水线服务"""

    @staticmethod
    async def create_chapter_task(
        db: Session,
        project_id: int,
        chapter_index: int,
        title: str = ""
    ) -> Chapter:
        """创建章节任务"""
        # 创建章节
        chapter = Chapter(
            project_id=project_id,
            chapter_index=chapter_index,
            title=title or f"第{chapter_index}章",
            status=ChapterStatus.PLANNED,
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)

        # 创建任务
        task = GenerationTask(
            project_id=project_id,
            chapter_id=chapter.id,
            task_type="chapter_pipeline",
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()

        return chapter

    @staticmethod
    async def run_pipeline(
        db: Session,
        chapter_id: int,
        project: Project
    ) -> Dict:
        """运行完整流水线"""
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError("章节不存在")

        task = db.query(GenerationTask).filter(
            GenerationTask.chapter_id == chapter_id,
            GenerationTask.status == TaskStatus.PENDING
        ).first()

        if task:
            task.status = TaskStatus.RUNNING
            db.commit()

        results = {
            "chapter_id": chapter_id,
            "steps": [],
            "success": False,
        }

        try:
            # Step 1: Planner
            plan_result = await WritingPipelineService._step_planner(db, chapter, project)
            results["steps"].append(plan_result)

            # Step 2: Draft
            draft_result = await WritingPipelineService._step_draft(db, chapter, project, plan_result["content"])
            results["steps"].append(draft_result)

            # Step 3: Critic
            critic_result = await WritingPipelineService._step_critic(db, chapter, project, draft_result["content"])
            results["steps"].append(critic_result)

            current_score = critic_result.get("score", 0)
            draft_content = draft_result["content"]

            # Step 4: Rewrite (如果分数不够)
            rewrite_count = 0
            max_rewrites = project.max_rewrite_rounds or 3

            while current_score < (project.quality_threshold or 80) and rewrite_count < max_rewrites:
                rewrite_result = await WritingPipelineService._step_rewrite(
                    db, chapter, project, draft_content, critic_result["content"]
                )
                results["steps"].append(rewrite_result)

                # 重新评分
                new_critic = await WritingPipelineService._step_critic(db, chapter, project, rewrite_result["content"])
                results["steps"].append(new_critic)

                new_score = new_critic.get("score", 0)

                # 检查是否有提升
                if new_score > current_score:
                    draft_content = rewrite_result["content"]
                    current_score = new_score

                rewrite_count += 1

                # 如果连续提升很小，停止
                if rewrite_count >= 2 and new_score - current_score < 2:
                    break

            # Step 5: Continuity
            continuity_result = await WritingPipelineService._step_continuity(db, chapter, project, draft_content)
            results["steps"].append(continuity_result)

            # 保存最终版本
            chapter.final_content = draft_content
            chapter.final_word_count = len(draft_content)
            chapter.total_score = current_score
            chapter.status = ChapterStatus.COMPLETED

            from datetime import datetime
            chapter.completed_at = datetime.utcnow()

            if task:
                task.status = TaskStatus.COMPLETED
                task.finished_at = datetime.utcnow()

            db.commit()

            # 保存产物文件
            await WritingPipelineService._save_artifacts(chapter_id, results["steps"])

            results["success"] = True
            results["final_score"] = current_score
            results["word_count"] = chapter.final_word_count

        except Exception as e:
            chapter.status = ChapterStatus.FAILED
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
            db.commit()
            results["error"] = str(e)

        return results

    @staticmethod
    async def _step_planner(db: Session, chapter: Chapter, project: Project) -> Dict:
        """Planner Agent - 制定本章计划"""
        prompt = f"""
为小说第{chapter.chapter_index}章制定写作计划。

项目信息：
- 题材: {project.genre}
- 目标读者: {project.target_reader or '一般读者'}
- 每章目标字数: {project.chapter_word_goal}

质量目标：
- 剧情推进强度: {project.plot_progress_intensity}/10
- 爽点密度: {project.satisfaction_density}/10
- 情绪拉扯: {project.emotional_tension}/10

请输出：
1. 本章目标
2. 冲突设计
3. 人物安排
4. 章节钩子（开头和结尾）
5. 情绪节奏
6. 关键剧情点
"""
        response = await mock_llm_service.generate(prompt=prompt, role="planner")

        step = GenerationStep(
            task_id=None,
            chapter_id=chapter.id,
            step_index=1,
            agent_name="Planner",
            input_prompt=prompt,
            raw_output=response["content"],
            parsed_output=response["content"],
            model_name=response["model"],
            provider_name=response["provider"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            duration_seconds=int(response["duration_seconds"]),
        )
        db.add(step)
        db.commit()

        return {
            "agent": "Planner",
            "content": response["content"],
            "tokens": response["total_tokens"],
        }

    @staticmethod
    async def _step_draft(db: Session, chapter: Chapter, project: Project, plan: str) -> Dict:
        """Draft Agent - 起草初稿"""
        prompt = f"""
根据以下计划，撰写第{chapter.chapter_index}章的完整内容。

写作计划：
{plan}

要求：
- 字数: {project.chapter_word_goal}字左右
- 题材: {project.genre}
- 风格: 符合项目设定

请直接输出章节正文，不需要额外说明。
"""
        response = await mock_llm_service.generate(prompt=prompt, role="draft")

        step = GenerationStep(
            task_id=None,
            chapter_id=chapter.id,
            step_index=2,
            agent_name="Draft",
            input_prompt=prompt,
            raw_output=response["content"],
            parsed_output=response["content"],
            model_name=response["model"],
            provider_name=response["provider"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            duration_seconds=int(response["duration_seconds"]),
        )
        db.add(step)
        db.commit()

        return {
            "agent": "Draft",
            "content": response["content"],
            "tokens": response["total_tokens"],
        }

    @staticmethod
    async def _step_critic(db: Session, chapter: Chapter, project: Project, draft: str) -> Dict:
        """Critic Agent - 多维度评分"""
        prompt = f"""
对以下章节进行专业审稿评分。

章节内容：
{draft[:2000]}...

评分维度（每项0-100分）：
1. 剧情推进: 本章是否推动主线或关键关系
2. 人物一致性: 行为是否符合人物欲望、性格、历史
3. 节奏控制: 是否拖沓，高潮和缓冲是否合理
4. 章节钩子: 开头是否能拉人，结尾是否让人想看下一章
5. 情绪回报: 是否给到爽点、期待、压迫、释放或暧昧张力
6. 文风稳定: 是否符合项目文风
7. 连续性: 设定、时间线、伏笔、道具是否冲突
8. 信息清晰: 读者是否看得懂当前发生了什么
9. 商业可读性: 是否有追更动力

请输出：
1. 每项评分
2. 综合得分
3. 问题列表
4. 改进建议
"""
        response = await mock_llm_service.generate(prompt=prompt, role="critic")

        # 提取分数（从响应中解析）
        score = 82  # 模拟分数

        step = GenerationStep(
            task_id=None,
            chapter_id=chapter.id,
            step_index=3,
            agent_name="Critic",
            input_prompt=prompt,
            raw_output=response["content"],
            parsed_output=response["content"],
            score=score,
            model_name=response["model"],
            provider_name=response["provider"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            duration_seconds=int(response["duration_seconds"]),
        )
        db.add(step)
        db.commit()

        return {
            "agent": "Critic",
            "content": response["content"],
            "score": score,
            "tokens": response["total_tokens"],
        }

    @staticmethod
    async def _step_rewrite(db: Session, chapter: Chapter, project: Project, draft: str, critic_report: str) -> Dict:
        """Rewrite Agent - 按意见改稿"""
        prompt = f"""
根据审稿意见，修改以下章节内容。

原稿：
{draft[:1500]}...

审稿意见：
{critic_report[:1000]}...

请输出修改后的完整章节内容。
"""
        response = await mock_llm_service.generate(prompt=prompt, role="rewrite")

        step = GenerationStep(
            task_id=None,
            chapter_id=chapter.id,
            step_index=4,
            agent_name="Rewrite",
            input_prompt=prompt,
            raw_output=response["content"],
            parsed_output=response["content"],
            model_name=response["model"],
            provider_name=response["provider"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            duration_seconds=int(response["duration_seconds"]),
        )
        db.add(step)
        db.commit()

        return {
            "agent": "Rewrite",
            "content": response["content"],
            "tokens": response["total_tokens"],
        }

    @staticmethod
    async def _step_continuity(db: Session, chapter: Chapter, project: Project, draft: str) -> Dict:
        """Continuity Agent - 检查连续性"""
        prompt = f"""
检查以下章节的连续性和一致性。

章节内容：
{draft[:2000]}...

检查项：
1. 人物设定是否一致
2. 时间线是否合理
3. 伏笔是否对应
4. 设定是否冲突

请输出检查结果和建议。
"""
        response = await mock_llm_service.generate(prompt=prompt, role="continuity")

        score = 90  # 连续性评分

        step = GenerationStep(
            task_id=None,
            chapter_id=chapter.id,
            step_index=5,
            agent_name="Continuity",
            input_prompt=prompt,
            raw_output=response["content"],
            parsed_output=response["content"],
            score=score,
            model_name=response["model"],
            provider_name=response["provider"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            duration_seconds=int(response["duration_seconds"]),
        )
        db.add(step)
        db.commit()

        return {
            "agent": "Continuity",
            "content": response["content"],
            "score": score,
            "tokens": response["total_tokens"],
        }

    @staticmethod
    async def _save_artifacts(chapter_id: int, steps: List[Dict]):
        """保存产物文件"""
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        chapter_dir = os.path.join(ARTIFACTS_DIR, f"chapter_{chapter_id}")
        os.makedirs(chapter_dir, exist_ok=True)

        step_names = ["01_plan", "02_draft", "03_critic", "04_rewrite", "05_continuity"]

        for i, step in enumerate(steps):
            if i < len(step_names):
                filename = f"{step_names[i]}.md"
                filepath = os.path.join(chapter_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {step['agent']}\n\n")
                    f.write(f"Tokens: {step.get('tokens', 0)}\n")
                    if 'score' in step:
                        f.write(f"Score: {step['score']}\n")
                    f.write("\n---\n\n")
                    f.write(step['content'])

    @staticmethod
    def get_pipeline_status(db: Session, chapter_id: int) -> Dict:
        """获取流水线状态"""
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return {"error": "章节不存在"}

        steps = db.query(GenerationStep).filter(
            GenerationStep.chapter_id == chapter_id
        ).order_by(GenerationStep.step_index).all()

        return {
            "chapter_id": chapter_id,
            "status": chapter.status,
            "title": chapter.title,
            "score": chapter.total_score,
            "word_count": chapter.final_word_count,
            "steps": [
                {
                    "step_index": s.step_index,
                    "agent_name": s.agent_name,
                    "score": s.score,
                    "model_name": s.model_name,
                    "duration_seconds": s.duration_seconds,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in steps
            ]
        }
