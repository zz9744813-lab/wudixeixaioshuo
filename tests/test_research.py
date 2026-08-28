"""EPIC-D research layer tests: counterfactuals, rollout, controlled experiments."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal, init_db
from app.main import app
from app.models.evaluation import Evaluation
from app.models.research import Artifact
from app.research.counterfactual import apply_change, build_base_state

SAMPLE = """第一章 启程
清晨，张三离开了家乡。
他回头看了一眼熟悉的村庄。

第二章 风波
夜幕降临，风雨大作。
李四忽然停下了脚步。
第二天
他们发现前方有一座废弃的客栈。
"""


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


# ---- counterfactual builder (deterministic, LLM-free) --------------------- #
def test_base_state_is_fixed_copy(client):
    db = SessionLocal()
    try:
        from app.models.corpus import Scene

        scene = db.scalars(select(Scene).order_by(Scene.index)).first()
        assert scene is not None
        s1 = build_base_state(scene)
        s2 = build_base_state(scene)
        assert s1 == s2  # deterministic
        assert "text" in s1
    finally:
        db.close()


def test_apply_change_knowledge_and_relationship():
    state = {"text": "x", "participants": ["A", "B"]}
    out = apply_change(state, {
        "knowledge_change": {"character": "A", "fact": "F-1", "to": "SUSPECTED"},
        "relationship_change": {"a": "A", "b": "B", "dimension": "trust", "value": 0.3},
    })
    assert out["knowledge"]["A"]["F-1"] == "SUSPECTED"
    assert out["relationships"]["A->B"]["trust"] == 0.3
    assert state["participants"] == ["A", "B"]  # original untouched


def test_apply_change_unknown_op_fails_loudly():
    # A near-miss of a structured op name must fail loudly (禁止6), while
    # free-form parameters (spec §59 style) pass through.
    with pytest.raises(ValueError):
        apply_change({"text": "x"}, {"knowledge_chg": {}})
    out = apply_change({"text": "x"}, {"incremental_clues": 2})
    assert out["parameters"]["incremental_clues"] == 2


def test_control_variant_is_unchanged_copy():
    state = {"text": "x"}
    out = apply_change(state, {})
    assert out["text"] == "x"


# ---- full experiment through the API -------------------------------------- #
def test_experiment_run_is_honest_with_fake_provider(client):
    # Ingest a book so an anchor scene exists.
    client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("novel.txt", SAMPLE.encode("utf-8"), "text/plain")},
        data={"title": "Research Test"},
    )
    h = client.post("/api/v1/hypotheses", json={
        "statement": "Incremental clues during a delayed reveal raise curiosity.",
        "independent_variables": ["incremental_clues"],
        "dependent_variables": ["curiosity"],
        "controls": ["secret_importance"],
        "falsification_condition": "treatment not stably better than control",
    }).json()
    exp = client.post(f"/api/v1/hypotheses/{h['id']}/design-experiment", json={
        "fixed": {"secret_importance": "high"},
        "measurements": ["curiosity", "tension"],
        "variants": [
            {"label": "control", "variant_type": "control", "changed": {}},
            {"label": "treatment_A", "variant_type": "treatment",
             "changed": {"knowledge_change": {"character": "张三", "fact": "客栈的存在", "to": "SUSPECTED"}}},
        ],
    }).json()

    # Baseline for hermetic delta assertions (DB persists across suite runs).
    db = SessionLocal()
    try:
        eval_before = db.scalar(select(func.count()).select_from(Evaluation))
    finally:
        db.close()

    r = client.post(f"/api/v1/experiments/{exp['id']}/run")
    assert r.status_code == 200, r.text
    body = r.json()

    # FakeProvider gives no signal → the runner must be honest, not fake success.
    assert body["decision"] == "inconclusive"
    assert body["hypothesis_status"] == "PROPOSED"
    assert body["pairs"] == 1

    db = SessionLocal()
    try:
        # Rollout artifact + experiment report + one blind pairwise evaluation.
        rollout_count = db.scalar(
            select(func.count()).select_from(Artifact).where(
                Artifact.parent_id == exp["id"], Artifact.type == "rollout_tree"
            )
        )
        report_count = db.scalar(
            select(func.count()).select_from(Artifact).where(
                Artifact.parent_id == exp["id"], Artifact.type == "experiment_report"
            )
        )
        eval_count = db.scalar(select(func.count()).select_from(Evaluation))
    finally:
        db.close()
    assert rollout_count == 2  # control + treatment
    assert report_count == 1
    assert eval_count - eval_before == 1


def test_experiment_requires_variants_and_scene(client):
    h = client.post("/api/v1/hypotheses", json={"statement": "x"}).json()
    exp = client.post(f"/api/v1/hypotheses/{h['id']}/design-experiment", json={
        "variants": [],
    }).json()
    r = client.post(f"/api/v1/experiments/{exp['id']}/run")
    assert r.status_code == 400


def test_experiment_without_control_is_refused(client):
    """禁止6: an experiment without a declared control must fail loudly, not
    silently promote the first treatment to control."""
    h = client.post("/api/v1/hypotheses", json={"statement": "no-control exp"}).json()
    exp = client.post(f"/api/v1/hypotheses/{h['id']}/design-experiment", json={
        "variants": [
            {"label": "t1", "variant_type": "treatment", "changed": {"stakes_change": {"level": "high"}}},
            {"label": "t2", "variant_type": "treatment", "changed": {}},
        ],
    }).json()
    r = client.post(f"/api/v1/experiments/{exp['id']}/run")
    assert r.status_code == 400
    assert "control" in r.json()["detail"]
