"""
Agent Model Config Service - 模型配置聚合服务 (Phase 1)

职责:
- 聚合 model_roles + provider_route_configs + 24h model_call_logs
- 提供 list_agent_cards / update_binding / routing_preview / auto_assign_all
- 复用现有 LLMRouter 的 priority/weight/circuit-breaker，不重新发明轮子
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models.model_config import ModelCallLog, ModelProvider, ModelRole
from app.models.model_routing_event import ModelRoutingEvent
from app.models.provider_route_config import ProviderRouteConfig
from app.services.openai_llm_service import LLMServiceManager
from app.services.llm_router import LLMRouter, get_llm_router
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


# 角色中文名映射（与 /api/llm-routes/roles/list 保持一致）
ROLE_DESCRIPTIONS = {
    "planner": "规划 Agent",
    "draft": "起草 Agent",
    "critic": "审稿 Agent",
    "rewrite": "改写 Agent",
    "continuity": "连续性检查 Agent",
    "learning": "学习 Agent",
    "study": "学习/分析 Agent",
    "split": "分章 Agent",
    "analyze": "分析 Agent",
    "memory_update": "记忆更新 Agent",
    "memory_retrieval": "记忆检索 Agent",
    "foreshadow": "伏笔管理 Agent",
    "logic_critic": "逻辑评审 Agent",
    "style_critic": "文风评审 Agent",
    "commercial_critic": "商业性评审 Agent",
    "research": "联网研究 Agent",
    "meta_prompt": "Prompt 生成 Agent",
    "default": "默认角色",
}

# 角色默认偏好
ROLE_DEFAULT_QUALITY = {
    "planner": "quality",
    "draft": "balanced",
    "critic": "quality",
    "rewrite": "balanced",
    "continuity": "long_context",
    "learning": "quality",
    "memory_update": "fast",
    "memory_retrieval": "fast",
    "foreshadow": "balanced",
    "logic_critic": "quality",
    "style_critic": "quality",
    "commercial_critic": "balanced",
    "research": "balanced",
    "meta_prompt": "quality",
    "default": "balanced",
}

# Agent 分类
CATEGORY_MAP = {
    "writing": ["planner", "draft", "rewrite"],
    "quality": ["critic", "continuity", "logic_critic", "style_critic", "commercial_critic"],
    "memory": ["learning", "study", "split", "analyze", "memory_update", "memory_retrieval", "foreshadow"],
    "system": ["research", "meta_prompt", "default"],
}

CATEGORY_TITLES = {
    "writing": "写作生产链",
    "quality": "质量评审链",
    "memory": "知识记忆链",
    "system": "系统调度链",
}


class AgentModelConfigService:
    """模型配置聚合服务 - 包装在 LLMRouter 之上"""

    def __init__(self, db: Session):
        self.db = db

    # ---------- 公开 API ----------

    def list_agent_cards(self) -> Dict[str, Any]:
        """列出所有 Agent 卡片数据（含 24h 聚合统计）"""
        roles = LLMServiceManager.SUPPORTED_ROLES
        since = utc_now() - timedelta(hours=24)

        # 一次性查所有路由
        all_routes = self.db.query(ProviderRouteConfig).all()
        routes_by_role: Dict[str, List[ProviderRouteConfig]] = {}
        for r in all_routes:
            routes_by_role.setdefault(r.role, []).append(r)

        # 一次性查 24h 调用统计（按 role 聚合）
        stats_rows = (
            self.db.query(
                ModelCallLog.role,
                func.count(ModelCallLog.id).label("calls"),
                func.coalesce(func.sum(ModelCallLog.input_tokens), 0).label("input_t"),
                func.coalesce(func.sum(ModelCallLog.output_tokens), 0).label("output_t"),
                func.coalesce(func.sum(ModelCallLog.estimated_cost), 0.0).label("cost"),
                func.coalesce(func.sum(ModelCallLog.duration_ms), 0).label("total_ms"),
            )
            .filter(ModelCallLog.created_at >= since)
            .group_by(ModelCallLog.role)
            .all()
        )
        stats_by_role = {row.role: row for row in stats_rows}

        # 一次性查 model_roles（全局配置）
        model_roles = (
            self.db.query(ModelRole)
            .filter(ModelRole.project_id.is_(None))
            .all()
        )
        model_role_by_role = {mr.role: mr for mr in model_roles}

        # 按 category 分组
        groups: List[Dict[str, Any]] = []
        total_auto = 0
        total_manual = 0
        total_agents = 0
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        total_failed = 0
        running_count = 0

        for category, category_roles in CATEGORY_MAP.items():
            agents: List[Dict[str, Any]] = []
            for role in category_roles:
                card = self._build_agent_card(
                    role=role,
                    routes=routes_by_role.get(role, []),
                    model_role=model_role_by_role.get(role),
                    stats=stats_by_role.get(role),
                )
                agents.append(card)
                total_agents += 1
                if card["assignment_mode"] == "manual":
                    total_manual += 1
                else:
                    total_auto += 1
                total_cost += card["today_cost_usd"]
                total_input_tokens += card["today_input_tokens"]
                total_output_tokens += card["today_output_tokens"]
                if card["health"] == "failed":
                    total_failed += 1
                if card["last_run_status"] == "running":
                    running_count += 1

            groups.append({
                "category": category,
                "title": CATEGORY_TITLES.get(category, category),
                "agents": agents,
            })

        # 那些未分类的角色（default 等）
        categorized = {r for cs in CATEGORY_MAP.values() for r in cs}
        leftover = [r for r in roles if r not in categorized]
        if leftover:
            agents = []
            for role in leftover:
                card = self._build_agent_card(
                    role=role,
                    routes=routes_by_role.get(role, []),
                    model_role=model_role_by_role.get(role),
                    stats=stats_by_role.get(role),
                )
                agents.append(card)
                total_agents += 1
                if card["assignment_mode"] == "manual":
                    total_manual += 1
                else:
                    total_auto += 1
                total_cost += card["today_cost_usd"]
            groups.append({
                "category": "other",
                "title": "其他",
                "agents": agents,
            })

        # 顶层 summary
        provider_summary = self._build_provider_summary()
        return {
            "summary": {
                "agent_count": total_agents,
                "auto_count": total_auto,
                "manual_count": total_manual,
                "running_count": running_count,
                "failed_count": total_failed,
                "today_cost_usd": round(total_cost, 4),
                "today_input_tokens": total_input_tokens,
                "today_output_tokens": total_output_tokens,
            },
            "groups": groups,
            "providers": provider_summary,
        }

    def get_agent_card(self, role: str) -> Optional[Dict[str, Any]]:
        """获取单个 Agent 卡片详情（含 routing_preview）"""
        if role not in LLMServiceManager.SUPPORTED_ROLES:
            return None

        routes = (
            self.db.query(ProviderRouteConfig)
            .filter(ProviderRouteConfig.role == role)
            .all()
        )
        model_role = (
            self.db.query(ModelRole)
            .filter(ModelRole.role == role, ModelRole.project_id.is_(None))
            .first()
        )

        since = utc_now() - timedelta(hours=24)
        stats = (
            self.db.query(
                func.count(ModelCallLog.id).label("calls"),
                func.coalesce(func.sum(ModelCallLog.input_tokens), 0).label("input_t"),
                func.coalesce(func.sum(ModelCallLog.output_tokens), 0).label("output_t"),
                func.coalesce(func.sum(ModelCallLog.estimated_cost), 0.0).label("cost"),
                func.coalesce(func.sum(ModelCallLog.duration_ms), 0).label("total_ms"),
            )
            .filter(ModelCallLog.role == role, ModelCallLog.created_at >= since)
            .first()
        )

        card = self._build_agent_card(
            role=role,
            routes=routes,
            model_role=model_role,
            stats=stats,
        )

        # 加上调度预览（候选+分数）
        card["candidates"] = self._build_candidates(role, routes)
        card["recent_runs"] = self._recent_runs(role, limit=10)
        card["recent_routing_events"] = self._recent_routing_events(role, limit=5)

        return card

    def update_binding(self, role: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新某个 Agent 的 binding 配置。

        接受字段:
        - assignment_mode: auto | manual
        - allowed_provider_ids: List[int] (auto 时限制候选)
        - preferred_quality: str
        - max_cost_per_million: float | None
        - require_json: bool
        - min_context_tokens: int | None
        - fallback_enabled: bool
        - updated_by: str (user/system/migration)
        """
        if role not in LLMServiceManager.SUPPORTED_ROLES:
            raise ValueError(f"未知角色: {role}")

        model_role = (
            self.db.query(ModelRole)
            .filter(ModelRole.role == role, ModelRole.project_id.is_(None))
            .first()
        )

        if model_role is None:
            # 创建默认记录（用第一个可用 provider）
            provider = self.db.query(ModelProvider).filter(ModelProvider.is_enabled == 1).first()
            if not provider:
                raise ValueError("没有可用的 provider")
            model_role = ModelRole(
                role=role,
                project_id=None,
                provider_id=provider.id,
                model_name=provider.default_model or "gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=4000,
                priority=1,
            )
            self.db.add(model_role)

        # 写字段（白名单）
        allowed_fields = {
            "assignment_mode",
            "preferred_quality",
            "max_cost_per_million",
            "min_context_tokens",
            "fallback_enabled",
            "require_json",
            "allowed_provider_ids",
            "updated_by",
        }
        for k, v in data.items():
            if k not in allowed_fields:
                continue
            if k == "allowed_provider_ids" and isinstance(v, list):
                v = json.dumps(v)
            if k in ("require_json", "fallback_enabled") and isinstance(v, bool):
                v = 1 if v else 0
            setattr(model_role, k, v)

        # manual 模式下，确保至少有一个 enabled route
        if data.get("assignment_mode") == "manual":
            existing = (
                self.db.query(ProviderRouteConfig)
                .filter(ProviderRouteConfig.role == role, ProviderRouteConfig.enabled == True)
                .count()
            )
            if existing == 0 and model_role.provider_id:
                route = ProviderRouteConfig(
                    provider_id=model_role.provider_id,
                    role=role,
                    priority=100,
                    weight=1,
                    enabled=True,
                    timeout_seconds=60,
                    max_retries=2,
                )
                self.db.add(route)

        self.db.commit()
        self.db.refresh(model_role)
        return self._binding_to_dict(model_role)

    def routing_preview(self, role: str, override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dry-run 路由预览 - 不发请求，只列候选+分数。

        复用 LLMRouter._get_routes_for_role + 评分逻辑（与实际 generate 一致）。
        """
        override = override or {}
        routes = self._get_filtered_routes(role, override)

        candidates = []
        for r in routes:
            score, breakdown = self._score_route(r, role)
            provider = r.provider
            candidates.append({
                "route_id": r.id,
                "provider_id": r.provider_id,
                "provider_name": provider.name if provider else None,
                "provider_type": provider.provider_type if provider else None,
                "model_name": provider.default_model if provider else None,
                "priority": r.priority,
                "weight": r.weight,
                "enabled": r.enabled,
                "is_circuit_open": LLMRouter(self.db)._is_circuit_open(r),
                "score": score,
                "breakdown": breakdown,
                "stats": {
                    "total_calls": r.total_calls,
                    "success_rate": (
                        r.success_calls / r.total_calls * 100
                        if r.total_calls > 0 else 0.0
                    ),
                    "avg_latency_ms": r.avg_latency_ms,
                    "consecutive_failures": r.consecutive_failures,
                },
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[0] if candidates else None

        return {
            "role": role,
            "override": override,
            "selected": (
                {
                    "provider_id": selected["provider_id"],
                    "provider_name": selected["provider_name"],
                    "model_name": selected["model_name"],
                    "score": selected["score"],
                    "reason": self._build_reason(selected, role),
                }
                if selected else None
            ),
            "candidates": candidates,
            "candidate_count": len(candidates),
        }

    def auto_assign_all(self, include_manual: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """对所有 auto 模式的 role 跑一次 routing_preview，把最高分 route 落库。
        include_manual: True 时也覆盖 manual 锁定的（plan §8.4 二次确认语义）。
        dry_run: True 时不落库。
        """
        results = []
        skipped = 0
        updated = 0

        for role in LLMServiceManager.SUPPORTED_ROLES:
            model_role = (
                self.db.query(ModelRole)
                .filter(ModelRole.role == role, ModelRole.project_id.is_(None))
                .first()
            )
            if model_role is None:
                continue
            if model_role.assignment_mode == "manual" and not include_manual:
                skipped += 1
                continue

            preview = self.routing_preview(role, {})
            sel = preview.get("selected")
            if not sel:
                results.append({"role": role, "status": "no_candidate"})
                continue

            if not dry_run:
                # 落库: 把目前 manual 模式下的主 provider 切到 preview 选中的
                model_role.provider_id = sel["provider_id"]
                model_role.updated_by = "system"
                # 同步创建一个 enabled route（如果还没有这个 provider 的）
                exists = (
                    self.db.query(ProviderRouteConfig)
                    .filter(
                        ProviderRouteConfig.role == role,
                        ProviderRouteConfig.provider_id == sel["provider_id"],
                    )
                    .first()
                )
                if not exists:
                    self.db.add(ProviderRouteConfig(
                        role=role,
                        provider_id=sel["provider_id"],
                        priority=100,
                        weight=1,
                        enabled=True,
                        timeout_seconds=60,
                        max_retries=2,
                    ))
                self.db.commit()
                results.append({
                    "role": role,
                    "status": "updated",
                    "selected_provider": sel["provider_name"],
                    "selected_model": sel["model_name"],
                    "score": sel["score"],
                    "reason": sel["reason"],
                })
                updated += 1
            else:
                results.append({
                    "role": role,
                    "status": "would_update",
                    "selected_provider": sel["provider_name"],
                    "selected_model": sel["model_name"],
                    "score": sel["score"],
                    "reason": sel["reason"],
                })

        return {
            "ok": True,
            "dry_run": dry_run,
            "updated": updated,
            "skipped_locked": skipped,
            "results": results,
        }

    def record_routing_decision(
        self,
        *,
        role: str,
        assignment_mode: str,
        selected_provider_id: Optional[int],
        selected_provider_name: Optional[str],
        selected_route_id: Optional[int],
        selected_model_name: Optional[str],
        candidates: List[Dict[str, Any]],
        decision_reason: str,
        score_breakdown: Optional[Dict[str, Any]] = None,
        fallback_used: bool = False,
        fallback_chain: Optional[List[Dict[str, Any]]] = None,
        task_id: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> ModelRoutingEvent:
        """落库一个 routing 决策事件。供其他 service 在调用 LLM 前后调用。"""
        event = ModelRoutingEvent(
            role=role,
            task_id=str(task_id) if task_id else None,
            project_id=project_id,
            assignment_mode=assignment_mode,
            selected_provider_id=selected_provider_id,
            selected_provider_name=selected_provider_name,
            selected_route_id=selected_route_id,
            selected_model_name=selected_model_name,
            decision_reason=decision_reason[:500] if decision_reason else None,
            fallback_used=fallback_used,
        )
        event.set_candidates(candidates)
        if score_breakdown:
            event.set_score_breakdown(score_breakdown)
        if fallback_chain:
            event.set_fallback_chain(fallback_chain)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    # ---------- 内部 ----------

    def _build_agent_card(
        self,
        *,
        role: str,
        routes: List[ProviderRouteConfig],
        model_role: Optional[ModelRole],
        stats: Any,
    ) -> Dict[str, Any]:
        """构造单个 Agent 卡片"""
        # 决定当前生效的 provider/model
        enabled_routes = [r for r in routes if r.enabled]
        primary_route = None
        for r in enabled_routes:
            if not LLMRouter(self.db)._is_circuit_open(r):
                primary_route = r
                break
        if primary_route is None and enabled_routes:
            primary_route = enabled_routes[0]

        provider_name = None
        model_name = None
        provider_id = None
        is_mock = False
        if primary_route and primary_route.provider:
            provider_name = primary_route.provider.name
            provider_id = primary_route.provider_id
            model_name = primary_route.provider.default_model
            base_url = primary_route.provider.base_url or ""
            is_mock = "mock" in (provider_name or "").lower() or "mock" in base_url.lower() or "stub" in base_url.lower()

        # 24h 统计
        today_cost = float(getattr(stats, "cost", 0) or 0)
        input_t = int(getattr(stats, "input_t", 0) or 0)
        output_t = int(getattr(stats, "output_t", 0) or 0)
        total_ms = int(getattr(stats, "total_ms", 0) or 0)
        calls = int(getattr(stats, "calls", 0) or 0)
        avg_latency = int(total_ms / calls) if calls > 0 else None

        # 健康
        health = "healthy"
        if primary_route is None:
            health = "unconfigured"
        elif primary_route and LLMRouter(self.db)._is_circuit_open(primary_route):
            health = "failed"
        elif primary_route and (primary_route.consecutive_failures or 0) > 0:
            health = "warning"

        # 最近一次运行状态
        last = (
            self.db.query(ModelCallLog)
            .filter(ModelCallLog.role == role)
            .order_by(desc(ModelCallLog.created_at))
            .first()
        )
        last_run_status = last.status if last else None

        # 调度理由
        reason = self._build_role_reason(role, primary_route, enabled_routes)

        return {
            "agent_key": role,
            "name": ROLE_DESCRIPTIONS.get(role, role),
            "role": role,
            "category": self._role_category(role),
            "assignment_mode": (model_role.assignment_mode if model_role and model_role.assignment_mode else "auto"),
            "provider_id": provider_id,
            "provider_name": provider_name or "未配置",
            "model_name": model_name or "未选择",
            "is_mock": is_mock,
            "status": "configured" if primary_route else "unconfigured",
            "health": health,
            "last_run_status": last_run_status,
            "last_run_at": last.created_at.isoformat() if last else None,
            "today_cost_usd": round(today_cost, 4),
            "today_input_tokens": input_t,
            "today_output_tokens": output_t,
            "avg_latency_ms": avg_latency,
            "calls_24h": calls,
            "fallback_enabled": (model_role.fallback_enabled if model_role and model_role.fallback_enabled is not None else 1) == 1,
            "preferred_quality": (model_role.preferred_quality if model_role and model_role.preferred_quality else ROLE_DEFAULT_QUALITY.get(role, "balanced")),
            "decision_reason": reason,
            "enabled_route_count": len(enabled_routes),
            "total_route_count": len(routes),
        }

    def _role_category(self, role: str) -> str:
        for cat, roles in CATEGORY_MAP.items():
            if role in roles:
                return cat
        return "other"

    def _build_provider_summary(self) -> List[Dict[str, Any]]:
        """Provider 池摘要 - 给页面顶部统计用"""
        providers = self.db.query(ModelProvider).all()
        result = []
        for p in providers:
            routes = (
                self.db.query(ProviderRouteConfig)
                .filter(ProviderRouteConfig.provider_id == p.id)
                .all()
            )
            total_calls = sum(r.total_calls for r in routes)
            success_calls = sum(r.success_calls for r in routes)
            avg_latency = None
            latencies = [r.avg_latency_ms for r in routes if r.avg_latency_ms]
            if latencies:
                avg_latency = int(sum(latencies) / len(latencies))
            enabled_routes = sum(1 for r in routes if r.enabled)
            is_circuit_open = any(
                LLMRouter(self.db)._is_circuit_open(r) for r in routes if r.enabled
            )
            health = "healthy"
            if p.is_enabled != 1:
                health = "disabled"
            elif is_circuit_open:
                health = "failed"
            elif any((r.consecutive_failures or 0) > 0 for r in routes if r.enabled):
                health = "warning"
            result.append({
                "id": p.id,
                "name": p.name,
                "provider_type": p.provider_type,
                "is_enabled": p.is_enabled == 1,
                "is_default": p.is_default == 1,
                "api_key_mask": p.api_key_mask,
                "status": health,
                "model_count": 1,  # 简化：当前每个 provider 一个 default_model
                "default_model": p.default_model,
                "avg_latency_ms": avg_latency,
                "enabled_route_count": enabled_routes,
                "total_calls": total_calls,
                "success_rate": (
                    success_calls / total_calls * 100 if total_calls > 0 else None
                ),
            })
        return result

    def _build_candidates(self, role: str, routes: List[ProviderRouteConfig]) -> List[Dict[str, Any]]:
        """构造候选列表（用于详情页）"""
        out = []
        for r in routes:
            score, breakdown = self._score_route(r, role)
            provider = r.provider
            out.append({
                "route_id": r.id,
                "provider_id": r.provider_id,
                "provider_name": provider.name if provider else None,
                "model_name": provider.default_model if provider else None,
                "priority": r.priority,
                "weight": r.weight,
                "enabled": r.enabled,
                "is_circuit_open": LLMRouter(self.db)._is_circuit_open(r),
                "score": score,
                "breakdown": breakdown,
                "stats": {
                    "total_calls": r.total_calls,
                    "success_calls": r.success_calls,
                    "failed_calls": r.failed_calls,
                    "success_rate": (
                        r.success_calls / r.total_calls * 100
                        if r.total_calls > 0 else 0.0
                    ),
                    "avg_latency_ms": r.avg_latency_ms,
                    "consecutive_failures": r.consecutive_failures,
                },
            })
        out.sort(key=lambda x: x["score"], reverse=True)
        return out

    def _get_filtered_routes(self, role: str, override: Dict[str, Any]) -> List[ProviderRouteConfig]:
        """根据 override 过滤路由"""
        q = self.db.query(ProviderRouteConfig).filter(ProviderRouteConfig.role == role)
        routes = q.all()
        allowed = override.get("allowed_provider_ids")
        if allowed and isinstance(allowed, list):
            routes = [r for r in routes if r.provider_id in allowed]
        # 优先只取 enabled
        return [r for r in routes if r.enabled]

    def _score_route(self, route: ProviderRouteConfig, role: str) -> Tuple[int, Dict[str, Any]]:
        """评分 0-100: 复用 priority/weight/cost/latency/circuit-breaker 信息。

        与 plan §4.6 不同，这里用 priority（越小越高）和 success_rate 作主因子，
        不再另外发明 capability_fit 等维度（数据不够）。
        """
        breakdown: Dict[str, Any] = {}
        score = 0

        # 1. priority (权重 40) - 越小越好
        priority = route.priority or 100
        if priority <= 10:
            breakdown["priority"] = 40
        elif priority <= 50:
            breakdown["priority"] = 30
        elif priority <= 100:
            breakdown["priority"] = 20
        else:
            breakdown["priority"] = 10
        score += breakdown["priority"]

        # 2. 健康 (权重 30)
        if LLMRouter(self.db)._is_circuit_open(route):
            breakdown["health"] = 0
            score += 0
        else:
            total = route.total_calls
            if total > 0:
                sr = route.success_calls / total
                h = int(sr * 30)
                breakdown["health"] = h
                score += h
                # 连续失败惩罚
                if (route.consecutive_failures or 0) >= 3:
                    breakdown["consecutive_penalty"] = -10
                    score -= 10
            else:
                breakdown["health"] = 25  # 新 route 默认可信
                score += 25

        # 3. 延迟 (权重 15) - 越快越高
        if route.avg_latency_ms:
            if route.avg_latency_ms < 1000:
                breakdown["latency"] = 15
            elif route.avg_latency_ms < 3000:
                breakdown["latency"] = 10
            elif route.avg_latency_ms < 8000:
                breakdown["latency"] = 5
            else:
                breakdown["latency"] = 0
            score += breakdown["latency"]

        # 4. 角色质量偏好 (权重 15)
        preferred = ROLE_DEFAULT_QUALITY.get(role, "balanced")
        breakdown["role_preference"] = 10  # 简化: 暂都给中性分
        score += 10

        # 5. mock 惩罚
        provider = route.provider
        if provider and (
            "mock" in (provider.name or "").lower()
            or "mock" in (provider.base_url or "").lower()
            or "stub" in (provider.base_url or "").lower()
        ):
            breakdown["mock_penalty"] = -50
            score -= 50

        breakdown["total"] = score
        return max(0, min(100, score)), breakdown

    def _build_reason(self, candidate: Dict[str, Any], role: str) -> str:
        """构造人类可读的调度理由"""
        parts = []
        breakdown = candidate.get("breakdown", {})
        priority = candidate.get("priority", 100)
        parts.append(f"优先级 {priority}")
        sr = candidate["stats"].get("success_rate", 0)
        if sr > 0:
            parts.append(f"成功率 {sr:.0f}%")
        if candidate["stats"].get("avg_latency_ms"):
            parts.append(f"延迟 {candidate['stats']['avg_latency_ms']}ms")
        if breakdown.get("mock_penalty"):
            parts.append("[警告] Mock 模型")
        return " · ".join(parts)

    def _build_role_reason(
        self,
        role: str,
        primary_route: Optional[ProviderRouteConfig],
        enabled_routes: List[ProviderRouteConfig],
    ) -> str:
        if primary_route is None:
            return "未配置路由，请先在 /llm-routes 添加"
        if LLMRouter(self.db)._is_circuit_open(primary_route):
            return f"主 Provider 熔断中（{primary_route.consecutive_failures or 0} 次连续失败）"
        if not enabled_routes:
            return "已禁用所有路由"
        if primary_route.total_calls > 0:
            sr = primary_route.success_calls / primary_route.total_calls * 100
            return f"自动选择：优先级 {primary_route.priority}，成功率 {sr:.0f}%"
        return f"自动选择：优先级 {primary_route.priority}（无历史数据）"

    def _binding_to_dict(self, model_role: ModelRole) -> Dict[str, Any]:
        return {
            "role": model_role.role,
            "assignment_mode": model_role.assignment_mode or "auto",
            "provider_id": model_role.provider_id,
            "model_name": model_role.model_name,
            "temperature": model_role.temperature,
            "max_tokens": model_role.max_tokens,
            "allowed_provider_ids": json.loads(model_role.allowed_provider_ids) if model_role.allowed_provider_ids else None,
            "preferred_quality": model_role.preferred_quality or ROLE_DEFAULT_QUALITY.get(model_role.role, "balanced"),
            "max_cost_per_million": model_role.max_cost_per_million,
            "min_context_tokens": model_role.min_context_tokens,
            "require_json": bool(model_role.require_json),
            "fallback_enabled": bool(model_role.fallback_enabled),
            "updated_by": model_role.updated_by or "system",
            "updated_at": model_role.updated_at.isoformat() if model_role.updated_at else None,
        }

    def _recent_runs(self, role: str, limit: int = 10) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(ModelCallLog)
            .filter(ModelCallLog.role == role)
            .order_by(desc(ModelCallLog.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "provider_id": r.provider_id,
                "model_name": r.model_name,
                "status": r.status,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0,
                "estimated_cost": r.estimated_cost or 0.0,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
                "routing_event_id": r.routing_event_id,
            }
            for r in rows
        ]

    def _recent_routing_events(self, role: str, limit: int = 5) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(ModelRoutingEvent)
            .filter(ModelRoutingEvent.role == role)
            .order_by(desc(ModelRoutingEvent.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "assignment_mode": r.assignment_mode,
                "selected_provider_name": r.selected_provider_name,
                "selected_model_name": r.selected_model_name,
                "decision_reason": r.decision_reason,
                "fallback_used": r.fallback_used,
                "candidates": r.get_candidates(),
                "score_breakdown": r.get_score_breakdown(),
            }
            for r in rows
        ]
