"""EPIC-E evaluation tests: reader simulator, arena, benchmark harness."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.main import app
from app.models.benchmark import BenchmarkCase

SAMPLE = """第一章 启程
清晨，张三离开了家乡。
他回头看了一眼熟悉的村庄。

第二章 风波
夜幕降临，风雨大作。
李四忽然停下了脚步。
"""


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def scene_id(client):
    book = client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("novel.txt", SAMPLE.encode("utf-8"), "text/plain")},
        data={"title": "Eval Test"},
    ).json()
    scenes = client.get(f"/api/v1/books/{book['book_id']}/scenes").json()
    return scenes[0]["id"]


def test_reader_sim_with_profile(client, scene_id):
    profile = client.post("/api/v1/reader-profiles", json={
        "name": "impatient-thriller-fan",
        "patience": 0.2,
        "suspense_weight": 0.9,
        "tolerance_for_exposition": 0.2,
    }).json()
    r = client.post("/api/v1/eval/reader-sim", json={
        "scene_id": scene_id,
        "reader_profile_id": profile["id"],
    })
    assert r.status_code == 201, r.text
    metrics = r.json()["metrics"]
    # All nine §21.2 dimensions present (FakeProvider → zeros, but schema-honest).
    assert set(metrics) == {
        "continue_reading_probability", "confusion", "boredom", "curiosity",
        "tension", "satisfaction", "surprise", "character_attachment", "trust_in_author",
    }


def test_reader_sim_requires_input(client):
    r = client.post("/api/v1/eval/reader-sim", json={})
    assert r.status_code == 400


def test_arena_round_robin(client):
    r = client.post("/api/v1/arena/run", json={
        "candidates": [
            {"label": "alpha", "text": "版本A的文本内容，节奏更快。"},
            {"label": "beta", "text": "版本B的文本内容，铺垫更长。"},
            {"label": "gamma", "text": "版本C的文本内容，对话更多。"},
        ]
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["pairs"] == 3  # C(3,2)
    assert set(body["wins"]) == {"alpha", "beta", "gamma"}
    assert len(body["ranking"]) == 3


def test_arena_needs_two_candidates(client):
    r = client.post("/api/v1/arena/run", json={"candidates": [{"label": "solo", "text": "x"}]})
    assert r.status_code == 400


def test_benchmark_golden_case_frozen(client, scene_id):
    payload = {
        "bench": "InfoGapBench",
        "name": "who-knows-the-message",
        "scene_id": scene_id,
        "question": "谁知道消息的存在？",
        "expected": {"knower": "张三"},
    }
    first = client.post("/api/v1/benchmarks/cases", json=payload)
    # 201 on first-ever creation; 409 if a prior suite run already froze it —
    # either way the case must exist and be immutable.
    assert first.status_code in (201, 409), first.text

    # Golden cases are immutable (§47): same name → 409, never overwritten.
    second = client.post("/api/v1/benchmarks/cases", json=payload)
    assert second.status_code == 409


def test_benchmark_run_honest_with_fake(client, scene_id):
    # A case whose expected answer is non-trivial must FAIL under FakeProvider
    # (score 0) — never fake a pass.
    r = client.post("/api/v1/benchmarks/InfoGapBench/run", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cases"] >= 1
    assert body["failed"] == body["cases"]  # fake provider cannot answer
    assert body["mean_score"] == 0.0


def test_benchmark_empty_bench_400(client):
    r = client.post("/api/v1/benchmarks/CharacterBench/run", json={})
    assert r.status_code == 400


def test_benchmark_case_model_frozen_flag(client, scene_id):
    db = SessionLocal()
    try:
        case = db.scalars(
            select(BenchmarkCase).where(BenchmarkCase.name == "who-knows-the-message")
        ).first()
        assert case is not None
        assert case.frozen is True
        assert case.gold is True
    finally:
        db.close()
