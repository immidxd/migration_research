"""Key destination / continuation cities of Ukrainian (and broader Galician /
Rusyn) emigration to North America, c. 1880–1914.

Hand-seeded SETTLEMENT points — the same approach as `ports.py`. These are
the hubs the user will mark as arrival or continuation points for migrant
routes: the Canadian prairie block-settlement gateways plus the US industrial
and coal-belt cities where the first-wave diaspora concentrated.

Parented to the country (USA / CAN) seeded by `countries.py`. Run after it.
Idempotent on `Territory.code` (e.g. "city-winnipeg").
"""
from __future__ import annotations

import logging

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select

from backend.models.enums import TerritoryKind
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


# (code, name_local, name, country_code, lon, lat)
CITIES = [
    # --- Canada: prairie block-settlement gateways + eastern hubs ---
    ("city-winnipeg", "Вінніпег", "Winnipeg", "CAN", -97.1384, 49.8951),
    ("city-edmonton", "Едмонтон", "Edmonton", "CAN", -113.4938, 53.5461),
    ("city-saskatoon", "Саскатун", "Saskatoon", "CAN", -106.6702, 52.1332),
    ("city-regina", "Реджайна", "Regina", "CAN", -104.6189, 50.4452),
    ("city-calgary", "Калгарі", "Calgary", "CAN", -114.0719, 51.0447),
    ("city-toronto", "Торонто", "Toronto", "CAN", -79.3832, 43.6532),
    ("city-montreal", "Монреаль", "Montreal", "CAN", -73.5673, 45.5017),
    ("city-vancouver", "Ванкувер", "Vancouver", "CAN", -123.1207, 49.2827),

    # --- USA: industrial & anthracite-coal belt where the first wave settled ---
    ("city-new-york", "Нью-Йорк", "New York", "USA", -74.0060, 40.7128),
    ("city-chicago", "Чикаго", "Chicago", "USA", -87.6298, 41.8781),
    ("city-pittsburgh", "Піттсбург", "Pittsburgh", "USA", -79.9959, 40.4406),
    ("city-cleveland", "Клівленд", "Cleveland", "USA", -81.6944, 41.4993),
    ("city-detroit", "Детройт", "Detroit", "USA", -83.0458, 42.3314),
    ("city-philadelphia", "Філадельфія", "Philadelphia", "USA", -75.1652, 39.9526),
    ("city-newark", "Ньюарк", "Newark", "USA", -74.1724, 40.7357),
    ("city-buffalo", "Баффало", "Buffalo", "USA", -78.8784, 42.8864),
    ("city-scranton", "Скрентон", "Scranton", "USA", -75.6624, 41.4090),
    ("city-shamokin", "Шамокін", "Shamokin", "USA", -76.5586, 40.7895),
    ("city-minneapolis", "Мінеаполіс", "Minneapolis", "USA", -93.2650, 44.9778),
    ("city-boston", "Бостон", "Boston", "USA", -71.0589, 42.3601),
    ("city-jersey-city", "Джерсі-Сіті", "Jersey City", "USA", -74.0776, 40.7282),
    ("city-st-louis", "Сент-Луїс", "St. Louis", "USA", -90.1994, 38.6270),
    ("city-baltimore", "Балтимор", "Baltimore", "USA", -76.6122, 39.2904),
    ("city-yonkers", "Йонкерс", "Yonkers", "USA", -73.8988, 40.9312),
]


def run() -> None:
    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="Manual seed — key North American diaspora cities",
            citation="Coordinates from OpenStreetMap; selection of first-wave "
            "Ukrainian/Galician/Rusyn settlement and labour-migration hubs "
            "compiled by hand from standard secondary literature on the North "
            "American diaspora (Canadian prairie block settlements; US "
            "industrial and anthracite-coal cities).",
            kind="manual",
            year=2026,
            notes="Reproducible: see backend/scripts/seed/cities.py",
        )

        # Resolve parent country ids once.
        parent_ids: dict[str, int] = {}
        for country_code in {c[3] for c in CITIES}:
            country = db.execute(
                select(Territory).where(Territory.code == country_code)
            ).scalar_one_or_none()
            if country is None:
                logger.warning(
                    "parent country %s not found — run `countries` first", country_code
                )
            else:
                parent_ids[country_code] = country.id

        inserted = skipped = 0
        for code, name_local, name, country_code, lon, lat in CITIES:
            existing = db.execute(
                select(Territory).where(Territory.code == code)
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue
            t = Territory(
                kind=TerritoryKind.SETTLEMENT,
                name=name,
                name_local=name_local,
                code=code,
                parent_id=parent_ids.get(country_code),
                geom=from_shape(Point(lon, lat), srid=4326),
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src.id))
            inserted += 1

        logger.info("cities: inserted=%d skipped=%d", inserted, skipped)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
