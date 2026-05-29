"""Import US states and Canadian provinces from Natural Earth admin_1.

These are destinations / continuation points for transatlantic migration —
the user records arrivals at the state/province level (and later cities).
Stored as Territory rows of kind SUBDIVISION, parented to the country
(USA / CAN) that was seeded by `countries.py`.

Run AFTER `countries`, so the parent country rows exist:
    python -m backend.scripts.seed_all countries subdivisions

Idempotent on `Territory.code` (= ISO 3166-2, e.g. "US-NY", "CA-MB").
"""
from __future__ import annotations

import logging
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


NE_URL = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_1_states_provinces.zip"
RAW_DIR = PROJECT_ROOT / "data" / "territories" / "raw"
ZIP_PATH = RAW_DIR / "ne_50m_admin_1_states_provinces.zip"

# adm0_a3 codes we want subdivisions for, mapped to the parent country's
# `Territory.code` (ISO_A3) as seeded by countries.py.
WANTED = {"USA": "USA", "CAN": "CAN"}


def _ensure_downloaded() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 1024:
        return ZIP_PATH
    logger.info("downloading %s", NE_URL)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        resp = client.get(NE_URL)
        resp.raise_for_status()
        ZIP_PATH.write_bytes(resp.content)
    return ZIP_PATH


def _load_features() -> list[dict]:
    import pyogrio

    path = _ensure_downloaded()
    vsi = f"/vsizip/{path}/ne_50m_admin_1_states_provinces.shp"
    table = pyogrio.read_dataframe(
        vsi, columns=["name", "iso_3166_2", "adm0_a3", "admin"]
    )
    out: list[dict] = []
    for row in table.itertuples(index=False):
        geom = row.geometry if hasattr(row, "geometry") else None
        adm0 = (getattr(row, "adm0_a3", None) or "").strip()
        if geom is None or row.name is None or adm0 not in WANTED:
            continue
        out.append(
            {
                "name": row.name,
                "iso_3166_2": (getattr(row, "iso_3166_2", None) or "").strip() or None,
                "adm0_a3": adm0,
                "geometry": geom,
            }
        )
    return out


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Natural Earth 1:50m Admin 1 States/Provinces",
            citation="Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com",
            kind="dataset",
            url="https://www.naturalearthdata.com/downloads/50m-cultural-vectors/",
            year=2023,
        )

        # Resolve parent country ids once.
        parent_ids: dict[str, int] = {}
        for adm0, country_code in WANTED.items():
            country = db.execute(
                select(Territory).where(Territory.code == country_code)
            ).scalar_one_or_none()
            if country is None:
                logger.warning(
                    "parent country %s not found — run `countries` seeder first; "
                    "skipping its subdivisions", country_code
                )
            else:
                parent_ids[adm0] = country.id

        features = _load_features()
        logger.info("loaded %d subdivision features for %s", len(features), sorted(WANTED))

        inserted = skipped = 0
        for f in features:
            code = f["iso_3166_2"] or f"{f['adm0_a3']}-{f['name']}"
            existing = db.execute(
                select(Territory).where(Territory.code == code)
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            geom = shapely_shape(f["geometry"]) if not hasattr(f["geometry"], "geom_type") else f["geometry"]
            t = Territory(
                kind=TerritoryKind.SUBDIVISION,
                name=f["name"],
                code=code,
                parent_id=parent_ids.get(f["adm0_a3"]),
                geom=from_shape(geom, srid=4326),
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))
            inserted += 1

        logger.info("subdivisions: inserted=%d skipped=%d", inserted, skipped)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
