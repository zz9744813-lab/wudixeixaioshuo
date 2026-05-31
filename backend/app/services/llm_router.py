"""
LLM Router Service - 多API路由池服务
支持角色路由、负载均衡、故障转移、限流、熔断
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.model_config import ModelProvider
from app.models.provider_route_config import ProviderRouteConfig
from app.services.llm_service import BaseLLMService
from app.services.openai_llm_service import OpenAILLMService
from app.services.secret_service import decrypt_api_key


class LLMRouterAllProvidersFailed(Exception):
    """所有provider都失败的异常"""
    pass


class CircuitBreakerOpen(Exception):
    """熔断器开启异常"""
    pass


class RateLimitExceeded(Exception):
    """限流异常"""
    pass


class LLMRouteResult:
    """LLM路由调用结果"""

    def __init__(
        self,
        content: str,
        provider_id: int,
        provider_name: str,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
        role: str = "",
    ):
        self.content = content
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.model_name = model_name
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.cost = cost
        self.duration_ms = duration_ms
        self.role = role


class LLMRouter:
    """
    LLM路由器
    支持角色路由、优先级、权重轮询、故障转移、限流、熔断
    """

    # 内存中的调用统计（用于限流）
    _call_history: Dict[int, List[datetime]] = {}  # provider_id -> [调用时间列表]
    _token_history: Dict[int, List[Tuple[datetime, int]]] = {}  # provider_id -> [(时间, tokens)]

    def __init__(self, db: Session):
        self.db = db

    async def generate(
        self,
        role: str,
        messages: List[Dict[str, str]],
        task_id: Optional[str] = None,
        preferred_provider_id: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        trace: Optional[Dict[str, Any]] = None,
    ) -> LLMRouteResult:
        """
        根据role选择可用provider并生成响应

        Args:
            role: 角色名称 (planner/draft/critic/continuity/research/meta_prompt)
            messages: 消息列表
            task_id: 任务ID（用于日志）
            preferred_provider_id: 优先使用的provider ID
            max_tokens: 最大token数
            temperature: 温度参数
            trace: 追踪信息

        Returns:
            LLMRouteResult: 调用结果

        Raises:
            LLMRouterAllProvidersFailed: 所有provider都失败
        """
        # 获取该角色的路由配置
        routes = self._get_routes_for_role(role)

        if not routes:
            raise LLMRouterAllProvidersFailed(f"角色 '{role}' 没有配置任何路由")

        # 如果指定了优先provider，将其移到最前面
        if preferred_provider_id:
            routes = self._prioritize_route(routes, preferred_provider_id)

        # 按优先级分组
        routes_by_priority = self._group_by_priority(routes)

        # 尝试调用，按优先级顺序
        last_error = None

        for priority, priority_routes in sorted(routes_by_priority.items()):
            # 同优先级内按权重选择
            route = self._weighted_select(priority_routes)

            if not route or not route.enabled:
                continue

            # 检查熔断器
            if self._is_circuit_open(route):
                continue

            # 检查限流
            if self._is_rate_limited(route):
                continue

            try:
                result = await self._call_provider(
                    route=route,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    role=role,
                )

                # 更新成功统计
                self._update_route_stats(route, success=True, duration_ms=result.duration_ms)

                return result

            except Exception as e:
                last_error = e
                # 更新失败统计
                self._update_route_stats(route, success=False)
                continue

        # 所有provider都失败了
        error_msg = f"所有provider都失败: {str(last_error)}" if last_error else "所有provider都失败"
        raise LLMRouterAllProvidersFailed(error_msg)

    def _get_routes_for_role(self, role: str) -> List[ProviderRouteConfig]:
        """获取指定角色的路由配置"""
        return (
            self.db.query(ProviderRouteConfig)
            .filter(
                ProviderRouteConfig.role == role,
                ProviderRouteConfig.enabled == True
            )
            .order_by(ProviderRouteConfig.priority.asc())
            .all()
        )

    def _prioritize_route(
        self,
        routes: List[ProviderRouteConfig],
        provider_id: int
    ) -> List[ProviderRouteConfig]:
        """排除指定provider，让critic选择不同provider；无其他provider时回退返回全部"""
        filtered = [r for r in routes if r.provider_id != provider_id]
        if filtered:
            return filtered
        return routes  # 回退：无其他provider时用原列表

    def audit_role_coverage(self) -> Dict[str, Any]:
        """审计所有必需角色的路由覆盖情况"""
        import logging
        logger = logging.getLogger(__name__)

        required_roles = {"planner", "draft", "critic", "rewrite", "continuity", "learning"}

        configured_roles = set()
        enabled_count = 0
        try:
            routes = self.db.query(ProviderRouteConfig).all()
            for route in routes:
                if route.enabled:
                    configured_roles.add(route.role)
                    enabled_count += 1
        except Exception as e:
            logger.warning(f"审计路由覆盖失败: {e}")
            return {"error": str(e), "configured": list(configured_roles)}

        missing = sorted(required_roles - configured_roles)
        result = {
            "required_roles": sorted(required_roles),
            "configured_roles": sorted(configured_roles),
            "missing_roles": missing,
            "enabled_routes": enabled_count,
            "ok": len(missing) == 0,
        }

        if missing:
            logger.warning(f"LLM路由覆盖不足，缺少角色: {missing}")
        else:
            logger.info(f"LLM路由覆盖完整 ({len(required_roles)}/{len(required_roles)} 角色已配置)")

        return result



    def _group_by_priority(
        self,
        routes: List[ProviderRouteConfig]
    ) -> Dict[int, List[ProviderRouteConfig]]:
        """按优先级分组"""
        groups: Dict[int, List[ProviderRouteConfig]] = {}
        for route in routes:
            priority = route.priority
            if priority not in groups:
                groups[priority] = []
            groups[priority].append(route)
        return groups

    def _weighted_select(
        self,
        routes: List[ProviderRouteConfig]
    ) -> Optional[ProviderRouteConfig]:
        """按权重随机选择一个路由"""
        if not routes:
            return None

        # 过滤掉熔断的route
        available_routes = [r for r in routes if not self._is_circuit_open(r)]

        if not available_routes:
            # 如果都熔断了，尝试第一个（可能是刚熔断）
            available_routes = routes

        # 按权重选择
        total_weight = sum(r.weight for r in available_routes)
        if total_weight == 0:
            return available_routes[0]

        rand = random.uniform(0, total_weight)
        current_weight = 0

        for route in available_routes:
            current_weight += route.weight
            if rand <= current_weight:
                return route

        return available_routes[-1]

    def _is_circuit_open(self, route: ProviderRouteConfig) -> bool:
        """检查熔断器是否开启"""
        if route.circuit_breaker_opened_at is None:
            return False

        # 检查是否过了冷却时间
        reset_time = route.circuit_breaker_opened_at + timedelta(
            seconds=route.circuit_breaker_reset_seconds
        )

        if datetime.utcnow() >= reset_time:
            # 重置熔断器
            route.circuit_breaker_opened_at = None
            route.consecutive_failures = 0
            self.db.commit()
            return False

        return True

    def _is_rate_limited(self, route: ProviderRouteConfig) -> bool:
        """检查是否超过限流"""
        provider_id = route.provider_id
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)

        # 检查RPM
        if route.rpm_limit:
            calls = self._call_history.get(provider_id, [])
            recent_calls = [t for t in calls if t > one_minute_ago]
            self._call_history[provider_id] = recent_calls

            if len(recent_calls) >= route.rpm_limit:
                return True

        # 检查TPM
        if route.tpm_limit:
            tokens = self._token_history.get(provider_id, [])
            recent_tokens = [(t, n) for t, n in tokens if t > one_minute_ago]
            self._token_history[provider_id] = recent_tokens

            total_tokens = sum(n for _, n in recent_tokens)
            if total_tokens >= route.tpm_limit:
                return True

        return False

    async def _call_provider(
        self,
        route: ProviderRouteConfig,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
        role: str,
    ) -> LLMRouteResult:
        """调用指定的provider"""
        provider = route.provider

        if not provider:
            raise Exception(f"Provider {route.provider_id} 不存在")

        # 解密API Key
        api_key = decrypt_api_key(provider.api_key_encrypted)

        model_name = provider.default_model

        # 创建服务实例
        service = OpenAILLMService(
            base_url=provider.base_url,
            api_key=api_key,
            model_name=model_name,
            timeout=route.timeout_seconds or provider.timeout_seconds or 120,
            retry_times=route.max_retries or provider.retry_times or 2,
            provider_id=provider.id,
            provider_name=provider.name,
        )

        try:
            start_time = time.time()

            # 将messages转换为prompt（简化处理）
            prompt = self._messages_to_prompt(messages)
            system_prompt = self._extract_system_prompt(messages)

            response = await service.generate(
                prompt=prompt,
                model=model_name,
                temperature=temperature or provider.default_temperature or 0.7,
                max_tokens=max_tokens or provider.default_max_tokens or 4000,
                system_prompt=system_prompt,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # 记录调用历史（用于限流）
            self._record_call(route.provider_id, response.get("total_tokens", 0))

            return LLMRouteResult(
                content=response.get("content", ""),
                provider_id=provider.id,
                provider_name=provider.name,
                model_name=response.get("model", provider.default_model),
                input_tokens=response.get("input_tokens", 0),
                output_tokens=response.get("output_tokens", 0),
                total_tokens=response.get("total_tokens", 0),
                cost=response.get("cost", 0.0),
                duration_ms=duration_ms,
                role=role,
            )

        finally:
            await service.close()

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """将消息列表转换为prompt字符串"""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        return "\n\n".join(prompt_parts)

    def _extract_system_prompt(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """提取系统提示词"""
        for msg in messages:
            if msg.get("role") == "system":
                return msg.get("content")
        return None

    def _update_route_stats(
        self,
        route: ProviderRouteConfig,
        success: bool,
        duration_ms: int = 0
    ):
        """更新路由统计信息"""
        route.total_calls += 1

        if success:
            route.success_calls += 1
            route.consecutive_failures = 0

            # 更新平均延迟
            if route.avg_latency_ms is None:
                route.avg_latency_ms = duration_ms
            else:
                # 移动平均
                route.avg_latency_ms = int(
                    (route.avg_latency_ms * (route.total_calls - 1) + duration_ms) / route.total_calls
                )
        else:
            route.failed_calls += 1
            route.consecutive_failures += 1

            # 检查是否需要熔断
            if route.consecutive_failures >= route.circuit_breaker_threshold:
                route.circuit_breaker_opened_at = datetime.utcnow()

        self.db.commit()

    def _record_call(self, provider_id: int, tokens: int):
        """记录调用历史"""
        now = datetime.utcnow()

        if provider_id not in self._call_history:
            self._call_history[provider_id] = []
        self._call_history[provider_id].append(now)

        if provider_id not in self._token_history:
            self._token_history[provider_id] = []
        self._token_history[provider_id].append((now, tokens))

    def get_route_stats(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取路由统计信息"""
        query = self.db.query(ProviderRouteConfig)

        if role:
            query = query.filter(ProviderRouteConfig.role == role)

        routes = query.all()
        stats = []

        for route in routes:
            provider = route.provider
            stats.append({
                "id": route.id,
                "role": route.role,
                "provider_id": route.provider_id,
                "provider_name": provider.name if provider else "Unknown",
                "priority": route.priority,
                "weight": route.weight,
                "enabled": route.enabled,
                "total_calls": route.total_calls,
                "success_calls": route.success_calls,
                "failed_calls": route.failed_calls,
                "success_rate": (
                    route.success_calls / route.total_calls * 100
                    if route.total_calls > 0 else 0
                ),
                "avg_latency_ms": route.avg_latency_ms,
                "consecutive_failures": route.consecutive_failures,
                "is_circuit_open": self._is_circuit_open(route),
            })

        return stats

    def reset_circuit_breaker(self, route_id: int) -> bool:
        """手动重置熔断器"""
        route = (
            self.db.query(ProviderRouteConfig)
            .filter(ProviderRouteConfig.id == route_id)
            .first()
        )

        if route:
            route.circuit_breaker_opened_at = None
            route.consecutive_failures = 0
            self.db.commit()
            return True

        return False


# 全局路由器实例（用于依赖注入）
_llm_router: Optional[LLMRouter] = None


def get_llm_router(db: Session) -> LLMRouter:
    """获取LLMRouter实例"""
    return LLMRouter(db)
