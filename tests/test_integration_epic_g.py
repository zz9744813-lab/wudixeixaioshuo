"""EPIC-G integration tests: NovelForge adapter (§43), production feedback (§44),
Obsidian export (§42)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.main import app
from app.models.enums import KnowledgeTier
from app.models.knowledge_registry import KnowledgeRule


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _seed_rule(client, tier: KnowledgeTier, name: str) -> str:
    r = client.post("/api/v1/rules", json={
        "name": name, "statement": "s", "mechanism": "m",
        "preconditions": ["secret_importance_high"],
        "failure_modes": ["reveal_without_consequence"],
    }).json()
    db = SessionLocal()
    try:
        kr = db.get(KnowledgeRule, r["id"])
        kr.tier = tier
        db.add(kr)
        db.commit()
    finally:
        db.close()
    return r["id"]


def test_adapter_returns_full_section43_shape(client):
    rule_id = _seed_rule(client, KnowledgeTier.VALIDATED, "§43 形状规则")
    r = client.post("/api/v1/novelforge/scene-advice", json={
        "scene_goal": "让A怀疑B但不能确认",
        "character_ids": ["CHAR-A"],
    })
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "character_constraints", "knowledge_constraints", "causal_constraints",
        "recommended_techniques", "avoid_patterns", "candidate_events",
        "risk_flags", "evidence_refs", "knowledge_tier",
    }
    assert rule_id in body["evidence_refs"]
    # Constraints derive from the validated rule's §61 card, not raw novel text (§45).
    assert any(c["rule_id"] == rule_id and c["constraint"] == "secret_importance_high"
               for c in body["knowledge_constraints"])
    assert any(a["rule_id"] == rule_id and a["pattern"] == "reveal_without_consequence"
               for a in body["avoid_patterns"])
    assert body["knowledge_tier"] in ("VALIDATED", "PRODUCTION_PROVEN")
    assert "no_validated_knowledge_yet" not in body["risk_flags"]


def test_production_feedback_promotes_and_demotes(client):
    rule_ok = _seed_rule(client, KnowledgeTier.VALIDATED, "生产成功规则")
    r = client.post("/api/v1/novelforge/production-feedback", json={
        "rule_id": rule_ok, "accepted": True, "chapter_ref": "CH-42",
        "notes": "A/B 中胜出",
    }).json()
    assert r["outcome"] == "accepted"
    assert r["to"] == "PRODUCTION_PROVEN"

    rule_bad = _seed_rule(client, KnowledgeTier.VALIDATED, "生产失败规则")
    r = client.post("/api/v1/novelforge/production-feedback", json={
        "rule_id": rule_bad, "accepted": False, "notes": "读者模拟器翻车",
    }).json()
    assert r["outcome"] == "rejected"
    assert r["to"] == "SUPPORTED"  # §63: NovelForge 实际失败 → 降级

    # The demoted rule must disappear from the production surface (P-10).
    visible = {x["id"] for x in client.get("/api/v1/rules").json()}
    assert rule_bad not in visible
    assert rule_ok in visible


def test_production_feedback_requires_target(client):
    r = client.post("/api/v1/novelforge/production-feedback", json={"accepted": True})
    assert r.status_code == 400


def test_obsidian_export_creates_vault(client, tmp_path):
    r = client.post("/api/v1/export/obsidian")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["counts"]["scenes"] >= 0
    expected_files = {f"{n}.md" for n in [
        "00_总仪表盘", "01_研究进展", "03_待验证假设", "04_已验证规律",
        "05_反例库", "15_失败研究", "16_系统健康",
    ]}
    assert expected_files <= set(body["files"])
    vault = Path(body["directory"])
    assert vault.exists()
    assert (vault / "00_总仪表盘.md").read_text(encoding="utf-8").startswith("# 总仪表盘")


def test_plot_options_only_validated(client):
    rule_id = _seed_rule(client, KnowledgeTier.VALIDATED, "情节约束规则")
    r = client.post("/api/v1/novelforge/plot-options", json={"scene_goal": "x"}).json()
    assert any(c["rule_id"] == rule_id for c in r["candidate_constraints"])
