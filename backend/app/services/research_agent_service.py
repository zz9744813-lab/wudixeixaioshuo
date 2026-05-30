"""Research Agent Service - 联网研究 Agent 服务。"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.research import (
    KnowledgePattern,
    ReaderInsight,
    ResearchRun,
    ResearchRunStatus,
    ResearchSource,
    TrendReport,
)
from app.services.knowledge_service import KnowledgeService
from app.services.llm_router import LLMRouter, LLMRouterAllProvidersFailed
from app.services.web_extract_service import WebExtractService
from app.services.web_search_service import WebSearchService
from app.utils.time_utils import utc_now

# 研究类型映射
RESEARCH_TYPE_NAMES = {
    "pattern": "套路模式",
    "comment": "读者评论",
    "trend": "市场趋势",
    "style": "作者风格",
}


class ResearchAgentService:
    """联网研究 Agent：搜索 → 抓取 → LLM 抽取 → 知识沉淀。"""

    def __init__(self, db: Session):
        self.db = db
        self.search_service = WebSearchService()
        self.extract_service = WebExtractService()
        self.knowledge_service = KnowledgeService(db)

    async def run_research(
        self,
        topic: str,
        research_type: str = "pattern",
        project_id: Optional[int] = None,
        run_id: Optional[int] = None,
    ) -> ResearchRun:
        """执行一次联网研究。"""
        run = ResearchRun(
            topic=topic,
            research_type=research_type,
            project_id=project_id,
            run_id=run_id,
            status=ResearchRunStatus.RUNNING,
            created_at=utc_now(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            # 1. 生成搜索词
            queries = self._build_queries(topic, research_type)
            run.query_plan_json = {"queries": queries}
            self.db.commit()

            # 2. 搜索
            all_results = []
            for q in queries:
                try:
                    results = await self.search_service.search(q, limit=5)
                    all_results.extend(results)
                except RuntimeError:
                    # 无搜索 API 配置时记录错误并继续
                    run.error_message = "未配置联网搜索 API，使用本地分析模式"
                    break

            # 3. 抓取页面并保存来源
            sources = []
            for sr in all_results[:20]:
                extracted = await self.extract_service.extract(sr.url)
                source = ResearchSource(
                    research_run_id=run.id,
                    title=sr.title or extracted.title,
                    url=sr.url,
                    source_type=sr.source_type,
                    trust_score=sr.trust_score,
                    extracted_text_hash=extracted.text_hash,
                    excerpt=extracted.excerpt or sr.snippet,
                    used_for=research_type,
                )
                self.db.add(source)
                sources.append(source)
            self.db.commit()

            # 4. LLM 抽取结构化知识
            extracted_knowledge = await self._extract_knowledge(
                topic=topic,
                research_type=research_type,
                sources=sources,
            )

            # 5. 入库
            source_ids = [s.id for s in sources]
            saved_count = await self._save_knowledge(
                research_type=research_type,
                extracted_knowledge=extracted_knowledge,
                source_ids=source_ids,
                genre=topic,
            )

            # 6. 生成研究报告
            summary = self._build_summary(research_type, sources, extracted_knowledge, saved_count)
            run.extracted_summary = summary
            run.result_json = {
                "sources_count": len(sources),
                "knowledge_saved": saved_count,
                "extracted": extracted_knowledge,
            }
            run.status = ResearchRunStatus.SUCCEEDED
            run.finished_at = utc_now()
            self.db.commit()

        except Exception as exc:
            run.status = ResearchRunStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = utc_now()
            self.db.commit()

        return run

    def _build_queries(self, topic: str, research_type: str) -> List[str]:
        """根据主题和类型生成搜索词。"""
        base = topic
        type_suffixes = {
            "pattern": ["套路分析", "写作技巧", "开篇钩子"],
            "comment": ["读者评论", "书评", "追读体验"],
            "trend": ["排行榜", "趋势分析", "热度排名"],
            "style": ["作者风格", "文风分析", "叙事技巧"],
        }
        suffixes = type_suffixes.get(research_type, ["分析"])
        return [f"{base} {s}" for s in suffixes]

    async def _extract_knowledge(
        self,
        topic: str,
        research_type: str,
        sources: List[ResearchSource],
    ) -> Dict[str, Any]:
        """用 LLM 从来源中抽取结构化知识。"""
        excerpts = "\n".join(
            f"- [{s.title}]({s.url}): {s.excerpt[:200]}" for s in sources[:10] if s.excerpt
        )
        if not excerpts:
            return self._fallback_extract(research_type, topic)

        type_name = RESEARCH_TYPE_NAMES.get(research_type, "研究")
        system_prompt = (
            "你是小说创作研究助手。根据公开来源总结方法论和模式。"
            "禁止复刻原文、禁止输出大段受版权文本、只能总结方法论和模式。"
            "输出严格 JSON。"
        )
        user_prompt = (
            f"研究主题：{topic}\n"
            f"研究类型：{type_name}\n"
            f"来源摘录：\n{excerpts}\n\n"
            f"请从中抽取结构化的 {type_name} 知识，输出 JSON。"
        )

        try:
            result = await LLMRouter(self.db).generate(
                role="research",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2000,
                temperature=0.3,
                trace={"component": "research_agent", "research_type": research_type},
            )
            return self._parse_json(result.content)
        except (LLMRouterAllProvidersFailed, Exception):
            return self._fallback_extract(research_type, topic)

    def _fallback_extract(self, research_type: str, topic: str) -> Dict[str, Any]:
        """无 LLM 时的兜底抽取。"""
        if research_type == "pattern":
            return {
                "patterns": [
                    {
                        "pattern_name": f"{topic}基础模式",
                        "pattern_type": "hook",
                        "genre": topic,
                        "description": f"基于公开来源分析的{topic}写作模式总结。",
                        "confidence": 0.3,
                    }
                ]
            }
        elif research_type == "comment":
            return {
                "reader_insights": [
                    {
                        "insight_type": "like",
                        "title": f"{topic}读者偏好分析",
                        "description": f"基于公开评论归纳的{topic}读者偏好。",
                        "confidence": 0.3,
                    }
                ]
            }
        elif research_type == "trend":
            return {
                "trend_report": {
                    "genre": topic,
                    "platform": "综合",
                    "report_title": f"{topic}趋势简报",
                    "report_body": f"基于公开来源的{topic}市场趋势分析。",
                    "trend_tags": [],
                }
            }
        else:
            return {"summary": f"{topic}风格分析（无 LLM 兜底）"}

    async def _save_knowledge(
        self,
        research_type: str,
        extracted_knowledge: Dict[str, Any],
        source_ids: List[int],
        genre: str,
    ) -> int:
        """将抽取的知识入库。"""
        count = 0
        if research_type == "pattern":
            patterns = extracted_knowledge.get("patterns", [])
            for p in patterns:
                p.setdefault("genre", genre)
            saved = await self.knowledge_service.save_patterns(patterns, source_ids)
            count = len(saved)
        elif research_type == "comment":
            insights = extracted_knowledge.get("reader_insights", [])
            for i in insights:
                i.setdefault("genre", genre)
            saved = await self.knowledge_service.save_reader_insights(insights, source_ids)
            count = len(saved)
        elif research_type == "trend":
            report = extracted_knowledge.get("trend_report", {})
            if report:
                report.setdefault("genre", genre)
                await self.knowledge_service.save_trend_report(report, source_ids)
                count = 1
        return count

    def _build_summary(
        self,
        research_type: str,
        sources: List[ResearchSource],
        extracted: Dict[str, Any],
        saved_count: int,
    ) -> str:
        """构建研究摘要。"""
        type_name = RESEARCH_TYPE_NAMES.get(research_type, "研究")
        return (
            f"【{type_name}报告】\n"
            f"搜索来源：{len(sources)} 个\n"
            f"知识入库：{saved_count} 条\n"
            f"数据来源涵盖公开搜索结果、文章、评论等。"
        )

    def _parse_json(self, content: str) -> Dict[str, Any]:
        """从 LLM 输出中解析 JSON。"""
        text = (content or "").strip()
        if text.startswith("```"):
            lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            return {"raw": text[:2000]}

    def apply_to_project(
        self,
        knowledge_type: str,
        knowledge_ids: List[int],
        project_id: int,
        apply_to_bible: bool = True,
        apply_to_critic: bool = False,
        apply_to_prompt: bool = False,
    ) -> Dict[str, Any]:
        """将研究知识应用到项目。"""
        from app.models.project import Project

        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        applied = []
        if knowledge_type == "pattern":
            items = self.db.query(KnowledgePattern).filter(KnowledgePattern.id.in_(knowledge_ids)).all()
            if apply_to_bible and project.bible:
                existing = project.bible.knowledge_patterns or []
                project.bible.knowledge_patterns = existing + [
                    {"id": p.id, "name": p.pattern_name, "type": p.pattern_type}
                    for p in items
                ]
            applied = [{"id": i.id, "name": i.pattern_name} for i in items]
        elif knowledge_type == "insight":
            items = self.db.query(ReaderInsight).filter(ReaderInsight.id.in_(knowledge_ids)).all()
            applied = [{"id": i.id, "title": i.title} for i in items]
        elif knowledge_type == "trend":
            items = self.db.query(TrendReport).filter(TrendReport.id.in_(knowledge_ids)).all()
            applied = [{"id": i.id, "title": i.report_title} for i in items]

        self.db.commit()
        return {
            "project_id": project_id,
            "knowledge_type": knowledge_type,
            "applied_count": len(applied),
            "applied": applied,
            "apply_to_bible": apply_to_bible,
            "apply_to_critic": apply_to_critic,
            "apply_to_prompt": apply_to_prompt,
        }
