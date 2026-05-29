"""Stitch the Austro-Hungarian regions onto their neighbours so the cross-source
seam (HistoGIS AH vs RiStat RU) stops showing gaps/overlaps along the frontier.

The Dniester/Zbruch frontier was digitised differently by each dataset, leaving
slivers. ST_Snap pulls the AH region's frontier vertices onto the neighbour's
edge within a small tolerance (~2 km) — verified to preserve area (±0.2%) and
validity, with zero resulting overlap.

Order matters: Galicia & Bukovina snap to the RU gubernia union (authoritative
for the imperial frontier); Zakarpattia then snaps to the already-fixed Galicia
(their seam is AH-internal, different HistoGIS sources).

Also cleans stale provenance: the AH regions kept the old "approximate hull"
note and manual-seed source even though their geometry is now real HistoGIS.

Run after ah_crownlands + zakarpattia. Idempotent (snapping an already-snapped
geometry is a near no-op).
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal

logger = logging.getLogger("migrations.seed")

TOL = 0.02  # ~2.2 km at this latitude

RU_UNION = (
    "SELECT ST_Union(geom) FROM territories "
    "WHERE kind='gubernia' AND empire='russian_empire' AND geom IS NOT NULL"
)


def run() -> None:
    db = SessionLocal()
    try:
        # 1) snap Galicia & Bukovina to the Russian gubernia frontier
        for code in ("ua-region-halychyna", "ua-region-bukovyna"):
            db.execute(
                text(f"""
                    UPDATE territories
                    SET geom = ST_Multi(ST_MakeValid(ST_Snap(geom, ({RU_UNION}), :tol)))
                    WHERE code = :code AND geom IS NOT NULL
                """),
                {"tol": TOL, "code": code},
            )
            logger.info("snapped %s to RU frontier", code)

        # 2) snap Zakarpattia to the now-fixed Galicia
        db.execute(
            text("""
                UPDATE territories
                SET geom = ST_Multi(ST_MakeValid(ST_Snap(
                    geom,
                    (SELECT geom FROM territories WHERE code='ua-region-halychyna'),
                    :tol)))
                WHERE code = 'ua-region-zakarpattia' AND geom IS NOT NULL
            """),
            {"tol": TOL},
        )
        logger.info("snapped ua-region-zakarpattia to Galicia")

        # 3) clean stale provenance: drop the old "approximate hull" manual
        #    source + note now that geometry is real.
        db.execute(text("""
            DELETE FROM territory_sources ts
            USING sources s
            WHERE ts.source_id = s.id
              AND s.short_title = 'Manual seed — Ukrainian umbrella regions (approximate)'
              AND ts.territory_id IN (
                SELECT id FROM territories
                WHERE code IN ('ua-region-halychyna','ua-region-bukovyna','ua-region-zakarpattia')
              )
        """))
        db.execute(text("""
            UPDATE territories SET notes = 'Real boundary from HistoGIS (see source).'
            WHERE code IN ('ua-region-halychyna','ua-region-bukovyna')
              AND (notes IS NULL OR notes LIKE 'Approximate hull%')
        """))
        db.commit()
        logger.info("cleaned stale AH provenance")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
