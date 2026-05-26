"""Migration flows CRUD."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db
from backend.models.flows import MigrationFlow
from backend.models.source_links import FlowSource
from backend.schemas.flows import FlowCreate, FlowOut, FlowUpdate


router = APIRouter(prefix="/api/migration-flows", tags=["flows"])


_LIST_SQL = """
    SELECT
        f.id,
        f.origin_territory_id,
        o.name AS origin_name,
        f.destination_territory_id,
        d.name AS destination_name,
        f.temporal_label_id,
        tl.label AS temporal_label,
        f.date_from, f.date_to, f.date_precision,
        f.count, f.count_lower, f.count_upper, f.count_method,
        f.vector, f.transport_mode,
        f.origin_precision, f.destination_precision,
        f.provisional, f.notes,
        f.created_at, f.updated_at,
        COALESCE((
            SELECT json_agg(json_build_object(
                'source_id', fs.source_id,
                'short_title', s.short_title,
                'note', fs.note
            ))
            FROM flow_sources fs
            JOIN sources s ON s.id = fs.source_id
            WHERE fs.flow_id = f.id
        ), '[]'::json) AS sources
    FROM migration_flows f
    JOIN territories o ON o.id = f.origin_territory_id
    JOIN territories d ON d.id = f.destination_territory_id
    LEFT JOIN temporal_labels tl ON tl.id = f.temporal_label_id
"""


@router.get("", response_model=list[FlowOut])
def list_flows(
    vector: list[str] | None = Query(default=None),
    origin_id: int | None = None,
    destination_id: int | None = None,
    covering_year: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    where = []
    params: dict[str, Any] = {"lim": min(limit, 1000)}
    if vector:
        where.append("f.vector::text = ANY(:vectors)")
        params["vectors"] = vector
    if origin_id is not None:
        where.append("f.origin_territory_id = :oid")
        params["oid"] = origin_id
    if destination_id is not None:
        where.append("f.destination_territory_id = :did")
        params["did"] = destination_id
    if covering_year is not None:
        # Match flows whose canonical date range overlaps the year.
        where.append(
            "((f.date_from IS NULL OR EXTRACT(YEAR FROM f.date_from) <= :y) "
            "AND (f.date_to IS NULL OR EXTRACT(YEAR FROM f.date_to) >= :y))"
        )
        params["y"] = covering_year

    sql = f"{_LIST_SQL} {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY f.created_at DESC LIMIT :lim"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{flow_id}", response_model=FlowOut)
def get_flow(flow_id: int, db: Session = Depends(get_db)):
    sql = f"{_LIST_SQL} WHERE f.id = :i"
    row = db.execute(text(sql), {"i": flow_id}).mappings().first()
    if not row:
        raise HTTPException(404, "flow not found")
    return dict(row)


@router.post("", response_model=FlowOut, status_code=201)
def create_flow(payload: FlowCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"sources"})
    # Auto-provisional if no sources were attached.
    data["provisional"] = len(payload.sources) == 0

    flow = MigrationFlow(**data)
    db.add(flow)
    db.flush()  # populate id

    for s in payload.sources:
        db.add(FlowSource(flow_id=flow.id, source_id=s.source_id, note=s.note))

    db.commit()
    db.refresh(flow)
    return get_flow(flow.id, db)


@router.patch("/{flow_id}", response_model=FlowOut)
def update_flow(flow_id: int, payload: FlowUpdate, db: Session = Depends(get_db)):
    flow = db.get(MigrationFlow, flow_id)
    if not flow:
        raise HTTPException(404, "flow not found")

    updates = payload.model_dump(exclude_unset=True, exclude={"sources"})
    for k, v in updates.items():
        setattr(flow, k, v)

    if payload.sources is not None:
        # Replace M2M wholesale on explicit request.
        db.execute(
            text("DELETE FROM flow_sources WHERE flow_id = :i"), {"i": flow_id}
        )
        for s in payload.sources:
            db.add(FlowSource(flow_id=flow_id, source_id=s.source_id, note=s.note))
        # Recompute provisional based on the new source set.
        if not payload.sources:
            flow.provisional = True

    db.commit()
    return get_flow(flow_id, db)


@router.delete("/{flow_id}", status_code=204)
def delete_flow(flow_id: int, db: Session = Depends(get_db)):
    flow = db.get(MigrationFlow, flow_id)
    if not flow:
        raise HTTPException(404, "flow not found")
    db.delete(flow)
    db.commit()
