"""Territorial stock facts (territory_stats) + read access to territory periods.

A "stat" is a stock/snapshot ("10,000 Ukrainians in Canada as of 1908") — a
fact the user enters, with the same sources-first discipline as flows: no
source => provisional.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.models.temporal_facts import TerritoryStat
from backend.models.source_links import TerritoryStatSource
from backend.schemas.stats import PeriodOut, StatCreate, StatOut, StatUpdate


router = APIRouter(prefix="/api", tags=["stats"])


_STAT_SQL = """
    SELECT
        s.id, s.territory_id, t.name AS territory_name,
        s.stat_kind, s.group_label,
        s.as_of_year, s.temporal_label_id, tl.label AS temporal_label,
        s.count, s.count_lower, s.count_upper, s.count_method,
        s.provisional, s.notes, s.created_at, s.updated_at,
        COALESCE((
            SELECT json_agg(json_build_object(
                'source_id', ss.source_id,
                'short_title', src.short_title,
                'note', ss.note
            ))
            FROM territory_stat_sources ss
            JOIN sources src ON src.id = ss.source_id
            WHERE ss.stat_id = s.id
        ), '[]'::json) AS sources
    FROM territory_stats s
    JOIN territories t ON t.id = s.territory_id
    LEFT JOIN temporal_labels tl ON tl.id = s.temporal_label_id
"""


@router.get("/territory-stats", response_model=list[StatOut])
def list_stats(
    territory_id: int | None = None,
    stat_kind: list[str] | None = Query(default=None),
    covering_year: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    where = []
    params: dict[str, Any] = {"lim": min(limit, 1000)}
    if territory_id is not None:
        where.append("s.territory_id = :tid")
        params["tid"] = territory_id
    if stat_kind:
        where.append("s.stat_kind::text = ANY(:kinds)")
        params["kinds"] = stat_kind
    if covering_year is not None:
        where.append(
            "(s.as_of_year = :y OR (tl.year_from <= :y AND tl.year_to >= :y))"
        )
        params["y"] = covering_year
    sql = f"{_STAT_SQL} {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY s.as_of_year DESC NULLS LAST, s.id DESC LIMIT :lim"
    return [dict(r) for r in db.execute(text(sql), params).mappings().all()]


@router.get("/territory-stats/{stat_id}", response_model=StatOut)
def get_stat(stat_id: int, db: Session = Depends(get_db)):
    row = db.execute(text(f"{_STAT_SQL} WHERE s.id = :i"), {"i": stat_id}).mappings().first()
    if not row:
        raise HTTPException(404, "stat not found")
    return dict(row)


@router.post("/territory-stats", response_model=StatOut, status_code=201)
def create_stat(payload: StatCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"sources"})
    data["provisional"] = len(payload.sources) == 0
    stat = TerritoryStat(**data)
    db.add(stat)
    db.flush()
    for s in payload.sources:
        db.add(TerritoryStatSource(stat_id=stat.id, source_id=s.source_id, note=s.note))
    db.commit()
    return get_stat(stat.id, db)


@router.patch("/territory-stats/{stat_id}", response_model=StatOut)
def update_stat(stat_id: int, payload: StatUpdate, db: Session = Depends(get_db)):
    stat = db.get(TerritoryStat, stat_id)
    if not stat:
        raise HTTPException(404, "stat not found")
    updates = payload.model_dump(exclude_unset=True, exclude={"sources"})
    for k, v in updates.items():
        setattr(stat, k, v)
    if payload.sources is not None:
        db.execute(text("DELETE FROM territory_stat_sources WHERE stat_id = :i"), {"i": stat_id})
        for s in payload.sources:
            db.add(TerritoryStatSource(stat_id=stat_id, source_id=s.source_id, note=s.note))
        if not payload.sources:
            stat.provisional = True
    db.commit()
    return get_stat(stat_id, db)


@router.delete("/territory-stats/{stat_id}", status_code=204)
def delete_stat(stat_id: int, db: Session = Depends(get_db)):
    stat = db.get(TerritoryStat, stat_id)
    if not stat:
        raise HTTPException(404, "stat not found")
    db.delete(stat)
    db.commit()


@router.get("/territory-periods", response_model=list[PeriodOut])
def list_periods(
    territory_id: int | None = None,
    covering_year: int | None = None,
    db: Session = Depends(get_db),
):
    where = []
    params: dict[str, Any] = {}
    if territory_id is not None:
        where.append("territory_id = :tid")
        params["tid"] = territory_id
    if covering_year is not None:
        where.append("year_from <= :y AND year_to >= :y")
        params["y"] = covering_year
    sql = f"""
        SELECT id, territory_id, year_from, year_to, status, name, name_local,
               sovereign_id, notes
        FROM territory_periods
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY year_from
    """
    return [dict(r) for r in db.execute(text(sql), params).mappings().all()]
