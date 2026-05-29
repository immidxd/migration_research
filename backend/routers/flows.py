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


def _year_overlap_clause(
    where: list[str],
    params: dict[str, Any],
    covering_year: int | None,
    from_year: int | None,
    to_year: int | None,
) -> None:
    """Append a temporal-overlap predicate to `where`/`params` in place.

    A flow's canonical [date_from, date_to] range is matched against the
    requested window. NULL endpoints are treated as open-ended. `covering_year`
    is the single-year shorthand for from_year == to_year."""
    if covering_year is not None and from_year is None and to_year is None:
        from_year = to_year = covering_year
    if from_year is None and to_year is None:
        return
    if from_year is not None:
        where.append("(f.date_to IS NULL OR EXTRACT(YEAR FROM f.date_to) >= :y_from)")
        params["y_from"] = from_year
    if to_year is not None:
        where.append("(f.date_from IS NULL OR EXTRACT(YEAR FROM f.date_from) <= :y_to)")
        params["y_to"] = to_year


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
    from_year: int | None = None,
    to_year: int | None = None,
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
    _year_overlap_clause(where, params, covering_year, from_year, to_year)

    sql = f"{_LIST_SQL} {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY f.created_at DESC LIMIT :lim"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get(".geojson")
def list_flows_geojson(
    vector: list[str] | None = Query(default=None),
    covering_year: int | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return flows as a GeoJSON FeatureCollection of LineStrings.

    Geometry is a straight line between origin and destination centroids
    (computed by PostGIS). Curves are added client-side as a styling choice
    so server payload stays small.
    """
    where = []
    params: dict[str, Any] = {"lim": min(limit, 5000)}
    if vector:
        where.append("f.vector::text = ANY(:vectors)")
        params["vectors"] = vector
    _year_overlap_clause(where, params, covering_year, from_year, to_year)

    sql = f"""
        SELECT
            f.id, f.vector, f.transport_mode,
            f.count, f.count_lower, f.count_upper, f.count_method,
            f.origin_precision, f.destination_precision,
            f.provisional, f.date_precision,
            f.date_from, f.date_to,
            tl.label AS temporal_label,
            o.name AS origin_name, d.name AS destination_name,
            ST_X(ST_Centroid(o.geom)) AS o_lon,
            ST_Y(ST_Centroid(o.geom)) AS o_lat,
            ST_X(ST_Centroid(d.geom)) AS d_lon,
            ST_Y(ST_Centroid(d.geom)) AS d_lat,
            (SELECT COUNT(*) FROM flow_sources fs WHERE fs.flow_id = f.id) AS source_count
        FROM migration_flows f
        JOIN territories o ON o.id = f.origin_territory_id
        JOIN territories d ON d.id = f.destination_territory_id
        LEFT JOIN temporal_labels tl ON tl.id = f.temporal_label_id
        WHERE o.geom IS NOT NULL AND d.geom IS NOT NULL
              {('AND ' + ' AND '.join(where)) if where else ''}
        ORDER BY f.id DESC
        LIMIT :lim
    """
    rows = db.execute(text(sql), params).mappings().all()

    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "id": r["id"],
            "geometry": {
                "type": "LineString",
                "coordinates": [[r["o_lon"], r["o_lat"]], [r["d_lon"], r["d_lat"]]],
            },
            "properties": {
                "id": r["id"],
                "vector": r["vector"],
                "transport_mode": r["transport_mode"],
                "count": r["count"],
                "count_lower": r["count_lower"],
                "count_upper": r["count_upper"],
                "count_method": r["count_method"],
                "origin_name": r["origin_name"],
                "destination_name": r["destination_name"],
                "temporal_label": r["temporal_label"],
                "date_from": r["date_from"].isoformat() if r["date_from"] else None,
                "date_to": r["date_to"].isoformat() if r["date_to"] else None,
                "date_precision": r["date_precision"],
                "provisional": r["provisional"],
                "source_count": r["source_count"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


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
