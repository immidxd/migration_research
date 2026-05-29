"""Replace the coarse hand-drawn hulls of the Austro-Hungarian Ukrainian
umbrella regions with REAL 1910 crownland boundaries from HistoGIS.

Source: "Austro-Hungarian Empire Crownlands 1910" (HistoGIS, ACDH-OeAW;
Anna Piechl / Peter Paul Marckhgott-Sanabria), source #141. Derived from
OpenStreetMap + historical maps. Two crownlands map onto our regions:

    Königreich Galizien und Lodomerien → ua-region-halychyna (Галичина)
    Herzogtum Bukowina                 → ua-region-bukovyna  (Буковина)

Закарпаття (ua-region-zakarpattia) is NOT a crownland — it sat inside the
Kingdom of Hungary, so it needs Hungarian komitat data (separate source) and
keeps its coarse hull for now.

Geometry is committed at data/territories/raw/ah-crownlands-1910-histogis.geojson
(EPSG:4326) for reproducibility. Idempotent: re-running just re-sets the geom.
"""
from __future__ import annotations

import json
import logging

from geoalchemy2.shape import from_shape
from shapely.geometry import shape as shapely_shape
from sqlalchemy import select

from backend.app.settings import PROJECT_ROOT
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


GEOJSON = PROJECT_ROOT / "data" / "territories" / "raw" / "ah-crownlands-1910-histogis.geojson"
# slug in the geojson -> Territory.code
MAPPING = {
    "halychyna": "ua-region-halychyna",
    "bukovyna": "ua-region-bukovyna",
}


def run() -> None:
    if not GEOJSON.exists():
        logger.warning("AH crownlands GeoJSON missing at %s — skipping", GEOJSON)
        return
    fc = json.loads(GEOJSON.read_text())

    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="HistoGIS — Austro-Hungarian Empire Crownlands 1910",
            citation="Anna Piechl / Peter Paul Marckhgott-Sanabria, "
            "\"Austro-Hungarian Empire Crownlands 1910\", HistoGIS, Austrian "
            "Centre for Digital Humanities and Cultural Heritage (ACDH-OeAW). "
            "Derived from OpenStreetMap and historical maps. Galicia and "
            "Bukovina crownlands.",
            kind="dataset",
            url="https://histogis.acdh.oeaw.ac.at/shapes/source/detail/141",
            year=2020,
            notes="CC BY-NC. Raw: data/territories/raw/ah-crownlands-1910-histogis.geojson",
        )

        updated = 0
        for feat in fc["features"]:
            slug = feat["properties"]["slug"]
            code = MAPPING.get(slug)
            if not code:
                continue
            terr = db.execute(
                select(Territory).where(Territory.code == code)
            ).scalar_one_or_none()
            if terr is None:
                logger.warning("territory %s not found — skipping", code)
                continue
            geom = shapely_shape(feat["geometry"])
            terr.geom = from_shape(geom, srid=4326)
            db.flush()
            # attach source attestation (idempotent-ish: skip if present)
            exists = db.execute(
                select(TerritorySource).where(
                    TerritorySource.territory_id == terr.id,
                    TerritorySource.source_id == src.id,
                )
            ).first()
            if not exists:
                db.add(TerritorySource(territory_id=terr.id, source_id=src.id))
            updated += 1
            logger.info("replaced geom of %s from HistoGIS crownland", code)

        logger.info("ah_crownlands: updated %d region(s)", updated)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
