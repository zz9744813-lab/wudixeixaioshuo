"""
ReaderTrainingService - 异步真人训练营 (P2)

设计原则：
- submit_feedback 同步快返，只入库，不调用 LLM，不阻塞 Worker
- process_pending_batch 攒够 N 条才批处理成规则，计算 critic_gap
- get_reader_rules_for_prompt 给各 Agent 取高优先级真人规则
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.feedback import Feedback, FeedbackBatch
from app.services.event_bus import event_bus
from app.services.evolution_orchestrator import EvolutionOrchestrator
from app.services.openai_llm_service import llm_manager
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

_VALID_REACTIONS = {"hooked", "meh", "dropped"}
_CRITIC_GAP_THRESHOLD = 12.0


class ReaderTrainingService:
    """真人训练营服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== P2-2: 同步快返提交 ==========

    def submit_feedback(
        self,
        project_id: int,
        chapter_id: int,
        reader_score: Optional[float] = None,
        dimension_scores: Optional[dict] = None,
        anchor: Optional[List[dict]] = None,
        reaction: Optional[str] = None,
        raw_comment: Optional[str] = None,
        reader_id: Optional[str] = None,
        min_batch: int = 5,
    ) -> dict:
        """同步快返：只入库，不做 LLM，不阻塞。"""
        if reaction is not None and reaction not in _VALID_REACTIONS:
            raise ValueError(f"reaction 必须是 {_VALID_REACTIONS} 之一")
        if reader_score is not None and not (0 <= reader_score <= 100):
            raise ValueError("reader_score 必须在 0-100 之间")

        fb = Feedback(
            project_id=project_id,
            chapter_id=chapter_id,
            source="reader",
            raw_text=raw_comment or "",
            reader_score=reader_score,
            dimension_scores=dimension_scores or {},
            anchor=anchor or [],
            reaction=reaction,
            status="queued",
        )
        self.db.add(fb)
        self.db.commit()
        self.db.refresh(fb)

        pending_count = self._count_pending(project_id)
        needed = max(0, min_batch - pending_count)

        # 事件发布失败不影响入库
        self._publish("feedback.queued", {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "feedback_id": fb.id,
            "pending_count": pending_count,
            "min_batch": min_batch,
            "message": f"反馈已入队，攒够 {min_batch} 条后生效",
        })

        return {
            "status": "queued",
            "message": f"反馈已入队，攒够 {min_batch} 条后生效",
            "feedback_id": fb.id,
            "pending_count": pending_count,
            "needed_for_batch": needed,
            "min_batch": min_batch,
        }

    def _count_pending(self, project_id: Optional[int]) -> int:
        q = self.db.query(Feedback).filter(
            Feedback.status == "queued",
            Feedback.source == "reader",
        )
        if project_id:
            q = q.filter(Feedback.project_id == project_id)
        return q.count()

    def _publish(self, event_type: str, data: dict):
        """同步上下文下尽力发布事件，失败仅记日志。"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(event_bus.publish(event_type, data))
            else:
                loop.run_until_complete(event_bus.publish(event_type, data))
        except Exception as e:
            logger.debug(f"事件发布跳过 ({event_type}): {e}")

    # ========== P2-3: 批处理 ==========

    async def process_pending_batch(
        self,
        project_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        min_batch: int = 5,
    ) -> dict:
        """攒够 N 条 queued 反馈后批处理成规则，并计算 critic_gap。"""
        q = self.db.query(Feedback).filter(
            Feedback.status == "queued",
            Feedback.source == "reader",
        )
        if project_id:
            q = q.filter(Feedback.project_id == project_id)
        if chapter_id:
            q = q.filter(Feedback.chapter_id == chapter_id)
        pending = q.order_by(Feedback.created_at.asc()).all()

        if len(pending) < min_batch:
            return {
                "status": "waiting",
                "pending_count": len(pending),
                "min_batch": min_batch,
                "message": "反馈已入队，继续等待更多真人反馈",
            }

        batch = FeedbackBatch(
            project_id=project_id or pending[0].project_id,
            chapter_id=chapter_id,
            feedback_ids=[f.id for f in pending],
            feedback_count=len(pending),
            status="processing",
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        await event_bus.publish("feedback.batch.processing", {
            "project_id": batch.project_id, "batch_id": batch.id,
            "feedback_count": batch.feedback_count,
        })

        try:
            parsed = await self._llm_parse_feedbacks(batch.project_id, pending)
        except Exception as e:
            batch.status = "failed"
            batch.error_message = str(e)[:1000]
            self.db.commit()
            await event_bus.publish("feedback.batch.failed", {
                "project_id": batch.project_id, "batch_id": batch.id,
                "error": str(e)[:200],
            })
            return {"status": "failed", "batch_id": batch.id, "error": str(e)[:200]}

        if not parsed:
            parsed = self._fallback_parse(pending)

        # 评分聚合
        reader_scores = [f.reader_score for f in pending if f.reader_score is not None]
        avg_reader = round(sum(reader_scores) / len(reader_scores), 2) if reader_scores else None
        avg_system = self._avg_system_score(pending)
        critic_gap = None
        if avg_reader is not None and avg_system is not None:
            critic_gap = round(avg_reader - avg_system, 2)

        derived_rules = parsed.get("derived_rules", []) or []
        need_calibration = bool(critic_gap is not None and abs(critic_gap) > _CRITIC_GAP_THRESHOLD)
        if need_calibration:
            derived_rules.append(self._build_calibration_rule(avg_reader, avg_system, critic_gap))

        batch.derived_rules = derived_rules
        batch.dimension_summary = parsed.get("dimension_summary", {}) or {}
        batch.reaction_summary = parsed.get("reaction_summary", {}) or self._reaction_summary(pending)
        batch.avg_reader_score = avg_reader
        batch.avg_system_score = avg_system
        batch.critic_gap = critic_gap
        batch.triggered_critic_calibration = 1 if need_calibration else 0
        batch.status = "processed"
        batch.processed_at = utc_now()

        for f in pending:
            f.status = "batched"
            f.batch_id = batch.id
            f.is_processed = 1
        self.db.commit()
        self.db.refresh(batch)

        await event_bus.publish("feedback.batch.processed", {
            "project_id": batch.project_id,
            "batch_id": batch.id,
            "feedback_count": batch.feedback_count,
            "derived_rules_count": len(derived_rules),
            "critic_gap": critic_gap,
            "triggered_critic_calibration": need_calibration,
        })
        if need_calibration:
            await event_bus.publish("critic.calibration.requested", {
                "project_id": batch.project_id, "batch_id": batch.id,
                "avg_reader_score": avg_reader, "avg_system_score": avg_system,
                "critic_gap": critic_gap,
            })

            await self._trigger_evolution_and_calibration(
                batch=batch,
                avg_reader=avg_reader,
                avg_system=avg_system,
                critic_gap=critic_gap,
                derived_rules=derived_rules,
            )
        return {
            "status": "processed",
            "batch_id": batch.id,
            "feedback_count": batch.feedback_count,
            "avg_reader_score": avg_reader,
            "avg_system_score": avg_system,
            "critic_gap": critic_gap,
            "triggered_evolution": bool(batch.triggered_evolution),
            "triggered_critic_calibration": need_calibration,
            "derived_rules_count": len(derived_rules),
        }

    # ========== P2-4: LLM 解析 ==========

    async def _llm_parse_feedbacks(self, project_id: int, feedbacks: List[Feedback]) -> Optional[dict]:
        payload = [
            {
                "chapter_id": f.chapter_id,
                "reader_score": f.reader_score,
                "reaction": f.reaction,
                "dimension_scores": f.dimension_scores or {},
                "anchor": f.anchor or [],
                "comment": f.raw_text or "",
            }
            for f in feedbacks
        ]
        prompt = (
            "你是小说读者反馈分析器。请把以下真人反馈归纳为可执行的写作/审稿规则。\n\n"
            "要求：\n"
            "1. 不要泛泛总结，要输出可直接注入 Draft / Critic / 总编 的规则。\n"
            "2. 每条规则必须有 role：draft / critic / planner / chief_editor / rewrite。\n"
            "3. 每条规则必须有 priority：1-10。\n"
            "4. 必须引用反馈证据 evidence。\n"
            "5. 如果读者反应是 dropped，要优先提炼避坑规则。\n"
            "6. 如果读者反应是 hooked，要提炼可复用爽点。\n"
            "7. 输出 JSON。\n\n"
            f"反馈列表：\n{json.dumps(payload, ensure_ascii=False)[:4000]}\n\n"
            "输出严格 JSON：\n"
            "{\n"
            '  "derived_rules": [{"role": "draft", "rule": "", "priority": 9, "evidence": [], "applied_from_chapter": null}],\n'
            '  "dimension_summary": {},\n'
            '  "reaction_summary": {}\n'
            "}"
        )
        response = await llm_manager.generate(
            prompt=prompt,
            role="learning",
            temperature=0.4,
            db=self.db,
            request_type="reader_feedback_parse",
            project_id=project_id,
        )
        return self._parse_json(response.get("content", ""))

    def _parse_json(self, content: str) -> Optional[dict]:
        if not content:
            return None
        text = content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None

    def _fallback_parse(self, feedbacks: List[Feedback]) -> dict:
        """LLM 不可用时，从批注与反应粗粒度提炼规则。"""
        rules = []
        applied_from = self._next_chapter_index(feedbacks)
        dropped = [f for f in feedbacks if f.reaction == "dropped"]
        hooked = [f for f in feedbacks if f.reaction == "hooked"]

        anchor_comments = []
        for f in feedbacks:
            for a in (f.anchor or []):
                if a.get("comment"):
                    anchor_comments.append(a["comment"])

        if dropped:
            rules.append({
                "role": "draft", "priority": 9,
                "rule": "多名读者弃书，需强化前段冲突与爽点，减少铺陈与解释性段落。",
                "evidence": anchor_comments[:5],
                "applied_from_chapter": applied_from,
            })
        if hooked:
            rules.append({
                "role": "draft", "priority": 7,
                "rule": "读者对高悬念段落反应积极，应复用强钩子与情绪冲击写法。",
                "evidence": [],
                "applied_from_chapter": applied_from,
            })
        if anchor_comments:
            rules.append({
                "role": "critic", "priority": 7,
                "rule": "重点核查读者批注集中的节奏/人物/钩子问题。",
                "evidence": anchor_comments[:5],
                "applied_from_chapter": applied_from,
            })
        return {
            "derived_rules": rules,
            "dimension_summary": {},
            "reaction_summary": self._reaction_summary(feedbacks),
        }

    def _next_chapter_index(self, feedbacks: List[Feedback]) -> Optional[int]:
        chapter_ids = [f.chapter_id for f in feedbacks if f.chapter_id]
        if not chapter_ids:
            return None
        chapters = self.db.query(Chapter).filter(Chapter.id.in_(chapter_ids)).all()
        if not chapters:
            return None
        return max(c.chapter_index for c in chapters) + 1

    def _avg_system_score(self, feedbacks: List[Feedback]) -> Optional[float]:
        chapter_ids = list({f.chapter_id for f in feedbacks if f.chapter_id})
        if not chapter_ids:
            return None
        chapters = self.db.query(Chapter).filter(
            Chapter.id.in_(chapter_ids),
            Chapter.total_score.isnot(None),
        ).all()
        scores = [c.total_score for c in chapters if c.total_score]
        return round(sum(scores) / len(scores), 2) if scores else None

    def _build_calibration_rule(self, avg_reader, avg_system, critic_gap) -> dict:
        if critic_gap is not None and critic_gap < 0:
            note = "系统自评高于真人，Critic 过于宽松，应收紧追读欲/爽点/钩子评分。"
        else:
            note = "系统自评低于真人，Critic 过于严格，应适度放宽对常规网文节奏的扣分。"
        return {
            "role": "critic", "priority": 10,
            "rule": f"真人({avg_reader})与系统({avg_system})评分偏差 {critic_gap}，需校准：{note}",
            "evidence": [],
            "applied_from_chapter": None,
            "is_calibration": True,
        }

    def _reaction_summary(self, feedbacks: List[Feedback]) -> dict:
        summary = {"hooked": 0, "meh": 0, "dropped": 0}
        for f in feedbacks:
            if f.reaction in summary:
                summary[f.reaction] += 1
        return summary

    async def _trigger_evolution_and_calibration(
        self,
        batch: FeedbackBatch,
        avg_reader: float,
        avg_system: float,
        critic_gap: float,
        derived_rules: list,
    ) -> None:
        """按方案 P4：critic_gap 过大时异步触发 Evolution 校准，不阻塞 Worker。"""
        try:
            orchestrator = EvolutionOrchestrator(self.db)
            result = await orchestrator.trigger_for_role(
                project_id=batch.project_id,
                role="critic",
                reason=f"critic_gap_exceeded:{critic_gap}",
                feedback_batch_id=batch.id,
                trigger_window_days=7,
                min_samples=2,
                candidate_count=2,
                min_improvement=3.0,
                auto_apply=False,
            )
            batch.triggered_evolution = 1 if result.get("status") == "applied" else 0
            self.db.commit()
            await event_bus.publish("evolution.reader_triggered", {
                "project_id": batch.project_id,
                "batch_id": batch.id,
                "role": "critic",
                "critic_gap": critic_gap,
                "run_id": result.get("run_id"),
                "status": result.get("status"),
            })
        except Exception as e:
            logger.warning(f"[ReaderTraining] 触发 Evolution 失败（不影响 Worker）: {e}")
            try:
                batch.triggered_evolution = 0
                batch.error_message = (batch.error_message or "") + f"\nEvolution触发失败: {e}"
                self.db.commit()
            except Exception:
                pass

    # ========== P2-5: 取规则 ==========

    def get_reader_rules_for_prompt(
        self,
        project_id: int,
        role: str,
        chapter_index: Optional[int] = None,
        limit: int = 10,
    ) -> List[dict]:
        batches = self.db.query(FeedbackBatch).filter(
            FeedbackBatch.project_id == project_id,
            FeedbackBatch.status == "processed",
        ).all()

        rules = []
        for batch in batches:
            for r in (batch.derived_rules or []):
                if r.get("role") != role:
                    continue
                applied = r.get("applied_from_chapter")
                if chapter_index is not None and applied is not None and applied > chapter_index:
                    continue
                rules.append({
                    "role": r.get("role"),
                    "rule": r.get("rule", ""),
                    "priority": r.get("priority", 5),
                    "evidence": r.get("evidence", []),
                    "batch_id": batch.id,
                })

        rules.sort(key=lambda x: x.get("priority", 0), reverse=True)
        return rules[:limit]


def format_reader_rules_for_prompt(rules: List[dict], role: str) -> str:
    """把真人规则格式化为 Prompt 片段。"""
    if not rules:
        return ""
    headers = {
        "draft": "## 真人读者训练营规则\n\n以下规则来自真人读者反馈，会影响后续章节写作。必须优先遵守：\n",
        "critic": "## 真人读者校准规则\n\n请用以下真人反馈校准你的审稿标准：\n",
        "planner": "## 真人读者反馈约束\n",
        "chief_editor": "## 真人读者偏好\n\n请把这些偏好转化为本章全局指令：\n",
        "rewrite": "## 真人读者反馈驱动的改稿要求\n\n如果本章存在读者已指出过的问题，必须优先修：\n",
    }
    header = headers.get(role, headers["draft"])
    lines = [header]
    for i, r in enumerate(rules, 1):
        line = f"{i}. 【优先级{r.get('priority', 5)}】{r.get('rule', '')}"
        ev = r.get("evidence") or []
        if ev:
            line += f"\n   - 证据：{'；'.join(map(str, ev[:3]))}"
        lines.append(line)
    return "\n".join(lines)
