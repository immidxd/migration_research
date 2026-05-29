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
            EXISTS (
                SELECT 1 FROM territories c
                WHERE c.parent_id = territories.id AND c.kind = 'region'
            ) AS is_container,
            EXTRACT(YEAR FROM valid_from)::int AS valid_year_from,
            EXTRACT(YEAR FROM valid_to)::int   AS valid_year_to,
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
                {k: v for k, v in r.items() if k not in ("geometry",)}
                for r in rows
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
                    "is_container": r["is_container"],
                    "valid_year_from": r["valid_year_from"],
                    "valid_year_to": r["valid_year_to"],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get(".labels")
def territory_label_points(
    kind: list[str] | None = Query(default=None),
    year: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """One label point per territory feature (not per polygon part).

    `ST_PointOnSurface` of the whole MultiPolygon gives a single point
    inside the largest part — perfect for placing a single readable label
    on a region that has many islands (e.g. Сибір with 15 sub-polygons,
    each previously getting its own duplicate label).

    When `year` is given, the name/name_local/status are taken from the
    matching territory_period (so Hawaii reads "Королівство Гаваї" before
    annexation and "Гаваї (США)" after), falling back to the base row."""
    where = []
    params: dict[str, Any] = {"yr": year}
    if kind:
        where.append("t.kind::text = ANY(:kinds)")
        params["kinds"] = kind
    sql = f"""
        SELECT
            t.id, t.kind, t.code, t.empire, t.is_umbrella_region,
            EXISTS (
                SELECT 1 FROM territories c
                WHERE c.parent_id = t.id AND c.kind = 'region'
            ) AS is_container,
            COALESCE(p.name, t.name) AS name,
            COALESCE(p.name_local, t.name_local) AS name_local,
            p.status AS period_status,
            ST_AsGeoJSON(ST_PointOnSurface(t.geom))::json AS pt
        FROM territories t
        LEFT JOIN LATERAL (
            SELECT name, name_local, status
            FROM territory_periods tp
            WHERE tp.territory_id = t.id
              AND :yr IS NOT NULL
              AND tp.year_from <= :yr AND tp.year_to >= :yr
            ORDER BY tp.year_from DESC
            LIMIT 1
        ) p ON true
        WHERE t.geom IS NOT NULL
              {('AND ' + ' AND '.join(where)) if where else ''}
    """
    rows = db.execute(text(sql), params).mappings().all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": r["id"],
                "geometry": r["pt"],
                "properties": {
                    "id": r["id"],
                    "kind": r["kind"],
                    "name": r["name"],
                    "name_local": r["name_local"],
                    "code": r["code"],
                    "empire": r["empire"],
                    "is_umbrella_region": r["is_umbrella_region"],
                    "is_container": r["is_container"],
                    "period_status": r["period_status"],
                },
            }
            for r in rows if r["pt"] is not None
        ],
    }


@router.get("/search")
def search_territories(
    q: str = "",
    kind: list[str] | None = Query(default=None),
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Typeahead across name, name_local, code AND aliases (UK / RU / EN).

    Matching an alias (territory_aliases) lets the Russian-named RiStat units be
    found by their Ukrainian or English forms (Полтавська / Poltava → Полтавская
    губерния). Results are de-duplicated and prefix/name matches rank first."""
    alias_match = (
        "EXISTS (SELECT 1 FROM territory_aliases a "
        "WHERE a.territory_id = t.id AND a.alias ILIKE :pat)"
    )
    where = []
    params: dict[str, Any] = {"pat": f"%{q}%", "q": q, "lim": min(limit, 100)}
    if q:
        where.append(
            f"(t.name ILIKE :pat OR t.name_local ILIKE :pat OR t.code ILIKE :pat OR {alias_match})"
        )
    if kind:
        where.append("t.kind::text = ANY(:kinds)")
        params["kinds"] = kind
    sql = f"""
        SELECT t.id, t.kind, t.name, t.name_local, t.code, t.empire, t.is_umbrella_region
        FROM territories t
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY
          CASE
            WHEN t.name ILIKE :q || '%' OR t.name_local ILIKE :q || '%' THEN 0
            WHEN t.name ILIKE :pat OR t.name_local ILIKE :pat THEN 1
            ELSE 2
          END,
          t.kind, t.name
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
            ) AS transit_profile,
            (
                SELECT json_agg(json_build_object(
                    'id', tp.id,
                    'year_from', tp.year_from,
                    'year_to', tp.year_to,
                    'status', tp.status,
                    'name', tp.name,
                    'name_local', tp.name_local,
                    'sovereign_id', tp.sovereign_id,
                    'notes', tp.notes
                ) ORDER BY tp.year_from)
                FROM territory_periods tp
                WHERE tp.territory_id = t.id
            ) AS periods,
            (
                SELECT json_agg(json_build_object(
                    'id', ts.id,
                    'stat_kind', ts.stat_kind,
                    'group_label', ts.group_label,
                    'as_of_year', ts.as_of_year,
                    'temporal_label_id', ts.temporal_label_id,
                    'count', ts.count,
                    'count_lower', ts.count_lower,
                    'count_upper', ts.count_upper,
                    'count_method', ts.count_method,
                    'provisional', ts.provisional,
                    'notes', ts.notes
                ) ORDER BY ts.as_of_year)
                FROM territory_stats ts
                WHERE ts.territory_id = t.id
            ) AS stats
        FROM territories t
        WHERE t.id = :tid
    """
    row = db.execute(text(sql), {"tid": territory_id}).mappings().first()
    if not row:
        raise HTTPException(404, "territory not found")
    return dict(row)
