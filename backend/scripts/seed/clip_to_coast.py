"""Clip land territories to the coastline so their fills stop exactly at the
sea instead of bleeding into the water (our historical polygons were digitised
at a coarser resolution than the CARTO basemap).

Mask: Natural Earth 1:10m land (public domain), subdivided + GIST-indexed for
fast per-territory intersection.

Reversible: each territory's ORIGINAL geometry is backed up once into
`territory_geom_orig`; clipping always derives from that backup, so the seeder
is idempotent and the originals can be restored. Restore with:
    UPDATE territories t SET geom = o.geom
    FROM territory_geom_orig o WHERE t.id = o.territory_id;

Run after the geometry seeders. Clips kinds: region, gubernia, uezd, subdivision.
"""
from __future__ import annotations

import logging
import zipfile

from sqlalchemy import text

from backend.app.settings import PROJECT_ROOT
from backend.models import SessionLocal

logger = logging.getLogger("migrations.seed")

LAND_ZIP = PROJECT_ROOT / "data" / "territories" / "raw" / "ne_10m_land.zip"
CLIP_KINDS = ("region", "gubernia", "uezd", "subdivision")


def _load_land_mask(db) -> None:
    """(Re)build _coast_land: NE 1:10m land, subdivided + GIST-indexed."""
    import pyogrio

    vsi = f"/vsizip/{LAND_ZIP}/ne_10m_land.shp"
    gdf = pyogrio.read_dataframe(vsi)
    db.execute(text("DROP TABLE IF EXISTS _coast_land_raw"))
    db.execute(text("CREATE TABLE _coast_land_raw (geom geometry(Geometry,4326))"))
    for geom in gdf.geometry:
        if geom is None:
            continue
        db.execute(
            text("INSERT INTO _coast_land_raw (geom) VALUES (ST_GeomFromWKB(:wkb, 4326))"),
            {"wkb": bytes(geom.wkb)},
        )
    db.execute(text("DROP TABLE IF EXISTS _coast_land"))
    db.execute(text("""
        CREATE TABLE _coast_land AS
        SELECT ST_Subdivide(ST_MakeValid(geom), 512) AS geom FROM _coast_land_raw
    """))
    db.execute(text("CREATE INDEX ix_coast_land_gist ON _coast_land USING gist (geom)"))
    db.execute(text("DROP TABLE _coast_land_raw"))
    n = db.execute(text("SELECT count(*) FROM _coast_land")).scalar()
    logger.info("coast land mask: %d subdivided pieces", n)


def _ensure_backup(db) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS territory_geom_orig (
            territory_id integer PRIMARY KEY REFERENCES territories(id) ON DELETE CASCADE,
            geom geometry(Geometry,4326)
        )
    """))
    n = db.execute(text("""
        INSERT INTO territory_geom_orig (territory_id, geom)
        SELECT id, geom FROM territories
        WHERE kind::text = ANY(:kinds) AND geom IS NOT NULL
        ON CONFLICT (territory_id) DO NOTHING
        RETURNING territory_id
    """), {"kinds": list(CLIP_KINDS)}).rowcount
    logger.info("backed up %d original geometries", n)


def run() -> None:
    if not LAND_ZIP.exists():
        logger.warning("land mask %s missing — skipping coastline clip", LAND_ZIP)
        return
    db = SessionLocal()
    try:
        _load_land_mask(db)
        _ensure_backup(db)
        # Clip from the ORIGINAL backup geometry (idempotent). Intersect only
        # with land pieces whose bbox overlaps the territory (&& uses the GIST
        # index), keep polygonal output only.
        res = db.execute(text("""
            UPDATE territories t
            SET geom = ST_Multi(ST_CollectionExtract(
                ST_MakeValid(ST_Intersection(
                    o.geom,
                    (SELECT ST_Union(c.geom) FROM _coast_land c WHERE c.geom && o.geom)
                )), 3))
            FROM territory_geom_orig o
            WHERE t.id = o.territory_id
              AND t.kind::text = ANY(:kinds)
              AND o.geom IS NOT NULL
              AND NOT ST_IsEmpty(COALESCE(
                    (SELECT ST_Union(c.geom) FROM _coast_land c WHERE c.geom && o.geom),
                    ST_GeomFromText('POLYGON EMPTY',4326)))
        """), {"kinds": list(CLIP_KINDS)})
        db.commit()
        logger.info("clipped %d territories to coastline", res.rowcount)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
