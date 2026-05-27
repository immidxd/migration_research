"""Recompute intra-imperial east umbrella regions as ST_Union of real
RiStat 1897 gubernias / oblasts.

Replaces my earlier hand-drawn rectangle hulls (and the country-clipped
versions) with geometrically-correct shapes built from constituent
historical admin units. Same technique as the Ukrainian umbrellas script.

Membership follows the conventional Russian Empire admin geography
(Степной край partially split between Туркестан and Урал for our
purposes; Кавказ includes both North Caucasus oblasts and Transcaucasus
governorates).
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal


# Explicit group membership by slug (RiStat 1897)
GROUPS: dict[str, list[str]] = {
    "ru-region-sybir": [
        "ri1897-tobolsk-governorate",
        "ri1897-tomsk-governorate",
        "ri1897-enisei-governorate",
        "ri1897-irkutsk-governorate",
        "ri1897-yakutsk-region",
        "ri1897-transbaikal-region",
    ],
    "ru-region-far-east": [
        "ri1897-amur-region",
        "ri1897-primorskaya-region",
        "ri1897-sakhalin-island",
    ],
    "ru-region-kavkaz": [
        # North Caucasus
        "ri1897-kuban-region",
        "ri1897-terek-region",
        "ri1897-stavropol-governorate",
        "ri1897-dagestan-region",
        "ri1897-black-sea-governorate",
        # Transcaucasus
        "ri1897-tiflis-governorate-incl-zakatalskii-district",
        "ri1897-kutaisi-governorate-incl-sukhumi-district",
        "ri1897-baku-governorate",
        "ri1897-erevan-governorate",
        "ri1897-elisabethpol-governorate",
        "ri1897-kars-governorate",
    ],
    "ru-region-turkestan": [
        # Turkestan governorate-generalship proper
        "ri1897-syr-darya-region",
        "ri1897-samarkand-region",
        "ri1897-fergana-region",
        "ri1897-semirechye-region",
        "ri1897-transcaspian-region",
        # Vassal protectorates
        "ri1897-bukhara",
        "ri1897-khiva",
        # Steppe край oblasts (administratively close to Turkestan)
        "ri1897-akmola-region",
        "ri1897-semipalatinsk-region",
        "ri1897-turgay-region",
    ],
    "ru-region-povolzhia": [
        "ri1897-samara-governorate",
        "ri1897-saratov-governorate",
        "ri1897-simbirsk-governorate",
        "ri1897-kazan-governorate",
        "ri1897-nizhny-novgorod-governorate",
        "ri1897-penza-governorate",
        "ri1897-astrakhan-governorate",
    ],
    "ru-region-ural": [
        "ri1897-perm-governorate",
        "ri1897-orenburg-governorate",
        "ri1897-ufa-governorate",
        "ri1897-viatka-governorate",
        "ri1897-ural-region",
    ],
}


def run() -> None:
    logger = logging.getLogger("migrations.rebuild-east")
    db = SessionLocal()
    try:
        # Explicit membership umbrellas
        for umbrella, members in GROUPS.items():
            res = db.execute(
                text("""
                    WITH m AS (
                        SELECT ST_Union(geom) AS g
                        FROM territories
                        WHERE code = ANY(:members)
                    )
                    UPDATE territories t
                    SET geom = ST_Multi(ST_MakeValid(m.g))
                    FROM m
                    WHERE t.code = :umbrella AND m.g IS NOT NULL
                    RETURNING t.id
                """),
                {"umbrella": umbrella, "members": members},
            ).first()
            if res:
                logger.info("rebuilt %s from %d members → id=%s",
                            umbrella, len(members), res[0])
            else:
                logger.warning("skipped %s — row or members missing", umbrella)

        # Європейська Росія = union of all RiStat gubernias whose centroid
        # lies west of the Urals (lon < 60°E). Cheap and reproducible.
        eu = db.execute(
            text("""
                WITH m AS (
                    SELECT ST_Union(geom) AS g
                    FROM territories
                    WHERE code LIKE 'ri1897-%'
                      AND ST_X(ST_Centroid(geom)) < 60
                )
                UPDATE territories t
                SET geom = ST_Multi(ST_MakeValid(m.g))
                FROM m
                WHERE t.code = 'ru-region-european' AND m.g IS NOT NULL
                RETURNING t.id
            """),
        ).first()
        if eu:
            logger.info("rebuilt ru-region-european (centroid west of 60°E) → id=%s", eu[0])

        # Азіатська частина РІ (the umbrella the user's flows point at) =
        # union of all RiStat gubernias whose centroid is east of the Urals
        as_ri = db.execute(
            text("""
                WITH m AS (
                    SELECT ST_Union(geom) AS g
                    FROM territories
                    WHERE code LIKE 'ri1897-%'
                      AND ST_X(ST_Centroid(geom)) >= 60
                )
                UPDATE territories t
                SET geom = ST_Multi(ST_MakeValid(m.g))
                FROM m
                WHERE t.code = 'ru-region-asian-ri' AND m.g IS NOT NULL
                RETURNING t.id
            """),
        ).first()
        if as_ri:
            logger.info("rebuilt ru-region-asian-ri (centroid east of 60°E) → id=%s", as_ri[0])

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
