"""Territories API — list + detail + GeoJSON FeatureCollection.

Geometry is serialised via PostGIS ST_AsGeoJSON for speed; we don't load
SQLAlchemy ORM objects when the client only needs a map layer.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db


router = APIRouter(prefix="/api/territories", tags=["territories"])


VALID_KINDS = {
    "settlement", "volost", "uezd", "gubernia", "region",
    "country", "subdivision", "port", "station", "border_crossing",
}
VALID_EMPIRES = {"russian_empire", "austro_hungarian", "other"}


@router.get("")
def list_territories(
    kind: list[str] | None = Query(default=None),
    empire: list[str] | None = Query(default=None),
    format: str = Query(default="geojson", pattern="^(geojson|table)$"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List territories.

    `format=geojson` → FeatureCollection (default; what the map uses).
    `format=table`   → flat array of dicts (for sidebar lists).
    """
    if kind:
        unknown = set(kind) - VALID_KINDS
        if unknown:
            raise HTTPException(400, f"unknown kind(s): {sorted(unknown)}")
    if empire:
        unknown = set(empire) - VALID_EMPIRES
        if unknown:
            raise HTTPException(400, f"unknown empire(s): {sorted(unknown)}")

    where = []
    params: dict[str, Any] = {}
    if kind:
        where.append("kind::text = ANY(:kinds)")
        params["kinds"] = kind
    if empire:
        where.append("empire::text = ANY(:empires)")
        params["empires"] = empire

    sql = f"""
        SELECT
            id, kind, name, name_local, code, empire,
            is_umbrella_region,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM territories
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY kind, name
    """
    rows = db.execute(text(sql), params).mappings().all()

    if format == "table":
        # Drop geometry to keep the payload light for sidebar lists.
        return {
            "items": [
                {k: v for k, v in r.items() if k != "geometry"} for r in rows
            ],
            "count": len(rows),
        }

    features = []
    for r in rows:
        if r["geometry"] is None:
            continue
        features.append(
            {
                "type": "Feature",
                "id": r["id"],
                "geometry": r["geometry"],
                "properties": {
                    "id": r["id"],
                    "kind": r["kind"],
                    "name": r["name"],
                    "name_local": r["name_local"],
                    "code": r["code"],
                    "empire": r["empire"],
                    "is_umbrella_region": r["is_umbrella_region"],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/search")
def search_territories(
    q: str = "",
    kind: list[str] | None = Query(default=None),
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Typeahead by name, name_local, or code. Case-insensitive."""
    where = []
    params: dict[str, Any] = {"pat": f"%{q}%", "q": q, "lim": min(limit, 100)}
    if q:
        where.append("(name ILIKE :pat OR name_local ILIKE :pat OR code ILIKE :pat)")
    if kind:
        where.append("kind::text = ANY(:kinds)")
        params["kinds"] = kind
    sql = f"""
        SELECT id, kind, name, name_local, code, empire, is_umbrella_region
        FROM territories
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY
          CASE WHEN name ILIKE :pat THEN 0 ELSE 1 END,
          kind, name
        LIMIT :lim
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{territory_id}")
def get_territory(territory_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    sql = """
        SELECT
            t.id, t.kind, t.name, t.name_local, t.code, t.empire,
            t.is_umbrella_region, t.notes,
            t.valid_from, t.valid_to,
            ST_AsGeoJSON(t.geom)::json AS geometry,
            (
                SELECT json_agg(json_build_object(
                    'id', s.id,
                    'short_title', s.short_title,
                    'citation', s.citation,
                    'kind', s.kind,
                    'year', s.year,
                    'url', s.url,
                    'note', ts.note
                ))
                FROM territory_sources ts
                JOIN sources s ON s.id = ts.source_id
                WHERE ts.territory_id = t.id
            ) AS sources,
            (
                SELECT row_to_json(p)
                FROM transit_point_profiles p
                WHERE p.territory_id = t.id
            ) AS transit_profile
        FROM territories t
        WHERE t.id = :tid
    """
    row = db.execute(text(sql), {"tid": territory_id}).mappings().first()
    if not row:
        raise HTTPException(404, "territory not found")
    return dict(row)
