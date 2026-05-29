"""Flow relations API (Group E core).

CRUD over user-confirmed relationships between flows, plus a candidate
suggester that proposes likely relations from the territory hierarchy, period
overlap and shared vector. Suggestions are computed live and never stored
until the user confirms (POSTs) one.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.models.flow_relations import FlowRelation
from backend.schemas.relations import RelationCandidate, RelationCreate, RelationOut


router = APIRouter(prefix="/api/flow-relations", tags=["relations"])


_LIST_SQL = """
    SELECT
        r.id, r.kind, r.note, r.created_at,
        r.from_flow_id, fo.name || ' → ' || fd.name AS from_label,
        r.to_flow_id,   to_.name || ' → ' || td.name AS to_label
    FROM flow_relations r
    JOIN migration_flows f1 ON f1.id = r.from_flow_id
    JOIN territories fo ON fo.id = f1.origin_territory_id
    JOIN territories fd ON fd.id = f1.destination_territory_id
    JOIN migration_flows f2 ON f2.id = r.to_flow_id
    JOIN territories to_ ON to_.id = f2.origin_territory_id
    JOIN territories td ON td.id = f2.destination_territory_id
"""


@router.get("", response_model=list[RelationOut])
def list_relations(flow_id: int | None = None, db: Session = Depends(get_db)):
    where = ""
    params: dict[str, Any] = {}
    if flow_id is not None:
        where = "WHERE r.from_flow_id = :fid OR r.to_flow_id = :fid"
        params["fid"] = flow_id
    rows = db.execute(text(f"{_LIST_SQL} {where} ORDER BY r.created_at DESC"), params).mappings().all()
    return [dict(r) for r in rows]


@router.post("", response_model=RelationOut, status_code=201)
def create_relation(payload: RelationCreate, db: Session = Depends(get_db)):
    for fid in (payload.from_flow_id, payload.to_flow_id):
        exists = db.execute(
            text("SELECT 1 FROM migration_flows WHERE id = :i"), {"i": fid}
        ).first()
        if not exists:
            raise HTTPException(404, f"flow {fid} not found")
    rel = FlowRelation(
        from_flow_id=payload.from_flow_id,
        to_flow_id=payload.to_flow_id,
        kind=payload.kind,
        note=payload.note,
    )
    db.add(rel)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "relation already exists")
    row = db.execute(text(f"{_LIST_SQL} WHERE r.id = :i"), {"i": rel.id}).mappings().first()
    return dict(row)


@router.delete("/{relation_id}", status_code=204)
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    rel = db.get(FlowRelation, relation_id)
    if not rel:
        raise HTTPException(404, "relation not found")
    db.delete(rel)
    db.commit()


# Candidate suggester. Uses an ancestor closure over territories.parent_id to
# decide place containment, then proposes a relation kind. Only flows that
# share the vector and have overlapping periods are considered.
_CANDIDATES_SQL = """
    WITH RECURSIVE anc AS (
        SELECT id AS tid, id AS aid FROM territories
        UNION ALL
        SELECT a.tid, t.parent_id
        FROM anc a JOIN territories t ON t.id = a.aid
        WHERE t.parent_id IS NOT NULL
    ),
    f AS (
        SELECT origin_territory_id AS o, destination_territory_id AS d,
               date_from, date_to, vector
        FROM migration_flows WHERE id = :fid
    )
    SELECT
        g.id AS other_flow_id,
        og.name || ' → ' || dg.name AS other_label,
        g.count AS other_count,
        CASE WHEN g.date_from IS NOT NULL
             THEN EXTRACT(YEAR FROM g.date_from)::text || '–' || COALESCE(EXTRACT(YEAR FROM g.date_to)::text, '?')
             ELSE NULL END AS other_period,
        g.origin_territory_id AS g_o,
        g.destination_territory_id AS g_d,
        f.o AS f_o, f.d AS f_d,
        -- place-containment flags
        (g.origin_territory_id = f.o AND g.destination_territory_id = f.d) AS same_place,
        EXISTS(SELECT 1 FROM anc WHERE tid = f.o AND aid = g.origin_territory_id)
          AND EXISTS(SELECT 1 FROM anc WHERE tid = f.d AND aid = g.destination_territory_id) AS g_contains_f,
        EXISTS(SELECT 1 FROM anc WHERE tid = g.origin_territory_id AND aid = f.o)
          AND EXISTS(SELECT 1 FROM anc WHERE tid = g.destination_territory_id AND aid = f.d) AS f_contains_g
    FROM migration_flows g
    JOIN f ON true
    JOIN territories og ON og.id = g.origin_territory_id
    JOIN territories dg ON dg.id = g.destination_territory_id
    WHERE g.id <> :fid
      AND g.vector = f.vector
      -- period overlap (NULL endpoints are open-ended)
      AND (f.date_from IS NULL OR g.date_to IS NULL OR g.date_to >= f.date_from)
      AND (f.date_to IS NULL OR g.date_from IS NULL OR g.date_from <= f.date_to)
      -- exclude pairs that already have any relation
      AND NOT EXISTS (
          SELECT 1 FROM flow_relations r
          WHERE (r.from_flow_id = :fid AND r.to_flow_id = g.id)
             OR (r.from_flow_id = g.id AND r.to_flow_id = :fid)
      )
    ORDER BY g.count DESC NULLS LAST, g.id DESC
    LIMIT 50
"""


@router.get("/candidates", response_model=list[RelationCandidate])
def relation_candidates(flow_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text(_CANDIDATES_SQL), {"fid": flow_id}).mappings().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        if r["same_place"]:
            kind, frm, to = "equals", flow_id, r["other_flow_id"]
            reason = "той самий вихід і прибуття, періоди перетинаються"
        elif r["g_contains_f"]:
            # g's places are ancestors of f's → g contains f
            kind, frm, to = "contains", r["other_flow_id"], flow_id
            reason = "ширша територія охоплює цей потік (за ієрархією)"
        elif r["f_contains_g"]:
            kind, frm, to = "contains", flow_id, r["other_flow_id"]
            reason = "цей потік ширший і охоплює інший (за ієрархією)"
        else:
            kind, frm, to = "overlaps_unknown", flow_id, r["other_flow_id"]
            reason = "період і вектор перетинаються, місця не вкладені"
        out.append({
            "other_flow_id": r["other_flow_id"],
            "other_label": r["other_label"],
            "other_count": r["other_count"],
            "other_period": r["other_period"],
            "from_flow_id": frm,
            "to_flow_id": to,
            "kind": kind,
            "reason": reason,
        })
    return out
