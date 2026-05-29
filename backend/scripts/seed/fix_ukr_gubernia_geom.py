"""Fix two Ukrainian gubernias that kept their hand-drawn 7-point placeholder
geometry because the RiStat import didn't match them by name: Podilska
(Подольская) and Volyn (Волынская).

Copies the real RiStat 1897 governorate boundaries onto the ru-gub-* rows that
the Ukrainian umbrella regions union over, then rebuilds those umbrellas so
Правобережжя / Наддніпрянщина stop showing straight placeholder edges.

Idempotent. Run after ri_1897. Mirrors the geom-replacement the other Ukrainian
gubernias already received.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal

logger = logging.getLogger("migrations.seed")

# placeholder ru-gub-* code -> real RiStat governorate code
GEOM_SOURCE = {
    "ru-gub-podilska": "ri1897-podolsk-governorate",
    "ru-gub-volyn": "ri1897-volhynian-governorate",
}


def run() -> None:
    db = SessionLocal()
    try:
        for target, source in GEOM_SOURCE.items():
            res = db.execute(
                text("""
                    UPDATE territories t
                    SET geom = s.geom
                    FROM territories s
                    WHERE t.code = :target AND s.code = :source AND s.geom IS NOT NULL
                    RETURNING ST_NPoints(t.geom)
                """),
                {"target": target, "source": source},
            ).first()
            if res:
                logger.info("copied %s geom → %s (%s pts)", source, target, res[0])
            else:
                logger.warning("could not copy %s → %s (missing row/geom)", source, target)
        db.commit()
    finally:
        db.close()

    # Rebuild the Ukrainian umbrellas now that all member gubernias are real.
    from backend.scripts.rebuild_ukrainian_umbrellas import run as rebuild
    rebuild()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
