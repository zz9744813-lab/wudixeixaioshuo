"""Corpus & Book API (spec §39 Corpus)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import get_db
from app.models.corpus import Book, Scene, Chapter
from app.schemas.domain import BookCreate, BookOut

router = APIRouter(prefix="/api/v1", tags=["corpus"])


@router.post("/books", response_model=BookOut, status_code=201)
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    book = Book(
        id=new_id("BOOK"),
        title=payload.title,
        author=payload.author,
        genre=payload.genre,
        corpus_source_id=payload.corpus_source_id,
        metadata_=payload.metadata,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return _to_out(book, db)


@router.get("/books", response_model=list[BookOut])
def list_books(db: Session = Depends(get_db)):
    books = db.scalars(select(Book).order_by(Book.created_at.desc())).all()
    return [_to_out(b, db) for b in books]


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: str, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "book not found")
    return _to_out(book, db)


@router.get("/books/{book_id}/scenes")
def list_book_scenes(book_id: str, db: Session = Depends(get_db), limit: int = 200, offset: int = 0):
    if not db.get(Book, book_id):
        raise HTTPException(404, "book not found")
    rows = db.scalars(
        select(Scene).where(Scene.book_id == book_id).order_by(Scene.index).limit(limit).offset(offset)
    ).all()
    return [
        {
            "id": s.id,
            "index": s.index,
            "pov": s.pov,
            "location": s.location,
            "participants": s.participants,
            "narrative_functions": s.narrative_functions,
            "summary": s.summary,
            "analyzed": s.analyzed,
        }
        for s in rows
    ]


def _to_out(book: Book, db: Session) -> BookOut:
    chapter_count = db.scalar(select(func.count()).select_from(Chapter).where(Chapter.book_id == book.id)) or 0
    scene_count = db.scalar(select(func.count()).select_from(Scene).where(Scene.book_id == book.id)) or 0
    return BookOut(
        id=book.id, title=book.title, author=book.author, genre=book.genre,
        chapter_count=chapter_count, scene_count=scene_count,
    )
