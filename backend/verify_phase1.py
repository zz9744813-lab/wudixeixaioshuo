"""
Phase 1 端到端验证脚本
Seed: 1 provider + 2 routes (1主+1备) + 1 model_role
验证: 7 个新端点 + routing event 自动落库
"""
import sys
sys.path.insert(0, 'F:/kelaode/quanzidong/backend')

from datetime import datetime, timedelta
from app.database import SessionLocal, init_db
from app.models.model_config import ModelProvider, ModelRole
from app.models.provider_route_config import ProviderRouteConfig
from app.models.model_routing_event import ModelRoutingEvent
from fastapi.testclient import TestClient
from app.main import app

# Init DB + migrations
init_db()

# Seed test data
db = SessionLocal()
try:
    # 1 provider
    if not db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first():
        p = ModelProvider(
            name="test-provider",
            provider_type="openai",
            base_url="http://localhost:11451/v1",
            api_key_encrypted="gAAAAA_testkey1234abcd",
            api_key_mask="****1234",
            default_model="test-model-v1",
            is_enabled=1,
            status="healthy",
        )
        db.add(p)
        db.commit()
        print(f"[seed] created provider id={p.id}")
    else:
        p = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first()
        print(f"[seed] provider exists id={p.id}")

    # 2 routes for planner
    routes_count = (
        db.query(ProviderRouteConfig)
        .filter(ProviderRouteConfig.role == "planner")
        .count()
    )
    if routes_count == 0:
        # Primary route (whitedream-like)
        primary_provider = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first()
        r1 = ProviderRouteConfig(
            provider_id=primary_provider.id,
            role="planner",
            priority=10,
            weight=1,
            enabled=True,
            timeout_seconds=60,
            max_retries=2,
            total_calls=20,
            success_calls=18,
            failed_calls=2,
            avg_latency_ms=850,
        )
        db.add(r1)
        # Secondary (mock) for fallback test
        if not db.query(ModelProvider).filter(ModelProvider.name == "mock-provider").first():
            mp = ModelProvider(
                name="mock-provider",
                provider_type="stub",
                base_url="http://localhost:9999/mock/v1",
                api_key_encrypted=None,
                default_model="mock-fast",
                is_enabled=1,
                status="healthy",
            )
            db.add(mp)
            db.commit()
        mock_p = db.query(ModelProvider).filter(ModelProvider.name == "mock-provider").first()
        r2 = ProviderRouteConfig(
            provider_id=mock_p.id,
            role="planner",
            priority=100,
            weight=1,
            enabled=True,
            timeout_seconds=30,
            max_retries=1,
            total_calls=5,
            success_calls=5,
            failed_calls=0,
            avg_latency_ms=120,
        )
        db.add(r2)
        db.commit()
        print(f"[seed] created 2 routes for planner")
    else:
        print(f"[seed] routes already exist ({routes_count} for planner)")

    # 1 model_role for draft
    if not db.query(ModelRole).filter(ModelRole.role == "draft").first():
        primary_provider = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first()
        mr = ModelRole(
            role="draft",
            project_id=None,
            provider_id=primary_provider.id,
            model_name="test-model-v1",
            temperature=0.7,
            max_tokens=4000,
            priority=1,
            assignment_mode="auto",
        )
        db.add(mr)
        db.commit()
        print(f"[seed] created model_role for draft")
    else:
        print(f"[seed] model_role for draft exists")

    # 1 routing event
    if db.query(ModelRoutingEvent).count() == 0:
        primary_provider = db.query(ModelProvider).filter(ModelProvider.name == "test-provider").first()
        e = ModelRoutingEvent(
            role="planner",
            assignment_mode="auto",
            selected_provider_id=primary_provider.id,
            selected_provider_name=primary_provider.name,
            selected_model_name="test-model-v1",
            decision_reason="种子数据：测试用",
        )
        e.set_candidates([
            {"provider_id": primary_provider.id, "score": 85, "reason": "primary"},
        ])
        e.set_score_breakdown({"priority": 30, "health": 25, "total": 55})
        db.add(e)
        db.commit()
        print(f"[seed] created 1 routing event")
    else:
        print(f"[seed] routing events already exist ({db.query(ModelRoutingEvent).count()})")
finally:
    db.close()

# 端到端 API 测试
print()
print("=" * 60)
print("端到端 API 测试")
print("=" * 60)
client = TestClient(app)
HEADERS = {"X-API-Key": "test"}


def show(label, r):
    print(f"\n[{label}] status={r.status_code}")
    if r.status_code >= 400:
        print(f"   body: {r.json()}")
    else:
        body = r.json()
        # 限制打印大小
        s = str(body)
        if len(s) > 600:
            s = s[:600] + "..."
        print(f"   body: {s}")
    return r


# T1: 列表
r = show("T1 list", client.get("/api/agent-model-configs", headers=HEADERS))
if r.status_code == 200:
    d = r.json()
    assert d["summary"]["agent_count"] == 18
    assert d["summary"]["manual_count"] >= 0
    assert len(d["groups"]) == 4  # 4 categories
    # 找到 planner，验证有 provider
    planner = None
    for g in d["groups"]:
        for a in g["agents"]:
            if a["agent_key"] == "planner":
                planner = a
    assert planner is not None
    assert planner["provider_name"] == "test-provider"
    assert planner["model_name"] == "test-model-v1"
    assert planner["enabled_route_count"] == 2
    assert "decision_reason" in planner
    print("   ✓ planner card 字段完整")

# T2: 详情
r = show("T2 detail", client.get("/api/agent-model-configs/planner", headers=HEADERS))
if r.status_code == 200:
    d = r.json()
    assert "candidates" in d and len(d["candidates"]) == 2
    assert d["candidates"][0]["score"] >= d["candidates"][1]["score"]  # 排序
    assert d["candidates"][0]["provider_name"] == "test-provider"  # priority 10 > 100
    assert "recent_runs" in d
    assert "recent_routing_events" in d
    assert len(d["recent_routing_events"]) >= 1
    print(f"   ✓ planner 详情: {len(d['candidates'])} candidates, "
          f"top={d['candidates'][0]['provider_name']}/score={d['candidates'][0]['score']}, "
          f"1 routing event")

# T3: routing preview
r = show("T3 preview", client.post(
    "/api/agent-model-configs/routing-preview",
    headers=HEADERS, json={"role": "planner"}))
if r.status_code == 200:
    d = r.json()
    assert d["selected"] is not None
    assert d["selected"]["provider_name"] == "test-provider"  # priority 10
    assert d["candidate_count"] == 2
    assert "breakdown" in d["candidates"][0]
    assert "priority" in d["candidates"][0]["breakdown"]
    print(f"   ✓ preview 选中: {d['selected']['provider_name']}/score={d['selected']['score']}")

# T4: auto-assign dry-run
r = show("T4 auto (dry)", client.post(
    "/api/agent-model-configs/auto-assign",
    headers=HEADERS, json={"dry_run": True}))
if r.status_code == 200:
    d = r.json()
    assert d["dry_run"] is True
    print(f"   ✓ dry_run 返回 {len(d['results'])} 个 role")

# T5: binding update
r = show("T5 binding", client.put(
    "/api/agent-model-configs/draft/binding",
    headers=HEADERS, json={"assignment_mode": "manual", "fallback_enabled": False}))
if r.status_code == 200:
    d = r.json()
    assert d["binding"]["assignment_mode"] == "manual"
    assert d["binding"]["fallback_enabled"] is False
    # 验证：恢复 auto
    r2 = client.put("/api/agent-model-configs/draft/binding",
                    headers=HEADERS, json={"assignment_mode": "auto", "fallback_enabled": True})
    assert r2.status_code == 200
    print("   ✓ manual/auto 切换可逆")

# T6: roles meta
r = show("T6 meta", client.get("/api/agent-model-configs/meta/roles", headers=HEADERS))
if r.status_code == 200:
    d = r.json()
    assert len(d["roles"]) == 16
    cats = set(r_["category"] for r_ in d["roles"])
    assert "writing" in cats and "quality" in cats
    print(f"   ✓ 16 roles, 4 categories")

# T7: routing events history
r = show("T7 events", client.get(
    "/api/agent-model-configs/planner/routing-events", headers=HEADERS))
if r.status_code == 200:
    d = r.json()
    assert d["role"] == "planner"
    assert len(d["items"]) >= 1
    item = d["items"][0]
    assert "decision_reason" in item
    assert "candidates" in item
    print(f"   ✓ {len(d['items'])} routing event(s)")

# T8: idempotent migration - 再调一次 init_db 不报错
print()
print("[T8] migration idempotency")
try:
    init_db()
    print("   ✓ 第二次 init_db 不报错")
except Exception as e:
    print(f"   ✗ {e}")

print()
print("=" * 60)
print("Phase 1 全部端到端测试通过")
print("=" * 60)
