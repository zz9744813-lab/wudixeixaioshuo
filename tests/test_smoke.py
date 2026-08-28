"""End-to-end smoke test of the Stage 0 / EPIC-A API surface."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, init_db, get_engine


@pytest.fixture(scope="module")
def client():
    init_db()  # ensure tables (also covered by Alembic in real deploys)
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["tables"] >= 42


def test_book_crud(client):
    r = client.post("/api/v1/books", json={"title": "Test Novel", "genre": "mystery"})
    assert r.status_code == 201, r.text
    book = r.json()
    bid = book["id"]
    assert book["title"] == "Test Novel"

    r = client.get(f"/api/v1/books/{bid}")
    assert r.status_code == 200
    assert r.json()["id"] == bid


def test_character_requires_book(client):
    r = client.post("/api/v1/characters", json={"book_id": "NOPE", "name": "X"})
    assert r.status_code == 404


def test_research_loop(client):
    book = client.post("/api/v1/books", json={"title": "R Book"}).json()
    char = client.post("/api/v1/characters", json={"book_id": book["id"], "name": "A"}).json()

    h = client.post("/api/v1/hypotheses", json={
        "statement": "Delayed reveal with incremental clues yields higher curiosity.",
        "independent_variables": ["incremental_clues"],
        "dependent_variables": ["curiosity"],
        "controls": ["secret_importance"],
        "falsification_condition": "treatment not stably better than control",
    }).json()
    assert h["status"] == "PROPOSED"

    exp = client.post(f"/api/v1/hypotheses/{h['id']}/design-experiment", json={
        "fixed": {"secret_importance": "high"},
        "measurements": ["curiosity", "tension"],
        "variants": [
            {"label": "control", "variant_type": "control", "changed": {"incremental_clues": 0}},
            {"label": "treatment_A", "variant_type": "treatment", "changed": {"incremental_clues": 2}},
        ],
    }).json()
    assert exp["variant_count"] == 2

    run = client.post(f"/api/v1/experiments/{exp['id']}/run").json()
    assert run["status"] == "COMPLETED"


def test_novelforge_gate(client):
    # P-10: the adapter must never reference knowledge below VALIDATED, and must
    # report the governance gap when nothing validated exists. (Other tests may
    # have legitimately promoted rules in this DB, so assert consistency.)
    validated_ids = {r["id"] for r in client.get("/api/v1/rules").json()}
    r = client.post("/api/v1/novelforge/scene-advice", json={
        "scene_goal": "make A suspect B without confirmation",
        "desired_effects": {"curiosity": "high"},
    })
    assert r.status_code == 200
    body = r.json()
    assert set(body["evidence_refs"]) <= validated_ids
    if not validated_ids:
        assert body["recommended_techniques"] == []
        assert "no_validated_knowledge_yet" in body["risk_flags"]
    else:
        assert "no_validated_knowledge_yet" not in body["risk_flags"]
