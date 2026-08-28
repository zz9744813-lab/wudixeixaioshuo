"""EPIC-F knowledge promotion gate tests (spec §26, §51, §63)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _create_rule(client, **overrides):
    payload = {
        "name": "延迟揭示需要增量线索",
        "statement": "延迟揭示期间加入增量线索会提高好奇心。",
        **overrides,
    }
    r = client.post("/api/v1/rules", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_observation_blocked_without_mechanism(client):
    rule = _create_rule(client)
    r = client.post(f"/api/v1/rules/{rule['id']}/promote")
    body = r.json()
    assert body["promoted"] is False
    assert any("mechanism" in m for m in body["missing"])


def test_ladder_stepwise_with_all_gates(client):
    rule = _create_rule(client, mechanism="信息差 + 期待积累")

    # OBSERVATION → CANDIDATE (mechanism present)
    r = client.post(f"/api/v1/rules/{rule['id']}/promote").json()
    assert r["promoted"] is True and r["to"] == "CANDIDATE"

    # CANDIDATE → SUPPORTED needs evidence
    r = client.post(f"/api/v1/rules/{rule['id']}/promote").json()
    assert r["promoted"] is False and any("evidence" in m for m in r["missing"])

    # Add evidence via direct update is not exposed; recreate with evidence.
    rule2 = _create_rule(client, name="带证据的规则", mechanism="信息差", evidence=[{"span": "S1"}])
    r = client.post(f"/api/v1/rules/{rule2['id']}/promote").json()
    assert r["promoted"] is True and r["to"] == "CANDIDATE"
    r = client.post(f"/api/v1/rules/{rule2['id']}/promote").json()
    assert r["promoted"] is True and r["to"] == "SUPPORTED"

    # SUPPORTED → REPLICATED needs counterexample + 2 reproductions.
    r = client.post(f"/api/v1/rules/{rule2['id']}/promote").json()
    assert r["promoted"] is False
    assert any("counterexample" in m for m in r["missing"])
    assert any("reproduction" in m for m in r["missing"])

    ce = client.post(f"/api/v1/rules/{rule2['id']}/counterexamples", json={
        "observation": "在日常流中延迟揭示反而显得做作。",
    })
    assert ce.status_code == 201
    # Still blocked: reproduction_count is 0 (no cross-sample reproduction yet).
    r = client.post(f"/api/v1/rules/{rule2['id']}/promote").json()
    assert r["promoted"] is False and any("reproduction" in m for m in r["missing"])

    # REPLICATED → VALIDATED needs experiment + judge agreement.
    # (Cannot reach REPLICATED through the API without reproductions — the gate
    # holds. Verify the VALIDATED gate via a rule seeded directly in the DB.)
    from app.db import SessionLocal
    from app.models.enums import KnowledgeTier
    from app.models.knowledge_registry import KnowledgeRule

    db = SessionLocal()
    try:
        kr = db.get(KnowledgeRule, rule2["id"])
        kr.reproduction_count = 2
        kr.counterexamples = list(kr.counterexamples) + [{"observation": "反例2"}]
        db.add(kr)
        db.commit()
    finally:
        db.close()
    r = client.post(f"/api/v1/rules/{rule2['id']}/promote").json()
    assert r["promoted"] is True and r["to"] == "REPLICATED"

    r = client.post(f"/api/v1/rules/{rule2['id']}/promote").json()
    assert r["promoted"] is False and any("experiment" in m for m in r["missing"])


def test_validated_requires_experiment_and_judge(client):
    from app.db import SessionLocal
    from app.models.enums import KnowledgeTier
    from app.models.knowledge_registry import KnowledgeRule

    rule = _create_rule(client, name="直接到REPLICATED", mechanism="m", evidence=[{"s": "1"}])
    db = SessionLocal()
    try:
        kr = db.get(KnowledgeRule, rule["id"])
        kr.tier = KnowledgeTier.REPLICATED
        kr.counterexamples = [{"observation": "x"}]
        kr.reproduction_count = 2
        db.add(kr)
        db.commit()
    finally:
        db.close()

    # No experiment yet → blocked.
    r = client.post(f"/api/v1/rules/{rule['id']}/promote").json()
    assert r["promoted"] is False and any("experiment" in m for m in r["missing"])

    # Experiment but no judge → still blocked.
    db = SessionLocal()
    try:
        kr = db.get(KnowledgeRule, rule["id"])
        kr.experiment_ids = ["EXP-1"]
        db.add(kr)
        db.commit()
    finally:
        db.close()
    r = client.post(f"/api/v1/rules/{rule['id']}/promote").json()
    assert r["promoted"] is False and any("judge" in m for m in r["missing"])

    # Experiment + sufficient judge agreement → VALIDATED.
    db = SessionLocal()
    try:
        kr = db.get(KnowledgeRule, rule["id"])
        kr.judge_agreement = 0.8
        db.add(kr)
        db.commit()
    finally:
        db.close()
    r = client.post(f"/api/v1/rules/{rule['id']}/promote").json()
    assert r["promoted"] is True and r["to"] == "VALIDATED"

    # VALIDATED → PRODUCTION_PROVEN requires real production evidence.
    r = client.post(f"/api/v1/rules/{rule['id']}/promote").json()
    assert r["promoted"] is False and any("production" in m for m in r["missing"])


def test_production_only_sees_validated_plus(client):
    from app.db import SessionLocal
    from app.models.enums import KnowledgeTier
    from app.models.knowledge_registry import KnowledgeRule

    # Seed one VALIDATED and one OBSERVATION rule.
    rule_v = _create_rule(client, name="生产可见规则", mechanism="m")
    rule_o = _create_rule(client, name="观察级规则", mechanism="m")
    db = SessionLocal()
    try:
        kr = db.get(KnowledgeRule, rule_v["id"])
        kr.tier = KnowledgeTier.VALIDATED
        db.add(kr)
        db.commit()
    finally:
        db.close()

    visible = client.get("/api/v1/rules").json()
    ids = {r["id"] for r in visible}
    assert rule_v["id"] in ids
    assert rule_o["id"] not in ids  # P-10: OBSERVATION never reaches production


def test_demote_deprecates(client):
    rule = _create_rule(client, name="将被废弃")
    r = client.post(f"/api/v1/rules/{rule['id']}/demote", json={"reason": "被 NovelForge 证伪"}).json()
    assert r["to"] == "DEPRECATED"
    gate = client.get(f"/api/v1/rules/{rule['id']}/gate").json()
    assert gate["tier"] == "DEPRECATED"


def test_gate_checklist_shape(client):
    rule = _create_rule(client, name="清单规则")
    gate = client.get(f"/api/v1/rules/{rule['id']}/gate").json()
    assert set(gate["checklist"]) == {
        "mechanism_明确", "preconditions_明确", "failure_modes_明确",
        "多个_source_evidence", "有_counterexample", "有_反事实实验",
        "有_独立_judge", "跨样本复现", "达到_VALIDATED",
    }
