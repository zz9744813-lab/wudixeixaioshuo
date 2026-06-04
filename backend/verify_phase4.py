"""
Phase 4 端到端验证脚本
Seed: 2 providers (primary + fallback) + 2 routes (primary priority 10, fallback priority 20)
验证:
  T1: 主 provider 抛异常 → 备用 provider 接管 (routing event 记录 fallback_used=true)
  T2: 主 provider 累计 5 次失败 → 触发熔断 → 下次直接跳过
  T3: 熔断后回退时间到 5 分钟前 → 路由自动重置 circuit
"""
import sys
sys.path.insert(0, 'F:/kelaode/quanzidong/backend')

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.database import SessionLocal, init_db
from app.models.model_config import ModelProvider, ModelRole
from app.models.provider_route_config import ProviderRouteConfig
from app.models.model_routing_event import ModelRoutingEvent
from app.services.llm_router import LLMRouter, LLMRouteResult

init_db()

db = SessionLocal()
try:
    # Providers
    primary = db.query(ModelProvider).filter(ModelProvider.name == "phase4-primary").first()
    if not primary:
        primary = ModelProvider(
            name="phase4-primary",
            provider_type="openai",
            base_url="http://localhost:11452/v1",
            api_key_encrypted="gAAAAA_phase4key1",
            api_key_mask="****hase4",
            default_model="phase4-model-v1",
            is_enabled=1,
            status="healthy",
        )
        db.add(primary)
        db.commit()
        db.refresh(primary)
        print(f"[seed] created phase4-primary id={primary.id}")

    fallback = db.query(ModelProvider).filter(ModelProvider.name == "phase4-fallback").first()
    if not fallback:
        fallback = ModelProvider(
            name="phase4-fallback",
            provider_type="stub",
            base_url="http://localhost:9998/mock/v1",
            api_key_encrypted=None,
            default_model="phase4-mock",
            is_enabled=1,
            status="healthy",
        )
        db.add(fallback)
        db.commit()
        db.refresh(fallback)
        print(f"[seed] created phase4-fallback id={fallback.id}")

    # Routes for critic (低频调用, 用作 Phase 4 独立轨道)
    existing = (
        db.query(ProviderRouteConfig)
        .filter(ProviderRouteConfig.role == "critic")
        .count()
    )
    if existing == 0:
        r1 = ProviderRouteConfig(
            provider_id=primary.id,
            role="critic",
            priority=10,
            weight=1,
            enabled=True,
            timeout_seconds=60,
            max_retries=0,  # Phase 4 测试时不重试, 快速失败
            circuit_breaker_threshold=5,
            circuit_breaker_reset_seconds=300,
        )
        db.add(r1)
        r2 = ProviderRouteConfig(
            provider_id=fallback.id,
            role="critic",
            priority=20,
            weight=1,
            enabled=True,
            timeout_seconds=30,
            max_retries=0,
        )
        db.add(r2)
        db.commit()
        print(f"[seed] created 2 critic routes (primary=priority 10, fallback=priority 20)")
    else:
        print(f"[seed] critic routes already exist ({existing})")

    # model_role critic (auto 模式, 不锁)
    mr = (
        db.query(ModelRole)
        .filter(ModelRole.role == "critic", ModelRole.project_id.is_(None))
        .first()
    )
    if not mr:
        mr = ModelRole(
            role="critic",
            project_id=None,
            provider_id=primary.id,
            model_name="phase4-model-v1",
            assignment_mode="auto",
            fallback_enabled=1,
        )
        db.add(mr)
        db.commit()
        print(f"[seed] created model_role critic (auto, fallback=1)")
    else:
        print(f"[seed] model_role critic exists")
finally:
    db.close()


def reset_critic_state(db):
    """每次测试前重置 critic 路由状态"""
    db.query(ProviderRouteConfig).filter(
        ProviderRouteConfig.role == "critic"
    ).update({
        "consecutive_failures": 0,
        "circuit_breaker_opened_at": None,
        "total_calls": 0,
        "success_calls": 0,
        "failed_calls": 0,
    })
    db.commit()


async def t1_fallback_chain():
    """T1: 主 provider 抛异常 → 备用 provider 接管"""
    db = SessionLocal()
    try:
        reset_critic_state(db)
        router = LLMRouter(db)
        primary_id = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == "critic", ProviderRouteConfig.priority == 10
        ).first().provider_id
        fallback_id = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == "critic", ProviderRouteConfig.priority == 20
        ).first().provider_id

        async def fake_call(route, **kwargs):
            if route.provider_id == primary_id:
                raise ConnectionError("[mock] primary down")
            return LLMRouteResult(
                content=f"[MOCK from {route.provider.name}]",
                provider_id=route.provider_id,
                provider_name=route.provider.name,
                model_name=route.provider.default_model,
                role="critic",
                duration_ms=80,
            )

        with patch.object(router, "_call_provider", side_effect=fake_call):
            result = await router.generate(
                role="critic",
                messages=[{"role": "user", "content": "test"}],
                task_id="phase4-T1-fallback",
                project_id=1,
                record_routing_event=True,
            )

        ev = (
            db.query(ModelRoutingEvent)
            .filter(ModelRoutingEvent.task_id == "phase4-T1-fallback")
            .order_by(ModelRoutingEvent.id.desc())
            .first()
        )
        fb_chain = ev.get_fallback_chain() if ev else None
        ok = (
            result.provider_name == "phase4-fallback"
            and ev is not None
            and ev.fallback_used is True
            and ev.assignment_mode == "auto"
            and fb_chain is not None
            and len(fb_chain) == 1
            and fb_chain[0]["provider_id"] == primary_id
            and "primary down" in fb_chain[0]["error"]
        )
        mark = "✓" if ok else "✗"
        print(f"[T1] {mark} primary failed → fallback '{result.provider_name}', "
              f"event.fallback_used={ev.fallback_used if ev else 'N/A'}, "
              f"chain_len={len(fb_chain) if fb_chain else 0}")
        if not ok and ev:
            print(f"   reason: {ev.decision_reason}")
            print(f"   chain: {fb_chain}")
        return ok
    finally:
        db.close()


async def t2_circuit_breaker_triggers():
    """T2: 主 provider 累计 5 次失败 → 触发熔断 → 下次直接跳过"""
    db = SessionLocal()
    try:
        reset_critic_state(db)
        router = LLMRouter(db)
        primary_route = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == "critic", ProviderRouteConfig.priority == 10
        ).first()
        primary_id = primary_route.provider_id
        fallback_id = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == "critic", ProviderRouteConfig.priority == 20
        ).first().provider_id

        call_log = []

        async def fake_call(route, **kwargs):
            call_log.append(route.provider_id)
            if route.provider_id == primary_id:
                raise ConnectionError("[mock] primary keeps failing")
            return LLMRouteResult(
                content=f"[MOCK from {route.provider.name}]",
                provider_id=route.provider_id,
                provider_name=route.provider.name,
                model_name=route.provider.default_model,
                role="critic",
                duration_ms=80,
            )

        with patch.object(router, "_call_provider", side_effect=fake_call):
            # 连续 5 次调用, 每次 primary 都失败, 触发熔断
            for i in range(5):
                await router.generate(
                    role="critic",
                    messages=[{"role": "user", "content": f"call-{i}"}],
                    task_id=f"phase4-T2-trigger-{i}",
                    project_id=1,
                    record_routing_event=True,
                )

        # 重新拉 primary route 状态
        db.refresh(primary_route)
        circuit_open = primary_route.circuit_breaker_opened_at is not None
        consec_fail = primary_route.consecutive_failures

        # 第 6 次调用: primary 应被跳过, 直接走 fallback
        call_log.clear()
        with patch.object(router, "_call_provider", side_effect=fake_call):
            result6 = await router.generate(
                role="critic",
                messages=[{"role": "user", "content": "call-6"}],
                task_id="phase4-T2-skip",
                project_id=1,
                record_routing_event=True,
            )

        # 检查: 熔断器已开 + 第 6 次只调了 fallback 一次
        primary_called_in_6th = primary_id in call_log
        ok = (
            circuit_open
            and consec_fail >= 5
            and result6.provider_name == "phase4-fallback"
            and not primary_called_in_6th
            and len(call_log) == 1
        )
        mark = "✓" if ok else "✗"
        print(f"[T2] {mark} circuit_open={circuit_open}, "
              f"consec_failures={consec_fail}, "
              f"6th_call: primary_called={primary_called_in_6th}, "
              f"result={result6.provider_name}")
        return ok
    finally:
        db.close()


async def t3_circuit_reset():
    """T3: 熔断后, 把 opened_at 调到 5 分钟前 → 下次调用自动重置"""
    db = SessionLocal()
    try:
        reset_critic_state(db)
        router = LLMRouter(db)
        primary_route = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == "critic", ProviderRouteConfig.priority == 10
        ).first()
        primary_id = primary_route.provider_id
        fallback_id = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == "critic", ProviderRouteConfig.priority == 20
        ).first().provider_id

        # 手动开熔断
        primary_route.consecutive_failures = 5
        primary_route.circuit_breaker_opened_at = datetime.utcnow() - timedelta(seconds=400)  # 400s 前, 超过 300s 冷却
        db.commit()
        db.refresh(primary_route)

        # 调一次, 期望 primary 重置并能正常调用
        async def fake_call_success(route, **kwargs):
            return LLMRouteResult(
                content=f"[MOCK from {route.provider.name}]",
                provider_id=route.provider_id,
                provider_name=route.provider.name,
                model_name=route.provider.default_model,
                role="critic",
                duration_ms=50,
            )

        with patch.object(router, "_call_provider", side_effect=fake_call_success):
            result = await router.generate(
                role="critic",
                messages=[{"role": "user", "content": "test"}],
                task_id="phase4-T3-reset",
                project_id=1,
                record_routing_event=True,
            )

        # 验证: primary 重新被调用 + circuit_opened_at 被清空
        db.refresh(primary_route)
        ok = (
            result.provider_name == "phase4-primary"
            and primary_route.circuit_breaker_opened_at is None
            and primary_route.consecutive_failures == 0
        )
        mark = "✓" if ok else "✗"
        print(f"[T3] {mark} after-cooldown: routed to {result.provider_name}, "
              f"circuit_opened_at={primary_route.circuit_breaker_opened_at}, "
              f"consec_failures={primary_route.consecutive_failures}")
        return ok
    finally:
        db.close()


async def main():
    print()
    print("=" * 60)
    print("Phase 4 端到端测试: circuit-breaker + fallback 链路")
    print("=" * 60)
    results = []
    results.append(await t1_fallback_chain())
    results.append(await t2_circuit_breaker_triggers())
    results.append(await t3_circuit_reset())

    print()
    print("=" * 60)
    if all(results):
        print("Phase 4 全部测试通过 ✓")
    else:
        print(f"Phase 4 部分测试失败: {sum(results)}/{len(results)} 通过")
    print("=" * 60)


asyncio.run(main())
