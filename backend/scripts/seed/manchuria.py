"""Manchuria (Манжурія) as an umbrella historical region, 1911.

Source of truth: CHGIS V6, 1911 time slice, province polygons — the standard
academic historical GIS for late-Qing administrative boundaries (Harvard CGA /
Fudan). Manchuria is modelled as the union of the three late-Qing provinces of
the region (the "Three Eastern Provinces", 東三省):

    Fengtian 奉天 (later Liaoning) · Jilin 吉林 · Heilongjiang 黑龍江

License: CC0 1.0 (public domain) — so, like the RiStat files, the raw shapefile
zip travels in git for reproducibility:
    data/territories/raw/v6_1911_prov_pgn_utf.zip

Source CRS is EPSG:2333 (a projected China grid); reprojected to EPSG:4326 on
import. Idempotent on Territory.code = "region-manchuria-1911".
"""
from __future__ import annotations

import logging
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.ops import unary_union
from sqlalchemy import select

from backend.app.settings import PROJECT_ROOT
from backend.models.enums import Empire, TerritoryKind
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


RAW_DIR = PROJECT_ROOT / "data" / "territories" / "raw"
ZIP_PATH = RAW_DIR / "v6_1911_prov_pgn_utf.zip"
SHP_NAME = "v6_1911_prov_pgn_utf.shp"
CODE = "region-manchuria-1911"

# The three provinces, matched exactly on the CHGIS pinyin name field NAME_PY
# (verified against the 1911 province layer; 27 provinces total).
TARGET_PROVINCES = {"fengtian", "jilin", "heilongjiang"}


def _merged_geom():
    import pyogrio

    if not ZIP_PATH.exists():
        raise FileNotFoundError(
            f"{ZIP_PATH} not found. Download the CHGIS V6 '1911 Layers UTF8' "
            "province polygons (doi:10.7910/DVN/HHVVHX, file v6_1911_prov_pgn_utf.zip) "
            "into data/territories/raw/."
        )
    gdf = pyogrio.read_dataframe(f"/vsizip/{ZIP_PATH}/{SHP_NAME}")
    sel = gdf[gdf["NAME_PY"].str.lower().isin(TARGET_PROVINCES)]
    if len(sel) != len(TARGET_PROVINCES):
        logger.warning(
            "Manchuria: matched %d/%d provinces (%s)",
            len(sel), len(TARGET_PROVINCES), sorted(sel["NAME_PY"]),
        )
    sel = sel.to_crs(4326)
    return unary_union(list(sel.geometry))


def run() -> None:
    with session_scope() as db:
        existing = db.execute(
            select(Territory).where(Territory.code == CODE)
        ).scalar_one_or_none()
        if existing:
            logger.info("Manchuria %s exists, skipping", CODE)
            return

        merged = _merged_geom()

        src = get_or_create_source(
            db,
            short_title="CHGIS V6 — 1911 province polygons",
            citation="CHGIS, 2016, \"1911 Layers UTF8 Encoding\", "
            "doi:10.7910/DVN/HHVVHX, Harvard Dataverse, V1. China Historical "
            "Geographic Information System (CHGIS) Version 6, Harvard CGA / "
            "Fudan University. Manchuria = union of Fengtian (奉天), Jilin (吉林) "
            "and Heilongjiang (黑龍江) province polygons.",
            kind="dataset",
            url="https://doi.org/10.7910/DVN/HHVVHX",
            year=2016,
            notes="CC0 1.0. Raw file committed: data/territories/raw/"
            "v6_1911_prov_pgn_utf.zip. Reproducible: backend/scripts/seed/manchuria.py",
        )

        t = Territory(
            kind=TerritoryKind.REGION,
            name="Manchuria",
            name_local="Манжурія",
            code=CODE,
            empire=Empire.OTHER,
            is_umbrella_region=True,
            geom=from_shape(merged, srid=4326),
            notes="Three Eastern Provinces of the late Qing (1911), per CHGIS V6.",
        )
        db.add(t)
        db.flush()
        db.add(TerritorySource(territory_id=t.id, source_id=src.id))
        logger.info("seeded Manchuria umbrella region %s", CODE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
