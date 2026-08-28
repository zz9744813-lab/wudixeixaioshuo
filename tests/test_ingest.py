"""Tests for the EPIC-B ingestion pipeline.

Covers rule-based parsers (txt/md/epub/docx), chapter + scene detection, duplicate
detection, the HTTP ingest endpoints, idempotency, and the local worker drain.
"""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.ingest.chapter_detector import detect_chapters
from app.ingest.dedup import find_duplicates
from app.ingest.parsers import parse_bytes
from app.ingest.scene_splitter import split_chapter
from app.ingest.service import enqueue_ingest, ingest_bytes
from app.ingest.types import ChapterBlock
from app.main import app
from app.models.corpus import Book, Chapter, Scene, SceneSpan
from app.models.enums import TaskStatus
from app.models.infra import Task

SAMPLE_TXT = """序
这是一段前言文字，没有章节标题。

第一章 启程
清晨，张三离开了家乡。
他回头看了一眼熟悉的村庄。

* * *

张三在路上遇见了李四。
两人结伴同行。

第二章 风波
夜幕降临，风雨大作。
李四忽然停下了脚步。

第二天
他们发现前方有一座废弃的客栈。

第三章 结局
故事在此暂告一段落。
"""


@pytest.fixture(scope="module")
def client():
    from app.db import init_db

    init_db()
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------------- #
# Parsers
# --------------------------------------------------------------------------- #
def test_txt_parser():
    doc = parse_bytes(SAMPLE_TXT.encode("utf-8"), "novel.txt")
    assert doc.format == "txt"
    assert "第一章" in doc.text
    assert "序" in doc.text


def test_md_parser_headings():
    md = "# 第一章 启程\n张三出发了。\n\n## 小节\n细节。\n\n# 第二章 风波\n风雨。\n"
    doc = parse_bytes(md.encode("utf-8"), "novel.md")
    assert doc.format == "md"
    levels = {h.level for h in doc.headings}
    assert 1 in levels and 2 in levels
    assert doc.text.count("启程") == 1  # heading text preserved, marker stripped


def test_epub_parser():
    raw = _build_epub()
    doc = parse_bytes(raw, "book.epub")
    assert doc.format == "epub"
    assert "启程" in doc.text
    assert any(h.level == 1 for h in doc.headings)


def test_docx_parser():
    raw = _build_docx()
    doc = parse_bytes(raw, "book.docx")
    assert doc.format == "docx"
    assert "启程" in doc.text
    assert any(h.level == 1 for h in doc.headings)


# --------------------------------------------------------------------------- #
# Chapter + scene detection
# --------------------------------------------------------------------------- #
def test_chapter_detection():
    doc = parse_bytes(SAMPLE_TXT.encode("utf-8"), "novel.txt")
    chapters = detect_chapters(doc.text, doc.headings)
    # 序 (preamble) + 3 章
    assert len(chapters) == 4
    assert chapters[0].title is None  # preamble
    assert chapters[1].title == "启程"
    assert chapters[2].title == "风波"


def test_scene_splitting():
    doc = parse_bytes(SAMPLE_TXT.encode("utf-8"), "novel.txt")
    chapters = detect_chapters(doc.text, doc.headings)
    ch1 = chapters[1]
    scenes = split_chapter(ch1, doc.headings)
    # 第一章 has one '* * *' ornament break -> 2 scenes
    assert len(scenes) == 2
    ch2 = chapters[2]
    scenes2 = split_chapter(ch2, doc.headings)
    # 第二章 has a '第二天' time-jump -> 2 scenes
    assert len(scenes2) == 2


def test_no_boundary_single_chapter():
    doc = parse_bytes("只是一些普通的文字，没有章节标题，也没有场景分隔。\n".encode("utf-8") * 3, "x.txt")
    chapters = detect_chapters(doc.text, doc.headings)
    assert len(chapters) == 1
    scenes = split_chapter(chapters[0], doc.headings)
    assert len(scenes) == 1


def test_giant_chapter_fallback_split():
    huge = ("段落内容重复用以构造超长场景。" * 50 + "\n\n") * 30
    ch = ChapterBlock(index=0, title=None, raw_text=huge, char_start=0, char_end=len(huge))
    scenes = split_chapter(ch, [])
    assert len(scenes) > 1
    assert all(s.heuristic for s in scenes)


# --------------------------------------------------------------------------- #
# Duplicate detection
# --------------------------------------------------------------------------- #
def test_dedup_exact():
    texts = ["独特的第一段内容。", "完全相同的重复段落。", "另一段不一样的。", "完全相同的重复段落。"]
    groups = find_duplicates(texts)
    assert [1, 3] in groups or [3, 1] in groups


# --------------------------------------------------------------------------- #
# HTTP ingest (spec §39)
# --------------------------------------------------------------------------- #
def test_corpus_ingest_txt(client):
    r = client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("novel.txt", SAMPLE_TXT.encode("utf-8"), "text/plain")},
        data={"title": "测试小说", "genre": "mystery"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["chapter_count"] == 4
    assert body["scene_count"] >= 5
    assert body["span_count"] > 0

    # Book now lists the scenes.
    scenes = client.get(f"/api/v1/books/{body['book_id']}/scenes").json()
    assert len(scenes) == body["scene_count"]


def test_corpus_ingest_md(client):
    md = "# 第一章 启程\n张三出发了。\n\n# 第二章 风波\n风雨交加。\n"
    r = client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("novel.md", md.encode("utf-8"), "text/markdown")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["chapter_count"] == 2


def test_corpus_ingest_epub(client):
    r = client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("book.epub", _build_epub(), "application/epub+zip")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["chapter_count"] >= 2


def test_corpus_ingest_docx(client):
    r = client.post(
        "/api/v1/corpus/ingest",
        files={"file": ("book.docx", _build_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["chapter_count"] >= 2


def test_ingest_idempotent(client):
    content = SAMPLE_TXT.encode("utf-8")
    first = client.post(
        "/api/v1/corpus/ingest", files={"file": ("novel.txt", content, "text/plain")}
    ).json()
    second = client.post(
        "/api/v1/corpus/ingest", files={"file": ("novel.txt", content, "text/plain")}
    ).json()
    assert second["idempotent"] is True
    assert second["book_id"] == first["book_id"]
    assert second["scene_count"] == first["scene_count"]


def test_book_scoped_ingest_and_idempotency(client):
    book = client.post("/api/v1/books", json={"title": "Scope Book"}).json()
    bid = book["id"]
    content = SAMPLE_TXT.encode("utf-8")

    r1 = client.post(
        f"/api/v1/books/{bid}/ingest", files={"file": ("novel.txt", content, "text/plain")}
    )
    assert r1.status_code == 201, r1.text
    scenes_1 = r1.json()["scene_count"]

    r2 = client.post(
        f"/api/v1/books/{bid}/ingest", files={"file": ("novel.txt", content, "text/plain")}
    )
    assert r2.json()["idempotent"] is True
    assert r2.json()["scene_count"] == scenes_1  # no duplicate chapters


def test_ingest_unknown_book_404(client):
    r = client.post(
        "/api/v1/books/NOPE/ingest", files={"file": ("x.txt", b"hi", "text/plain")}
    )
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Worker drain (spec §40)
# --------------------------------------------------------------------------- #
def test_worker_drain():
    from app.ingest.worker import drain_ingest_queue

    db = SessionLocal()
    try:
        from app.core.ids import new_id

        book = Book(id=new_id("BOOK"), title="Worker Book", metadata_={})
        db.add(book)
        db.flush()
        task = enqueue_ingest(db, SAMPLE_TXT.encode("utf-8"), "novel.txt", book=book)
        assert task.status == TaskStatus.PENDING

        processed = drain_ingest_queue(db=db)
        assert processed == 1

        reloaded = db.get(Task, task.id)
        assert reloaded.status == TaskStatus.SUCCESS

        scene_count = db.scalar(
            select(func.count()).select_from(Scene).where(Scene.book_id == book.id)
        )
        assert scene_count >= 5
        span_count = db.scalar(
            select(func.count()).select_from(SceneSpan)
            .join(Scene, SceneSpan.scene_id == Scene.id)
            .where(Scene.book_id == book.id)
        )
        assert span_count > 0
    finally:
        db.rollback()
        db.close()


# --------------------------------------------------------------------------- #
# Fixture builders
# --------------------------------------------------------------------------- #
def _build_epub() -> bytes:
    container = (
        '<?xml version="1.0"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>"
    )
    opf = (
        '<?xml version="1.0"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
        "<metadata><dc:title xmlns:dc='http://purl.org/dc/elements/1.1/'>测试</dc:title></metadata>"
        "<manifest>"
        "<item id='c1' href='c1.xhtml' media-type='application/xhtml+xml'/>"
        "<item id='c2' href='c2.xhtml' media-type='application/xhtml+xml'/>"
        "</manifest>"
        "<spine><itemref idref='c1'/><itemref idref='c2'/></spine>"
        "</package>"
    )
    c1 = "<html><body><h1>第一章 启程</h1><p>张三出发了。</p></body></html>"
    c2 = "<html><body><h1>第二章 风波</h1><p>风雨交加。</p></body></html>"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("OEBPS/content.opf", opf)
        zf.writestr("OEBPS/c1.xhtml", c1)
        zf.writestr("OEBPS/c2.xhtml", c2)
    return buf.getvalue()


def _build_docx() -> bytes:
    document = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:pPr><w:pStyle w:val='Heading1'/></w:pPr><w:r><w:t>第一章 启程</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>张三出发了。</w:t></w:r></w:p>"
        "<w:p><w:pPr><w:pStyle w:val='Heading1'/></w:pPr><w:r><w:t>第二章 风波</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>风雨交加。</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", document)
    return buf.getvalue()
