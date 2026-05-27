"""One-off: re-cut umbrella region polygons against real country shapes.

The hand-drawn coarse hulls in the various seeders looked like boxy
rectangles on the map. By intersecting each hull with the union of the
modern Natural-Earth countries the region covers, we get a polygon that
hugs real coastlines and borders — much closer to what a reader expects
when they see "Сибір" or "Кавказ" outlined.

This script ONLY touches geometry. Names, source links, codes, and any
data references stay intact.

Run with:
    python -m backend.scripts.reshape_umbrella_regions
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal


# slug → list of ISO_A3 country codes whose union forms the geographic mask
CLIPS: dict[str, list[str]] = {
    # Russian Empire west of the Urals — the broad "European Russia"
    "ru-region-european": [
        "RUS", "BLR", "UKR", "LTU", "LVA", "EST", "MDA", "FIN", "POL",
    ],
    # Russian Empire east of the Urals (legacy umbrella for the user's flows)
    "ru-region-asian-ri": ["RUS", "KAZ"],

    # More specific east-of-Urals regions
    "ru-region-sybir":      ["RUS"],
    "ru-region-far-east":   ["RUS"],
    "ru-region-povolzhia":  ["RUS"],
    "ru-region-ural":       ["RUS"],
    "ru-region-kavkaz":     ["RUS", "GEO", "ARM", "AZE"],
    "ru-region-turkestan":  ["KAZ", "UZB", "TKM", "KGZ", "TJK"],

    # Ukrainian historical regions — clip to Ukraine (+ neighbours where
    # the regions stretch across modern borders)
    "ua-region-pravoberezhzhia":    ["UKR"],
    "ua-region-livoberezhzhia":     ["UKR"],
    "ua-region-slobozhanshchyna":   ["UKR", "RUS"],
    "ua-region-pivden":             ["UKR"],
    "ua-region-naddniprianshchyna": ["UKR"],
    "ua-region-halychyna":          ["UKR", "POL"],
    "ua-region-bukovyna":           ["UKR", "ROU"],
    "ua-region-zakarpattia":        ["UKR"],
}


def run() -> None:
    logger = logging.getLogger("migrations.reshape")
    db = SessionLocal()
    try:
        for slug, codes in CLIPS.items():
            res = db.execute(
                text("""
                    WITH mask AS (
                        SELECT ST_Union(geom) AS g
                        FROM territories
                        WHERE kind = 'country' AND code = ANY(:codes)
                    )
                    UPDATE territories t
                    SET geom = ST_Multi(ST_MakeValid(ST_Intersection(t.geom, mask.g)))
                    FROM mask
                    WHERE t.code = :slug AND mask.g IS NOT NULL
                    RETURNING t.id, ST_NumGeometries(t.geom) AS parts
                """),
                {"slug": slug, "codes": codes},
            ).first()
            if res:
                logger.info("reshaped %s → id=%s parts=%s", slug, res[0], res[1])
            else:
                logger.warning("skipped %s — no row or empty mask", slug)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
