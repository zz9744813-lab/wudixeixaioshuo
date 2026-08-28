"""EPIC-C multi-pass analysis tests (FakeProvider, no API key needed)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import init_db
from app.llm.fake import FakeProvider, _fill
from app.llm.provider import extract_json
from app.main import app
from app.models.corpus import Scene
from app.models.infra import ModelCall, Run

SAMPLE = """第一章 启程
清晨，张三离开了家乡。
他回头看了一眼熟悉的村庄。

* * *

张三在路上遇见了李四。

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


def _ingest(client):
    r = client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("novel.txt", SAMPLE.encode("utf-8"), "text/plain")},
        data={"title": "Agents Test"},
    )
    return r.json()


def test_fake_provider_fills_schema():
    from app.agents.schemas import EventExtraction

    out = EventExtraction(**_fill(EventExtraction))
    assert out.events == []


def test_extract_json_repair():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json("noise {\"b\": 2} noise") == {"b": 2}
    assert extract_json("not json") is None


def test_analyze_endpoint_runs_all_passes(client):
    # Hermetic: clear prior agent runs so counts are exact for this run.
    from sqlalchemy import delete

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        db.execute(delete(ModelCall))
        db.execute(delete(Run).where(Run.task_type.in_([
            "event", "perception", "knowledge", "belief", "goal", "emotion",
            "relationship", "causality", "technique", "counterinterpretation", "reconcile",
        ])))
        db.commit()
    finally:
        db.close()

    book = _ingest(client)
    scenes = client.get(f"/api/v1/books/{book['book_id']}/scenes").json()
    scene_id = scenes[0]["id"]

    r = client.post(f"/api/v1/scenes/{scene_id}/analyze?force=true")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["analyzed"] is True
    assert len(body["passes"]) == 11  # 11 passes wired

    # Provenance: every pass recorded a Run + ModelCall (spec §35).
    db = SessionLocal()
    try:
        run_count = db.scalar(
            select(func.count()).select_from(Run).where(Run.task_type.in_([
                "event", "perception", "knowledge", "belief", "goal", "emotion",
                "relationship", "causality", "technique", "counterinterpretation", "reconcile",
            ]))
        )
        call_count = db.scalar(select(func.count()).select_from(ModelCall))
    finally:
        db.close()
    assert run_count == 11
    assert call_count == 11

    assert db_scalar_scene(scene_id) is not None


def db_scalar_scene(scene_id):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        return db.get(Scene, scene_id)
    finally:
        db.close()
