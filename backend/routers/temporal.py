"""Temporal labels API.

Returns labels filterable by kind or covering a specific year. Used by
the timeline UI for both the label picker and for resolving "which named
period contains 1893?" lookups.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db


router = APIRouter(prefix="/api/temporal-labels", tags=["temporal"])


VALID_KINDS = {
    "year", "decade", "quarter_century", "half_century",
    "century", "era_label", "named_period",
}


@router.get("")
def list_labels(
    kind: list[str] | None = Query(default=None),
    covering_year: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List labels, optionally filtered by kind and/or by a year they cover."""
    if kind:
        unknown = set(kind) - VALID_KINDS
        if unknown:
            raise HTTPException(400, f"unknown kind(s): {sorted(unknown)}")

    where = []
    params: dict[str, Any] = {}
    if kind:
        where.append("kind::text = ANY(:kinds)")
        params["kinds"] = kind
    if covering_year is not None:
        where.append("year_from <= :y AND year_to >= :y")
        params["y"] = covering_year

    sql = f"""
        SELECT id, slug, label, kind, year_from, year_to, description
        FROM temporal_labels
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY kind, year_from, year_to
    """
    return [dict(r) for r in db.execute(text(sql), params).mappings().all()]


@router.get("/{label_id}")
def get_label(label_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.execute(
        text(
            "SELECT id, slug, label, kind, year_from, year_to, description "
            "FROM temporal_labels WHERE id = :i"
        ),
        {"i": label_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "label not found")
    return dict(row)
