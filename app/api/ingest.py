"""Ingestion API (spec §6, §39 Corpus).

Two entry points:

* ``POST /api/v1/corpus/ingest`` — full source→book flow (§6.2): registers an
  immutable ``CorpusSource``, creates a ``Book`` and splits it into
  ``Chapter`` / ``Scene`` / ``SceneSpan`` rows.
* ``POST /api/v1/books/{book_id}/ingest`` — ingest a file into an existing Book.

Both are deterministic and idempotent: re-submitting identical bytes yields the
same Book (no duplicate chapters). Parsing is rule-based and LLM-free (EPIC-B).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingest.service import ingest_bytes
from app.models.corpus import Book
from app.schemas.domain import IngestResultOut

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/corpus/ingest", response_model=IngestResultOut, status_code=201)
def ingest_corpus(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    genre: str | None = Form(None),
    source_class: str = Form("human_original"),
    db: Session = Depends(get_db),
):
    raw = file.file.read()
    if not raw:
        raise HTTPException(400, "empty upload")
    result = ingest_bytes(
        db, raw, file.filename, title=title, author=author, genre=genre, source_class=source_class
    )
    return result.to_dict()


@router.post("/books/{book_id}/ingest", response_model=IngestResultOut, status_code=201)
def ingest_book(
    book_id: str,
    file: UploadFile = File(...),
    source_class: str = Form("human_original"),
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "book not found")
    raw = file.file.read()
    if not raw:
        raise HTTPException(400, "empty upload")
    result = ingest_bytes(db, raw, file.filename, book=book, source_class=source_class)
    return result.to_dict()
