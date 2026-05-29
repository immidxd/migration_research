"""Replace the coarse hull of Закарпаття with the union of its historical
Hungarian komitats from HistoGIS.

Transcarpathia was not an Austrian crownland — it sat inside the Kingdom of
Hungary as four counties. HistoGIS only carries these counties from its
"Austrian Empire Counties 1835" source, so the geometry is an 1835 snapshot
(county borders were broadly stable through the 19th c., but this predates the
user's 1896–1914 period — caveat recorded in the source citation):

    Unghvar (Ung) ∪ Bereg ∪ Ugocsa ∪ Máramaros → ua-region-zakarpattia

Note: the union extends a little beyond modern Zakarpattia (Máramaros reaches
into today's Romania), reflecting the full historical komitats. Far better
than the previous 36-point rectangle. Idempotent.
"""
from __future__ import annotations

import json
import logging

from geoalchemy2.shape import from_shape
from shapely.geometry import shape as shapely_shape
from shapely.ops import unary_union
from sqlalchemy import select

from backend.app.settings import PROJECT_ROOT
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


GEOJSON = PROJECT_ROOT / "data" / "territories" / "raw" / "zakarpattia-komitats-1835-histogis.geojson"
CODE = "ua-region-zakarpattia"


def run() -> None:
    if not GEOJSON.exists():
        logger.warning("Zakarpattia komitats GeoJSON missing at %s — skipping", GEOJSON)
        return
    fc = json.loads(GEOJSON.read_text())
    geoms = [shapely_shape(f["geometry"]) for f in fc["features"]]
    if not geoms:
        logger.warning("no komitat geometries — skipping")
        return
    merged = unary_union(geoms)

    with session_scope() as db:
        terr = db.execute(select(Territory).where(Territory.code == CODE)).scalar_one_or_none()
        if terr is None:
            logger.warning("%s not found — skipping", CODE)
            return
        terr.geom = from_shape(merged, srid=4326)
        terr.notes = ("Union of Hungarian komitats Ung (Unghvar), Bereg, Ugocsa, "
                      "Máramaros, per HistoGIS Austrian Empire Counties 1835.")
        db.flush()

        src = get_or_create_source(
            db,
            short_title="HistoGIS — Austrian Empire Counties 1835 (Hungarian komitats)",
            citation="HistoGIS, Austrian Centre for Digital Humanities and "
            "Cultural Heritage (ACDH-OeAW), \"Austrian Empire Counties 1835\". "
            "Закарпаття modelled as the union of the Ung (Unghvar), Bereg, "
            "Ugocsa and Máramaros komitats. NOTE: 1835 snapshot — predates the "
            "1896–1914 research period; county borders were broadly stable but "
            "this is an approximation for that era.",
            kind="dataset",
            url="https://histogis.acdh.oeaw.ac.at/",
            year=2020,
            notes="CC BY-NC. Raw: data/territories/raw/zakarpattia-komitats-1835-histogis.geojson",
        )
        exists = db.execute(
            select(TerritorySource).where(
                TerritorySource.territory_id == terr.id,
                TerritorySource.source_id == src.id,
            )
        ).first()
        if not exists:
            db.add(TerritorySource(territory_id=terr.id, source_id=src.id))
        logger.info("rebuilt %s from 4 komitats", CODE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
