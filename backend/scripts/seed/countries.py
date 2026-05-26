"""Import country polygons from Natural Earth 1:50m Cultural Vectors.

Natural Earth is the standard open dataset for modern country boundaries.
For historical territories (gubernias, empires) we need other sources;
this importer ONLY handles present-day countries used as destinations and
intermediate territories.

Run once; idempotent on `Territory.code = ISO_A3`.
"""
from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import shape as shapely_shape
from sqlalchemy import select

from backend.app.settings import PROJECT_ROOT
from backend.models.enums import TerritoryKind
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


NE_URL = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"
RAW_DIR = PROJECT_ROOT / "data" / "territories" / "raw"
ZIP_PATH = RAW_DIR / "ne_50m_admin_0_countries.zip"


def _ensure_downloaded() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 1024:
        return ZIP_PATH
    logger.info("downloading %s", NE_URL)
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        resp = client.get(NE_URL)
        resp.raise_for_status()
        ZIP_PATH.write_bytes(resp.content)
    return ZIP_PATH


def _load_features() -> list[dict]:
    """Return list of {name, iso_a2, iso_a3, geometry} dicts.

    Uses pyogrio directly to avoid pulling the full geopandas stack into
    memory when we only need three fields per feature.
    """
    import pyogrio

    path = _ensure_downloaded()
    # pyogrio reads from a /vsizip/ path
    vsi = f"/vsizip/{path}/ne_50m_admin_0_countries.shp"
    table = pyogrio.read_dataframe(vsi, columns=["NAME", "ISO_A2", "ISO_A3"])
    out: list[dict] = []
    for row in table.itertuples(index=False):
        geom = row.geometry if hasattr(row, "geometry") else None
        if geom is None or row.NAME is None:
            continue
        out.append(
            {
                "name": row.NAME,
                "iso_a2": (row.ISO_A2 or "").strip() or None,
                "iso_a3": (row.ISO_A3 or "").strip() or None,
                "geometry": geom,
            }
        )
    return out


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Natural Earth 1:50m Admin 0 Countries",
            citation="Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com",
            kind="dataset",
            url="https://www.naturalearthdata.com/downloads/50m-cultural-vectors/",
            year=2023,
        )

        features = _load_features()
        logger.info("loaded %d country features", len(features))

        inserted = 0
        skipped = 0
        for f in features:
            code = f["iso_a3"] or f["iso_a2"]
            if not code:
                logger.warning("skipping %s — no ISO code", f["name"])
                continue

            existing = db.execute(
                select(Territory).where(Territory.code == code)
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            geom_wkb = from_shape(f["geometry"], srid=4326)
            territory = Territory(
                kind=TerritoryKind.COUNTRY,
                name=f["name"],
                name_local=None,
                code=code,
                geom=geom_wkb,
            )
            db.add(territory)
            db.flush()
            db.add(TerritorySource(territory_id=territory.id, source_id=src.id))
            inserted += 1

        logger.info("countries: inserted=%d skipped=%d", inserted, skipped)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
