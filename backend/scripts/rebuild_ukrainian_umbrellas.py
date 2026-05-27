"""Recompute Ukrainian umbrella regions as ST_Union of constituent
real RiStat 1897 gubernias.

Replaces my earlier hand-drawn coarse hulls (and the country-clipped
versions) with geometrically-correct umbrellas built from actual
historical gubernia boundaries.

Definitions follow the standard Ukrainian historiographic convention
(Hrushevsky / Subtelny / Magocsi):

  Naddniprianshchyna = Pravoberezhzhia ∪ Livoberezhzhia ∪ Pivden
  Pravoberezhzhia    = Kyiv + Podolia + Volynia
  Livoberezhzhia     = Poltava + Chernihiv
  Slobozhanshchyna   = Kharkiv (core; spilled over into Voronezh/Kursk,
                       but those are not part of the conventional umbrella)
  Pivden (Novorossia) = Kherson + Tavria + Katerynoslav + Bessarabia
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal


UMBRELLAS: dict[str, list[str]] = {
    "ua-region-pravoberezhzhia":    ["ru-gub-kyiv", "ru-gub-podilska", "ru-gub-volyn"],
    "ua-region-livoberezhzhia":     ["ru-gub-poltava", "ru-gub-chernihiv"],
    "ua-region-slobozhanshchyna":   ["ru-gub-kharkiv"],
    "ua-region-pivden":             ["ru-gub-kherson", "ru-gub-tavria",
                                     "ru-gub-katerynoslav", "ru-gub-bessarabia"],
    "ua-region-naddniprianshchyna": [
        "ru-gub-kyiv", "ru-gub-podilska", "ru-gub-volyn",
        "ru-gub-poltava", "ru-gub-chernihiv",
        "ru-gub-kharkiv",
        "ru-gub-kherson", "ru-gub-tavria", "ru-gub-katerynoslav", "ru-gub-bessarabia",
    ],
}


def run() -> None:
    logger = logging.getLogger("migrations.rebuild")
    db = SessionLocal()
    try:
        for umbrella_slug, member_slugs in UMBRELLAS.items():
            res = db.execute(
                text("""
                    WITH members AS (
                        SELECT ST_Union(geom) AS g
                        FROM territories
                        WHERE code = ANY(:members)
                    )
                    UPDATE territories t
                    SET geom = ST_Multi(ST_MakeValid(members.g))
                    FROM members
                    WHERE t.code = :slug AND members.g IS NOT NULL
                    RETURNING t.id
                """),
                {"slug": umbrella_slug, "members": member_slugs},
            ).first()
            if res:
                logger.info("rebuilt %s from %d gubernias → id=%s",
                            umbrella_slug, len(member_slugs), res[0])
            else:
                logger.warning("skipped %s — umbrella row or members missing", umbrella_slug)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
