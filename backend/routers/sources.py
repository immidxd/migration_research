from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db


router = APIRouter(prefix="/api/sources", tags=["sources"])


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
