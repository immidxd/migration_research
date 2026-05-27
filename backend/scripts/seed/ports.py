"""Key historical embarkation ports and a few rail border crossings.

Points are stored as Territory rows of kind PORT (or BORDER_CROSSING) and
the embarkation-specific metadata lives in transit_point_profiles.
"""
from __future__ import annotations

import logging
from datetime import date

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select

from backend.models.enums import TerritoryKind
from backend.models.routes import TransitPointProfile
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


PORTS = [
    # Black Sea
    {"code": "port-odesa", "name": "Одеса", "lon": 30.7233, "lat": 46.4825,
     "kind": TerritoryKind.PORT, "operator": None,
     "active_from": date(1794, 1, 1)},
    {"code": "port-mykolaiv", "name": "Миколаїв", "lon": 31.9946, "lat": 46.9750,
     "kind": TerritoryKind.PORT, "operator": None,
     "active_from": date(1789, 1, 1)},

    # Baltic
    {"code": "port-libau", "name": "Лібава (Liepāja)", "lon": 21.0108, "lat": 56.5046,
     "kind": TerritoryKind.PORT, "operator": "Russian East Asiatic SS",
     "active_from": date(1880, 1, 1)},
    {"code": "port-ryga", "name": "Рига", "lon": 24.1052, "lat": 56.9496,
     "kind": TerritoryKind.PORT, "operator": None,
     "active_from": date(1850, 1, 1)},
    {"code": "port-danzig", "name": "Данціг (Gdańsk)", "lon": 18.6466, "lat": 54.3520,
     "kind": TerritoryKind.PORT, "operator": None,
     "active_from": date(1850, 1, 1)},

    # North Sea (the dominant transatlantic departures)
    {"code": "port-hamburg", "name": "Гамбург", "lon": 9.9937, "lat": 53.5511,
     "kind": TerritoryKind.PORT, "operator": "Hamburg America Line (HAPAG)",
     "active_from": date(1847, 1, 1)},
    {"code": "port-bremerhaven", "name": "Бремергафен", "lon": 8.5810, "lat": 53.5396,
     "kind": TerritoryKind.PORT, "operator": "Norddeutscher Lloyd",
     "active_from": date(1857, 1, 1)},
    {"code": "port-antwerp", "name": "Антверпен", "lon": 4.4025, "lat": 51.2194,
     "kind": TerritoryKind.PORT, "operator": "Red Star Line",
     "active_from": date(1873, 1, 1)},
    {"code": "port-rotterdam", "name": "Роттердам", "lon": 4.4777, "lat": 51.9244,
     "kind": TerritoryKind.PORT, "operator": "Holland America Line",
     "active_from": date(1873, 1, 1)},
    {"code": "port-le-havre", "name": "Гавр", "lon": 0.1079, "lat": 49.4944,
     "kind": TerritoryKind.PORT, "operator": "Compagnie Générale Transatlantique",
     "active_from": date(1864, 1, 1)},
    {"code": "port-liverpool", "name": "Ліверпуль", "lon": -2.9916, "lat": 53.4084,
     "kind": TerritoryKind.PORT, "operator": "Cunard / White Star",
     "active_from": date(1840, 1, 1)},

    # Mediterranean / Adriatic
    {"code": "port-trieste", "name": "Трієст", "lon": 13.7768, "lat": 45.6495,
     "kind": TerritoryKind.PORT, "operator": "Austro-Americana",
     "active_from": date(1903, 1, 1)},
    {"code": "port-fiume", "name": "Фіуме (Rijeka)", "lon": 14.4422, "lat": 45.3271,
     "kind": TerritoryKind.PORT, "operator": "Cunard Hungarian-American Line",
     "active_from": date(1903, 1, 1)},

    # Key rail border crossings for east-bound (intra-imperial) migration
    {"code": "rail-cheliabinsk", "name": "Челябінськ (переселенський пункт)",
     "lon": 61.4291, "lat": 55.1644,
     "kind": TerritoryKind.BORDER_CROSSING,
     "operator": "Переселенське управління МВД РІ",
     "active_from": date(1893, 1, 1),
     "active_to": date(1917, 1, 1)},

    # New York Harbor immigration station — primary US entry point for
    # transatlantic arrivals during the user's research period.
    {"code": "border-ellis-island", "name": "Острів Елліс",
     "lon": -74.0395, "lat": 40.6995,
     "kind": TerritoryKind.BORDER_CROSSING,
     "operator": "United States Bureau of Immigration",
     "active_from": date(1892, 1, 1),
     "active_to": date(1954, 11, 12)},
]


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Manual seed — key embarkation ports & transit points",
            citation="Coordinates from OpenStreetMap; operator/period notes "
            "compiled by hand from standard secondary literature on European "
            "emigration shipping lines and Russian Imperial resettlement.",
            kind="manual",
            year=2026,
            notes="Reproducible: see backend/scripts/seed/ports.py",
        )

        for spec in PORTS:
            existing = db.execute(
                select(Territory).where(Territory.code == spec["code"])
            ).scalar_one_or_none()
            if existing:
                logger.info("port %s exists, skipping", spec["code"])
                continue

            pt = Point(spec["lon"], spec["lat"])
            t = Territory(
                kind=spec["kind"],
                name=spec["name"],
                code=spec["code"],
                geom=from_shape(pt, srid=4326),
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))

            db.add(TransitPointProfile(
                territory_id=t.id,
                active_from=spec.get("active_from"),
                active_to=spec.get("active_to"),
                operator=spec.get("operator"),
            ))
            logger.info("seeded transit point %s", spec["code"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
