"""
Phase 3 端到端验证脚本
Seed: 2 providers (test + mock) + 2 routes + 1 model_role (auto 模式)
验证: LLMRouter manual 锁强制 + 真实 routing event assignment_mode 透传
"""
import sys
sys.path.insert(0, 'F:/kelaode/quanzidong/backend')

import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from app.database import SessionLocal, init_db
from app.models.model_config import ModelProvider, ModelRole
from app.models.provider_route_config import ProviderRouteConfig
from app.models.model_routing_event import ModelRoutingEvent
from app.services.llm_router import LLMRouter, LLMRouteResult

init_db()

db = SessionLocal()
try:
    # Seed providers
    primary = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first()
    if not primary:
        primary = ModelProvider(
            name="test-provider",
            provider_type="openai",
            base_url="http://localhost:11451/v1",
            api_key_encrypted="gAAAAA_testkey1234abcd",
            api_key_mask="****1234",
            default_model="test-model-v1",
            is_enabled=1,
            status="healthy",
        )
        db.add(primary)
        db.commit()
        db.refresh(primary)
        print(f"[seed] created primary provider id={primary.id}")

    mock_p = db.query(ModelProvider).filter(ModelProvider.name == "mock-provider").first()
    if not mock_p:
        mock_p = ModelProvider(
            name="mock-provider",
            provider_type="stub",
            base_url="http://localhost:9999/mock/v1",
            api_key_encrypted=None,
            default_model="mock-fast",
            is_enabled=1,
            status="healthy",
        )
        db.add(mock_p)
        db.commit()
        db.refresh(mock_p)
        print(f"[seed] created mock provider id={mock_p.id}")

    # Seed routes for planner
    existing = (
        db.query(ProviderRouteConfig)
        .filter(ProviderRouteConfig.role == "planner")
        .count()
    )
    if existing == 0:
        # high-priority test route (will be used by auto mode)
        r1 = ProviderRouteConfig(
            provider_id=primary.id,
            role="planner",
            priority=10,
            weight=1,
            enabled=True,
            timeout_seconds=60,
            max_retries=2,
        )
        db.add(r1)
        # low-priority mock route (manual lock target)
        r2 = ProviderRouteConfig(
            provider_id=mock_p.id,
            role="planner",
            priority=100,
            weight=1,
            enabled=True,
            timeout_seconds=30,
            max_retries=1,
        )
        db.add(r2)
        db.commit()
        print(f"[seed] created 2 routes for planner (primary=priority 10, mock=priority 100)")
    else:
        print(f"[seed] routes already exist ({existing} for planner)")

    # Ensure model_role exists for planner
    mr = (
        db.query(ModelRole)
        .filter(ModelRole.role == "planner", ModelRole.project_id.is_(None))
        .first()
    )
    if not mr:
        mr = ModelRole(
            role="planner",
            project_id=None,
            provider_id=primary.id,  # 默认锁到 primary
            model_name="test-model-v1",
            assignment_mode="auto",
            fallback_enabled=1,
        )
        db.add(mr)
        db.commit()
        db.refresh(mr)
        print(f"[seed] created model_role for planner (auto mode, lock={primary.name})")
    else:
        print(f"[seed] model_role exists (mode={mr.assignment_mode}, lock={mr.provider_id})")
finally:
    db.close()

print()
print("=" * 60)
print("Phase 3 端到端测试: LLMRouter manual 锁强制")
print("=" * 60)


async def run_test(name, role, expected_provider_name, expected_mode, prep_fn=None):
    """单次路由测试。prep_fn 在调用前对 DB 做额外准备 (如改 model_role.assignment_mode)"""
    db = SessionLocal()
    try:
        if prep_fn:
            prep_fn(db)
        router = LLMRouter(db)

        # Mock _call_provider: 返回假 result, 通过 selected_route.provider.name 反映
        async def fake_call(route, **kwargs):
            return LLMRouteResult(
                content=f"[MOCK from {route.provider.name}]",
                provider_id=route.provider_id,
                provider_name=route.provider.name,
                model_name=route.provider.default_model,
                role=role,
                duration_ms=50,
            )

        with patch.object(router, "_call_provider", side_effect=fake_call):
            result = await router.generate(
                role=role,
                messages=[{"role": "user", "content": "hello"}],
                task_id=f"phase3-test-{name}",
                project_id=1,
                record_routing_event=True,
            )

        # 检查 routing event
        ev = (
            db.query(ModelRoutingEvent)
            .filter(ModelRoutingEvent.task_id == f"phase3-test-{name}")
            .order_by(ModelRoutingEvent.id.desc())
            .first()
        )
        if ev is None:
            print(f"[{name}] ✗ no routing event written")
            return False

        ok = (
            ev.assignment_mode == expected_mode
            and ev.selected_provider_name == expected_provider_name
        )
        mark = "✓" if ok else "✗"
        print(f"[{name}] {mark} routed to {result.provider_name} "
              f"(expected={expected_provider_name}, mode={ev.assignment_mode})")
        if not ok:
            print(f"   reason: {ev.decision_reason}")
        return ok
    finally:
        db.close()


# T1: auto 模式 → 走 priority 10 的 primary
def set_auto(db):
    mr = db.query(ModelRole).filter(ModelRole.role == "planner", ModelRole.project_id.is_(None)).first()
    primary_id = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first().id
    mr.assignment_mode = "auto"
    mr.provider_id = primary_id  # 锁定到 primary (但 auto 模式下不会生效)
    db.commit()


# T2: manual 模式 + lock=mock → 必须用 mock (即使 priority 100 较低)
def set_manual_lock_mock(db):
    mr = db.query(ModelRole).filter(ModelRole.role == "planner", ModelRole.project_id.is_(None)).first()
    mock_id = db.query(ModelProvider).filter(ModelProvider.name == "mock-provider").first().id
    mr.assignment_mode = "manual"
    mr.provider_id = mock_id
    mr.fallback_enabled = 1
    db.commit()


# T3: manual + lock=primary → 必须用 primary (auto 模式下 primary 也是首选, 验证 manual 同样能用 primary)
def set_manual_lock_primary(db):
    mr = db.query(ModelRole).filter(ModelRole.role == "planner", ModelRole.project_id.is_(None)).first()
    primary_id = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first().id
    mr.assignment_mode = "manual"
    mr.provider_id = primary_id
    mr.fallback_enabled = 1
    db.commit()


# T4: manual + 锁定 provider 没 route + fallback 关闭 → 拒绝
def set_manual_lock_missing(db):
    """先 disable 掉 mock route, 再 lock 到 mock, fallback=0"""
    mock_id = db.query(ModelProvider).filter(ModelProvider.name == "mock-provider").first().id
    db.query(ProviderRouteConfig).filter(
        ProviderRouteConfig.role == "planner",
        ProviderRouteConfig.provider_id == mock_id,
    ).update({"enabled": False})
    mr = db.query(ModelRole).filter(ModelRole.role == "planner", ModelRole.project_id.is_(None)).first()
    mr.assignment_mode = "manual"
    mr.provider_id = mock_id
    mr.fallback_enabled = 0
    db.commit()


def restore_planner_routes(db):
    db.query(ProviderRouteConfig).filter(
        ProviderRouteConfig.role == "planner",
        ProviderRouteConfig.provider_id == mock_p.id,
    ).update({"enabled": True})
    db.commit()


async def t4():
    """manual + 锁定的 provider 没 route + fallback=0 → 拒绝"""
    db = SessionLocal()
    try:
        set_manual_lock_missing(db)
        router = LLMRouter(db)

        async def fake_call(*args, **kwargs):
            return LLMRouteResult(content="should not be called", provider_id=0, provider_name="X", model_name="X", role="planner")

        with patch.object(router, "_call_provider", side_effect=fake_call):
            try:
                await router.generate(
                    role="planner",
                    messages=[{"role": "user", "content": "test"}],
                    task_id="phase3-test-T4",
                    project_id=1,
                    record_routing_event=True,
                )
                print("[T4] ✗ 应拒绝但接受了调用")
                ok = False
            except Exception as e:
                msg = str(e)
                if "手动锁定" in msg or "AllProvidersFailed" in type(e).__name__ or "LLMRouterAllProvidersFailed" in type(e).__name__:
                    print(f"[T4] ✓ 正确拒绝: {msg[:80]}")
                    ok = True
                else:
                    print(f"[T4] ✗ 抛了非预期异常: {type(e).__name__}: {msg[:80]}")
                    ok = False
        restore_planner_routes(db)
        return ok
    finally:
        db.close()


async def main():
    results = []
    # T1
    results.append(await run_test("T1-auto", "planner", "test-provider", "auto", prep_fn=set_auto))
    # T2
    results.append(await run_test("T2-manual-mock", "planner", "mock-provider", "manual", prep_fn=set_manual_lock_mock))
    # T3
    results.append(await run_test("T3-manual-primary", "planner", "test-provider", "manual", prep_fn=set_manual_lock_primary))
    # T4
    results.append(await t4())

    print()
    print("=" * 60)
    if all(results):
        print("Phase 3 全部测试通过 ✓")
    else:
        print(f"Phase 3 部分测试失败: {sum(results)}/{len(results)} 通过")
    print("=" * 60)


asyncio.run(main())
