"""Intra-imperial destination regions — the eastern vector.

These cover the broad receiving territories of internal migration from
Ukrainian lands within the Russian Empire: Volga, Urals, Siberia, Far East,
Caucasus, Turkestan, plus an umbrella "Asian part of the Russian Empire"
for sources that don't break the destination down further.
"""
from __future__ import annotations

import logging

from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy import select

from backend.models.enums import Empire, TerritoryKind
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


# Coarse hulls in EPSG:4326 — broad enough for an umbrella record like
# "переселення з Полтавської губернії до Сибіру" to point somewhere meaningful.
DESTINATIONS = [
    ("ru-region-asian-ri", "Азіатська частина Російської імперії", "Азіатська Росія",
     TerritoryKind.REGION, True, [
        (60.0, 78.0), (180.0, 75.0), (180.0, 42.0), (140.0, 40.0),
        (90.0, 39.0), (60.0, 39.0), (52.0, 50.0), (52.0, 65.0),
     ]),
    ("ru-region-povolzhia", "Поволжя", "Поволжя",
     TerritoryKind.REGION, False, [
        (44.0, 58.0), (53.0, 58.0), (53.0, 49.0), (44.0, 46.0),
     ]),
    ("ru-region-ural", "Урал", "Урал",
     TerritoryKind.REGION, False, [
        (54.0, 67.0), (66.0, 67.0), (66.0, 51.0), (54.0, 51.0),
     ]),
    ("ru-region-sybir", "Сибір", "Сибір",
     TerritoryKind.REGION, False, [
        (60.0, 75.0), (130.0, 73.0), (130.0, 50.0), (78.0, 49.0),
        (60.0, 55.0),
     ]),
    ("ru-region-far-east", "Далекий Схід", "Далекий Схід",
     TerritoryKind.REGION, False, [
        (125.0, 70.0), (180.0, 70.0), (180.0, 42.0), (130.0, 42.0),
        (125.0, 50.0),
     ]),
    ("ru-region-kavkaz", "Кавказ і Закавказзя", "Кавказ",
     TerritoryKind.REGION, False, [
        (37.0, 47.0), (50.0, 47.0), (50.0, 38.5), (37.0, 38.5),
     ]),
    ("ru-region-turkestan", "Туркестан", "Туркестан",
     TerritoryKind.REGION, False, [
        (52.0, 50.0), (80.0, 50.0), (80.0, 36.0), (52.0, 36.0),
     ]),
]


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Manual seed — intra-imperial east destinations (approximate)",
            citation="Author-drawn coarse polygonal hulls of broad receiving regions "
            "of internal migration in the Russian Empire: Asian Russia umbrella, "
            "Volga, Urals, Siberia, Far East, Caucasus, Turkestan. NOT precise; "
            "intended only to anchor flow records whose source gives a broad "
            "destination (e.g. 'переселення до Сибіру').",
            kind="manual",
            year=2026,
            notes="Reproducible: see backend/scripts/seed/intra_imperial.py",
        )

        for slug, name, local, kind, umbrella, hull in DESTINATIONS:
            existing = db.execute(
                select(Territory).where(Territory.code == slug)
            ).scalar_one_or_none()
            if existing:
                logger.info("intra-imperial dest %s exists, skipping", slug)
                continue
            t = Territory(
                kind=kind,
                name=name,
                name_local=local,
                code=slug,
                empire=Empire.RUSSIAN,
                is_umbrella_region=umbrella,
                geom=from_shape(Polygon(hull), srid=4326),
                notes="Approximate hull — see source for caveats.",
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))
            logger.info("seeded intra-imperial dest %s", slug)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
