"""Ingest service (spec §6, §33, §35, §38).

Orchestrates the full pipeline and persists the result:

    raw bytes
      -> object store (immutable copy)            (§6.3, §38)
      -> CorpusSource row
      -> parse (format parser)                    (§6.1)
      -> chapter detection                         (§6.2, §7)
      -> scene splitting per chapter              (§7)
      -> duplicate detection                       (§6.2)
      -> Book / Chapter / Scene / SceneSpan rows
      -> Task state machine (PENDING→RUNNING→SUCCESS / FAILED)  (§33)
      -> idempotency (re-ingest of identical bytes is a no-op)   (§33)

The work is split into :func:`_prepare` (immutable copy + source/book/task rows,
PENDING) and :func:`_process` (parse→split→persist, SUCCESS). The synchronous
:func:`ingest_bytes` runs both in one call; the Worker (``app.ingest.worker``)
can instead enqueue via :func:`enqueue_ingest` and drain later. All of it is
deterministic and LLM-free, so a re-run with the same file is idempotent.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.ingest.chapter_detector import detect_chapters
from app.ingest.dedup import find_duplicates
from app.ingest.parsers import parse_bytes
from app.ingest.scene_splitter import split_chapter
from app.ingest.types import IngestResult
from app.models.corpus import Book, Chapter, CorpusSource, Scene, SceneSpan
from app.models.enums import SourceClass, TaskStatus
from app.models.infra import DeadLetter, Task

_OBJECT_STORE = Path(__file__).resolve().parents[2] / "data" / "object_store" / "corpus_sources"

_CJK = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z0-9]+")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _count_tokens(text: str) -> int:
    return len(_CJK.findall(text)) + len(_LATIN.findall(text))


def _content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _save_raw_copy(raw: bytes, source_id: str, ext: str) -> Path:
    _OBJECT_STORE.mkdir(parents=True, exist_ok=True)
    path = _OBJECT_STORE / f"{source_id}.{ext}"
    path.write_bytes(raw)
    return path


def _resolve_source_class(value: str | None) -> SourceClass:
    try:
        return SourceClass(value)
    except (ValueError, TypeError):
        return SourceClass.HUMAN_ORIGINAL


def _build_idempotency_key(book_id: Optional[str], content_hash: str) -> str:
    scope = book_id or "corpus"
    return f"ingest:{scope}:{content_hash[:24]}"


def _prepare(
    db: Session,
    raw: bytes,
    filename: str | None,
    *,
    book: Optional[Book],
    title: Optional[str],
    author: Optional[str],
    genre: Optional[str],
    source_class: str,
) -> Tuple[Book, CorpusSource, Task, str]:
    """Create the immutable raw copy + CorpusSource + Book + PENDING Task.

    Returns ``(book, source, task, ext)``. Idempotent: identical bytes ingested
    into the same scope return the cached SUCCESS result instead (via the caller).
    """
    content_hash = _content_hash(raw)
    idem_key = _build_idempotency_key(book.id if book else None, content_hash)
    ext = (filename or "upload.txt").rsplit(".", 1)[-1].lower() or "txt"

    source_id = new_id("SRC")
    raw_path = _save_raw_copy(raw, source_id, ext)

    source = CorpusSource(
        id=source_id,
        title=title or (filename or "untitled"),
        author=author,
        source_class=_resolve_source_class(source_class),
        format=ext,
        raw_path=str(raw_path),
        language=None,
        metadata_={"filename": filename, "content_hash": content_hash},
        imported_at=_now(),
    )
    db.add(source)
    # The source row must physically exist before any book references it: with
    # no relationship() between the two, the unit of work orders tables
    # alphabetically and PostgreSQL would enforce the FK mid-flush otherwise.
    db.flush()

    if book is None:
        book = Book(
            id=new_id("BOOK"),
            corpus_source_id=source.id,
            title=title or (filename or "untitled"),
            author=author,
            genre=genre,
            metadata_={},
        )
    else:
        if not book.corpus_source_id:
            book.corpus_source_id = source.id

    task = Task(
        id=new_id("TASK"),
        type="ingest",
        queue="ingest",
        status=TaskStatus.PENDING,
        idempotency_key=idem_key,
        payload={
            "filename": filename,
            "content_hash": content_hash,
            "ext": ext,
            "source_id": source.id,
            "book_id": book.id,
        },
        retries=0,
        max_retries=3,
    )
    db.add(book)
    db.add(task)
    db.flush()
    return book, source, task, ext


def _run_pipeline(db: Session, raw: bytes, filename: str, *, book: Book, source: CorpusSource) -> IngestResult:
    doc = parse_bytes(raw, filename)
    chapters = detect_chapters(doc.text, doc.headings)

    scene_count = 0
    span_count = 0
    all_scene_texts: list[str] = []

    for ci, chap in enumerate(chapters):
        chapter = Chapter(
            id=new_id("CH"),
            book_id=book.id,
            index=ci,
            title=chap.title,
            raw_text=chap.raw_text,
            word_count=_count_tokens(chap.raw_text),
        )
        db.add(chapter)

        scenes = split_chapter(chap, doc.headings)

        for si, sc in enumerate(scenes):
            scene = Scene(
                id=new_id("SCENE"),
                book_id=book.id,
                chapter_id=chapter.id,
                index=si,
                source_range={
                    "chapter_index": ci,
                    "char_start": sc.char_start,
                    "char_end": sc.char_end,
                    "heuristic": sc.heuristic,
                },
                analyzed=False,
            )
            db.add(scene)
            scene_count += 1

            for p in sc.paragraphs:
                local_start = max(0, p.char_start - sc.char_start)
                local_end = max(local_start, p.char_end - sc.char_start)
                db.add(
                    SceneSpan(
                        id=new_id("SPAN"),
                        scene_id=scene.id,
                        char_start=local_start,
                        char_end=local_end,
                        text=p.text,
                    )
                )
                span_count += 1
            all_scene_texts.append(sc.raw_text)

    duplicate_groups = [grp for grp in find_duplicates(all_scene_texts) if len(grp) > 1]
    warnings: list[str] = []
    if duplicate_groups:
        warnings.append(f"{len(duplicate_groups)} duplicate scene group(s) detected")

    return IngestResult(
        book_id=book.id,
        source_id=source.id,
        task_id="",  # filled by caller
        chapter_count=len(chapters),
        scene_count=scene_count,
        span_count=span_count,
        duplicate_groups=duplicate_groups,
        warnings=warnings,
    )


def _finalize_success(db: Session, task: Task, result: IngestResult) -> IngestResult:
    result.task_id = task.id
    task.status = TaskStatus.SUCCESS
    task.result = result.to_dict()
    task.finished_at = _now()
    db.commit()
    return result


def _fail(db: Session, task: Task, exc: Exception) -> None:
    """Record a failure and route to the dead-letter queue (禁止无限重试, 禁止11)."""
    db.rollback()
    task = db.get(Task, task.id)
    if task is not None:
        task.status = TaskStatus.FAILED_RETRYABLE
        task.error = str(exc)[:2000]
        task.finished_at = _now()
        db.add(
            DeadLetter(
                id=new_id("DL"),
                original_task_id=task.id,
                payload=task.payload,
                error=str(exc)[:2000],
            )
        )
        db.commit()


def ingest_bytes(
    db: Session,
    raw: bytes,
    filename: str | None = None,
    *,
    book: Optional[Book] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    source_class: str = "human_original",
) -> IngestResult:
    """Synchronous ingest: prepare + process + finalize in one transaction."""
    content_hash = _content_hash(raw)
    idem_key = _build_idempotency_key(book.id if book else None, content_hash)
    cached = db.scalars(
        select(Task).where(Task.idempotency_key == idem_key, Task.status == TaskStatus.SUCCESS)
    ).first()
    if cached and cached.result:
        result = IngestResult(**cached.result)
        result.idempotent = True
        return result

    prepared_book, source, task, ext = _prepare(
        db, raw, filename, book=book, title=title, author=author, genre=genre, source_class=source_class
    )
    try:
        task.status = TaskStatus.RUNNING
        task.started_at = _now()
        db.flush()
        result = _run_pipeline(db, raw, filename or "upload.txt", book=prepared_book, source=source)
        return _finalize_success(db, task, result)
    except Exception as exc:  # noqa: BLE001
        _fail(db, task, exc)
        raise


def enqueue_ingest(
    db: Session,
    raw: bytes,
    filename: str | None = None,
    *,
    book: Optional[Book] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    source_class: str = "human_original",
) -> Task:
    """Enqueue an ingest as a PENDING Task for the Worker to drain later."""
    content_hash = _content_hash(raw)
    idem_key = _build_idempotency_key(book.id if book else None, content_hash)
    cached = db.scalars(
        select(Task).where(Task.idempotency_key == idem_key, Task.status == TaskStatus.SUCCESS)
    ).first()
    if cached and cached.result:
        # Already done; surface the cached task so callers can poll its result.
        return cached
    prepared_book, _source, task, _ext = _prepare(
        db, raw, filename, book=book, title=title, author=author, genre=genre, source_class=source_class
    )
    db.commit()
    # Dispatch via Redis when available (spec §40); the DB task row is the
    # source of truth either way, and a Redis outage degrades to local scanning.
    from app.core.queue import get_queue

    try:
        get_queue().enqueue(task.id)
    except Exception:  # noqa: BLE001 — queue notification is best-effort
        pass
    return task


def process_task(db: Session, task: Task) -> IngestResult:
    """Execute one PENDING ingest Task (used by the Worker)."""
    payload = task.payload or {}
    book = db.get(Book, payload.get("book_id"))
    source = db.get(CorpusSource, payload.get("source_id"))
    if book is None or source is None or not source.raw_path:
        raise ValueError("ingest task references a missing source/book")
    raw = Path(source.raw_path).read_bytes()
    task.status = TaskStatus.RUNNING
    task.started_at = _now()
    db.flush()
    try:
        result = _run_pipeline(db, raw, payload.get("filename") or "upload.txt", book=book, source=source)
        return _finalize_success(db, task, result)
    except Exception as exc:  # noqa: BLE001
        _fail(db, task, exc)
        raise
