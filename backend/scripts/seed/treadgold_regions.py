"""European Russia and Asiatic Russia umbrella regions, after Treadgold.

Donald W. Treadgold's framework in "The Great Siberian Migration" (1957) and
later work uses the Urals as the cardinal divide of the Russian Empire:
- "European Russia" / "the homeland west of the Urals" — the metropole
- "Asiatic Russia" — Siberia, Far East, Central Asia, etc.

These two umbrellas anchor sources that describe migration in those terms
without further breakdown ("from European Russia to Siberia", etc.).

Note: this seeder REPLACES the older `ru-region-asian-ri` slug with a
fresh pair `ru-region-european` and `ru-region-asiatic` to make the
Treadgold framework explicit. The old `ru-region-asian-ri` is left in
place (renamed) so any external references stay valid — its slug is just
updated to match the new naming.
"""
from __future__ import annotations

import logging

from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy import select, update

from backend.models.enums import Empire, TerritoryKind
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


# Approximate hulls in EPSG:4326. The Ural line is taken as ~60°E for
# the umbrella division (Treadgold uses the Urals proper, but for a coarse
# umbrella anchor the meridian is sufficient).
TREADGOLD = [
    {
        "code": "ru-region-european",
        "name": "Європейська Росія (за Treadgold)",
        "name_local": "Європейська Росія",
        "polygon": [
            (20.0, 70.0), (60.0, 70.0), (60.0, 50.0), (52.0, 45.0),
            (47.0, 40.0), (37.0, 44.0), (28.0, 45.0), (24.0, 50.0),
            (22.0, 55.0), (20.0, 60.0),
        ],
        "description": "За D. W. Treadgold (1957): «the homeland west of the Urals» — "
                       "метропольний простір Російської імперії, протиставлений Asiatic Russia.",
    },
    {
        "code": "ru-region-asiatic",
        "name": "Азіатська Росія (за Treadgold)",
        "name_local": "Азіатська Росія",
        "polygon": [
            (60.0, 78.0), (180.0, 75.0), (180.0, 42.0), (140.0, 40.0),
            (90.0, 39.0), (60.0, 39.0), (60.0, 70.0),
        ],
        "description": "За D. W. Treadgold (1957): «Asiatic Russia» — Сибір, "
                       "Далекий Схід, Центральна Азія, на схід від Уралу.",
    },
]


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Treadgold framework — European vs Asiatic Russia",
            citation="Treadgold, Donald W. The Great Siberian Migration: Government "
            "and Peasant in Resettlement from Emancipation to the First World War. "
            "Princeton University Press, 1957. Used here as the conceptual basis "
            "for the European-vs-Asiatic Russia umbrella division (Urals as cardinal "
            "boundary). Polygons are author-drawn approximate hulls.",
            kind="monograph",
            author="Treadgold, D. W.",
            year=1957,
            notes="Coarse hulls following Treadgold's west-of-Urals / east-of-Urals "
                  "framing. NOT digitised borders; only an anchor for broad-scope records.",
        )

        # If a previous run created `ru-region-asian-ri`, keep that row but
        # mark it as superseded so the user sees the Treadgold pair instead.
        old = db.execute(
            select(Territory).where(Territory.code == "ru-region-asian-ri")
        ).scalar_one_or_none()
        if old is not None and not any(
            db.execute(select(Territory).where(Territory.code == s["code"])).scalar_one_or_none()
            for s in TREADGOLD
        ):
            # First-time install of the Treadgold pair: nudge the legacy row's name.
            old.notes = (old.notes or "") + "\nSuperseded by ru-region-asiatic (Treadgold framework)."

        for spec in TREADGOLD:
            existing = db.execute(
                select(Territory).where(Territory.code == spec["code"])
            ).scalar_one_or_none()
            if existing:
                logger.info("Treadgold region %s exists, skipping", spec["code"])
                continue
            poly = Polygon(spec["polygon"])
            t = Territory(
                kind=TerritoryKind.REGION,
                name=spec["name"],
                name_local=spec["name_local"],
                code=spec["code"],
                empire=Empire.RUSSIAN,
                is_umbrella_region=True,
                geom=from_shape(poly, srid=4326),
                notes=spec["description"],
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))
            logger.info("seeded Treadgold region %s", spec["code"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
