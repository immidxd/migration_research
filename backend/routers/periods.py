from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db


router = APIRouter(prefix="/api/periods", tags=["periods"])


@router.get("")
def list_periods(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            "SELECT id, slug, name, date_from, date_to, description "
            "FROM periods ORDER BY date_from"
        )
    ).mappings().all()
    return [dict(r) for r in rows]
