"""Approximate polygons for sub-Russian Ukrainian gubernias.

Same honesty caveat as umbrella_regions: these are hand-drawn coarse hulls
based on standard secondary literature, not digitised from historical maps.
Sufficient for entering and visualising flows; replace with a real
historical-boundary dataset later.
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


GUBERNIAS = [
    # (slug, name, name_local, hull[(lon,lat)...])
    ("ru-gub-kyiv", "Київська губернія", "Київщина", [
        (29.5, 51.5), (32.0, 51.4), (32.5, 50.8), (32.0, 49.5),
        (30.5, 48.7), (28.7, 49.4), (28.5, 50.3),
    ]),
    ("ru-gub-podilska", "Подільська губернія", "Поділля", [
        (26.5, 49.6), (29.2, 49.7), (29.5, 48.6), (28.7, 47.9),
        (27.0, 47.9), (26.4, 48.5),
    ]),
    ("ru-gub-volyn", "Волинська губернія", "Волинь", [
        (23.8, 51.6), (27.0, 51.6), (27.2, 50.5), (26.5, 49.7),
        (24.5, 49.9), (23.6, 50.8),
    ]),
    ("ru-gub-chernihiv", "Чернігівська губернія", "Чернігівщина", [
        (30.5, 53.1), (33.5, 52.8), (34.2, 51.7), (33.5, 50.7),
        (31.6, 50.6), (30.5, 51.2),
    ]),
    ("ru-gub-poltava", "Полтавська губернія", "Полтавщина", [
        (32.2, 51.0), (35.5, 51.0), (35.8, 49.5), (34.5, 48.4),
        (32.6, 48.5), (32.0, 49.7),
    ]),
    ("ru-gub-kharkiv", "Харківська губернія", "Харківщина", [
        (35.0, 51.6), (38.5, 51.4), (39.5, 49.8), (38.0, 48.3),
        (36.0, 48.5), (35.0, 49.7),
    ]),
    ("ru-gub-katerynoslav", "Катеринославська губернія", "Катеринославщина", [
        (33.2, 49.4), (37.6, 49.0), (38.5, 47.5), (37.0, 46.8),
        (34.0, 46.8), (32.8, 47.5),
    ]),
    ("ru-gub-kherson", "Херсонська губернія", "Херсонщина", [
        (29.5, 49.0), (33.5, 48.7), (34.0, 46.5), (32.8, 45.5),
        (30.0, 45.5), (29.0, 46.7),
    ]),
    ("ru-gub-tavria", "Таврійська губернія", "Таврія", [
        (32.5, 47.5), (37.5, 47.6), (37.0, 45.5), (36.0, 44.5),
        (33.5, 44.4), (32.2, 45.5),
    ]),
    ("ru-gub-bessarabia", "Бессарабська губернія", "Бессарабія", [
        (26.6, 48.5), (29.8, 48.5), (30.2, 46.5), (28.5, 45.5),
        (26.7, 45.6), (26.4, 47.4),
    ]),
]


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Manual seed — Russian Imperial gubernias of Ukraine (approximate)",
            citation="Author-drawn coarse polygonal hulls of sub-Russian Ukrainian "
            "gubernias (Kyiv, Podilia, Volyn, Chernihiv, Poltava, Kharkiv, "
            "Katerynoslav, Kherson, Tavria, Bessarabia). NOT digitised from historical "
            "maps — sufficient for flow visualisation only. Replace once a proper "
            "historical-boundary dataset is imported.",
            kind="manual",
            year=2026,
            notes="Reproducible: see backend/scripts/seed/gubernias.py",
        )

        for slug, name, local, hull in GUBERNIAS:
            existing = db.execute(
                select(Territory).where(Territory.code == slug)
            ).scalar_one_or_none()
            if existing:
                logger.info("gubernia %s exists, skipping", slug)
                continue
            t = Territory(
                kind=TerritoryKind.GUBERNIA,
                name=name,
                name_local=local,
                code=slug,
                empire=Empire.RUSSIAN,
                geom=from_shape(Polygon(hull), srid=4326),
                notes="Approximate hull — see source for caveats.",
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))
            logger.info("seeded gubernia %s", slug)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
