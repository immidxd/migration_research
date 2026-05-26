from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.models.sources import Source
from backend.schemas.sources import SourceCreate, SourceOut


router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    src = Source(**payload.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


@router.get("/search")
def search_sources(q: str = "", limit: int = 20, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Typeahead. Empty `q` returns the most recent N sources."""
    sql = """
        SELECT id, short_title, citation, kind, year
        FROM sources
        WHERE :q = '' OR short_title ILIKE :pat OR citation ILIKE :pat OR author ILIKE :pat
        ORDER BY id DESC
        LIMIT :lim
    """
    rows = db.execute(
        text(sql), {"q": q, "pat": f"%{q}%", "lim": min(limit, 100)}
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("")
def list_sources(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            "SELECT id, short_title, citation, kind, author, year, url, accessed_on "
            "FROM sources ORDER BY short_title"
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.execute(
        text(
            "SELECT id, short_title, citation, kind, author, year, url, "
            "accessed_on, notes FROM sources WHERE id = :sid"
        ),
        {"sid": source_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "source not found")
    return dict(row)
