"""Stitch the Austro-Hungarian regions onto their neighbours so the cross-source
seam (HistoGIS AH vs RiStat RU) stops showing gaps/overlaps along the frontier.

The Dniester/Zbruch frontier was digitised differently by each dataset (different
meander detail / vertex density), so ST_Snap couldn't reconcile the two lines.
Instead we make the RU side AUTHORITATIVE and force the AH region to end exactly
on it, with no gap and no overlap:

    seam = ST_Buffer(AH, tol) ∩ ST_Buffer(REF, tol)   -- band straddling the frontier
    AH_new = ST_Difference(ST_Union(AH, seam), REF)

  - the seam band exists ONLY where AH and REF are within ~tol of each other
    (i.e. along their shared frontier), so AH grows only there — NOT around the
    whole of RU;
  - ST_Union(AH, seam) fills any gap up to/past REF; ST_Difference(…, REF) then
    trims back to exactly REF's boundary → no gap, no overlap.
AH's far borders (with Poland / Romania / Hungary) are untouched (the buffers
don't intersect there).

References (adjacent RU units only, to keep it cheap and local):
  Galicia  → Podolia ∪ Volhynia
  Bukovina → Podolia ∪ Bessarabia
  Zakarpattia → the now-fixed Galicia (AH-internal seam, different sources)

Also cleans stale provenance: the AH regions kept the old "approximate hull"
note and manual-seed source even though their geometry is now real HistoGIS.

Run after ah_crownlands + zakarpattia. Idempotent.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal

logger = logging.getLogger("migrations.seed")

TOL = 0.05  # ~5 km — wider than the worst digitisation offset along the river

# AH region code -> SQL selecting the authoritative reference geometry it abuts
REFERENCES = {
    "ua-region-halychyna": (
        "SELECT ST_Union(geom) FROM territories "
        "WHERE code IN ('ru-gub-podilska','ru-gub-volyn') AND geom IS NOT NULL"
    ),
    "ua-region-bukovyna": (
        "SELECT ST_Union(geom) FROM territories "
        "WHERE code IN ('ru-gub-podilska','ru-gub-bessarabia') AND geom IS NOT NULL"
    ),
    "ua-region-zakarpattia": (
        "SELECT geom FROM territories WHERE code='ua-region-halychyna'"
    ),
}


def run() -> None:
    db = SessionLocal()
    try:
        # Order: Galicia & Bukovina first (abut RU), then Zakarpattia (abuts the
        # now-fixed Galicia).
        for code in ("ua-region-halychyna", "ua-region-bukovyna", "ua-region-zakarpattia"):
            ref = REFERENCES[code]
            db.execute(
                text(f"""
                    UPDATE territories t
                    SET geom = ST_Multi(ST_MakeValid(
                        ST_Difference(
                            ST_Union(
                                t.geom,
                                ST_Intersection(
                                    ST_Buffer(t.geom, :tol),
                                    ST_Buffer(ref.g, :tol)
                                )
                            ),
                            ref.g
                        )
                    ))
                    FROM (SELECT ({ref}) AS g) ref
                    WHERE t.code = :code AND t.geom IS NOT NULL AND ref.g IS NOT NULL
                """),
                {"tol": TOL, "code": code},
            )
            logger.info("conformed %s to its RU/AH reference boundary", code)

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
