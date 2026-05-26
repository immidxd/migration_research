"""Hand-crafted umbrella historical regions of Ukrainian lands.

These polygons are intentionally APPROXIMATE — they exist to anchor records
of broad origin like "Pravoberezhzhia" on the map. They are NOT a substitute
for proper period-accurate gubernia boundaries (which we'll import separately
once a reliable historical-boundary source is in place).

Source attribution is honest: marked as "manual seed" so any user of the data
can see at a glance that these shapes are author-drawn approximations, not
digitised from a historical map.

Each region's polygon is a coarse hull of constituent gubernias. Refine in
the UI once gubernia layers exist — the umbrella geom can be replaced with
ST_Union of children.
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


# (lon, lat) pairs — coarse hulls in EPSG:4326. North is roughly top.
REGIONS = [
    {
        "code": "ua-region-pravoberezhzhia",
        "name": "Правобережна Україна",
        "name_local": "Правобережжя",
        "empire": Empire.RUSSIAN,
        "polygon": [
            (24.0, 52.5), (28.5, 52.0), (32.2, 50.5),
            (32.5, 48.0), (30.0, 47.5), (25.5, 48.5), (24.0, 50.0),
        ],
    },
    {
        "code": "ua-region-livoberezhzhia",
        "name": "Лівобережна Україна",
        "name_local": "Лівобережжя",
        "empire": Empire.RUSSIAN,
        "polygon": [
            (32.0, 52.5), (35.5, 52.0), (35.8, 49.0),
            (34.5, 48.0), (32.2, 48.5), (32.0, 50.5),
        ],
    },
    {
        "code": "ua-region-slobozhanshchyna",
        "name": "Слобожанщина",
        "name_local": "Слобожанщина",
        "empire": Empire.RUSSIAN,
        "polygon": [
            (35.5, 52.0), (39.5, 51.5), (40.0, 49.0),
            (38.0, 48.0), (35.8, 48.5), (35.5, 50.0),
        ],
    },
    {
        "code": "ua-region-pivden",
        "name": "Південна Україна (Новоросія)",
        "name_local": "Південь",
        "empire": Empire.RUSSIAN,
        "polygon": [
            (28.5, 48.5), (35.0, 48.5), (38.5, 47.5),
            (38.0, 45.2), (33.0, 44.5), (28.5, 45.5),
        ],
    },
    {
        "code": "ua-region-naddniprianshchyna",
        "name": "Наддніпрянська Україна",
        "name_local": "Наддніпрянщина",
        "empire": Empire.RUSSIAN,
        # umbrella over Right + Left + Pivden — coarsest of all
        "polygon": [
            (24.0, 52.5), (40.0, 51.5), (40.0, 47.0),
            (33.0, 44.5), (28.5, 45.5), (24.0, 50.0),
        ],
    },
    {
        "code": "ua-region-halychyna",
        "name": "Галичина",
        "name_local": "Галичина",
        "empire": Empire.AUSTRO_HUNGARIAN,
        "polygon": [
            (21.5, 50.5), (26.5, 50.5), (26.5, 48.5),
            (24.5, 48.0), (21.5, 49.0),
        ],
    },
    {
        "code": "ua-region-bukovyna",
        "name": "Буковина",
        "name_local": "Буковина",
        "empire": Empire.AUSTRO_HUNGARIAN,
        "polygon": [
            (25.0, 48.5), (27.0, 48.5), (27.0, 47.5), (25.0, 47.5),
        ],
    },
    {
        "code": "ua-region-zakarpattia",
        "name": "Закарпаття",
        "name_local": "Закарпаття",
        "empire": Empire.AUSTRO_HUNGARIAN,
        "polygon": [
            (22.0, 49.0), (24.5, 49.0), (24.5, 48.0), (22.0, 48.0),
        ],
    },
]


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Manual seed — Ukrainian umbrella regions (approximate)",
            citation="Author-drawn coarse hulls intended only as anchors for broad-origin "
            "records (e.g. 'Pravoberezhzhia'). NOT a historical boundary dataset. "
            "Replace with ST_Union of constituent gubernias once gubernia layers are loaded.",
            kind="manual",
            year=2026,
            notes="Reproducible: see backend/scripts/seed/umbrella_regions.py",
        )

        for spec in REGIONS:
            existing = db.execute(
                select(Territory).where(Territory.code == spec["code"])
            ).scalar_one_or_none()
            if existing:
                logger.info("region %s exists, skipping", spec["code"])
                continue

            poly = Polygon(spec["polygon"])
            t = Territory(
                kind=TerritoryKind.REGION,
                name=spec["name"],
                name_local=spec["name_local"],
                code=spec["code"],
                empire=spec["empire"],
                is_umbrella_region=True,
                geom=from_shape(poly, srid=4326),
                notes="Approximate hull — see source for caveats.",
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))
            logger.info("seeded region %s", spec["code"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
