"""Populate territories.parent_id — the place hierarchy that powers the
flow-relation candidate suggester and (later) the aggregation resolver.

Membership is taken from the explicit lists in the umbrella rebuild scripts
(rebuild_ukrainian_umbrellas.py, rebuild_intra_imperial_regions.py), arranged
into a tree the user confirmed:

    gubernia → sub-region → Наддніпрянщина → Європейська Росія
    intra-imperial gubernia → region (Сибір/Урал/…) → Європейська|Азіатська Росія
    any ungrouped RI gubernia → Європейська|Азіатська Росія by centroid (60°E)

Idempotent: re-running just re-sets parent_id. Reference data only (no facts).
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from backend.models import SessionLocal

logger = logging.getLogger("migrations.hierarchy")


# child code -> parent code (explicit edges)
PARENTS: dict[str, str] = {
    # Ukrainian gubernias -> most-specific sub-region
    "ru-gub-kyiv": "ua-region-pravoberezhzhia",
    "ru-gub-podilska": "ua-region-pravoberezhzhia",
    "ru-gub-volyn": "ua-region-pravoberezhzhia",
    "ru-gub-poltava": "ua-region-livoberezhzhia",
    "ru-gub-chernihiv": "ua-region-livoberezhzhia",
    "ru-gub-kharkiv": "ua-region-slobozhanshchyna",
    "ru-gub-kherson": "ua-region-pivden",
    "ru-gub-tavria": "ua-region-pivden",
    "ru-gub-katerynoslav": "ua-region-pivden",
    "ru-gub-bessarabia": "ua-region-pivden",
    # sub-regions -> Naddniprianshchyna
    "ua-region-pravoberezhzhia": "ua-region-naddniprianshchyna",
    "ua-region-livoberezhzhia": "ua-region-naddniprianshchyna",
    "ua-region-pivden": "ua-region-naddniprianshchyna",
    "ua-region-slobozhanshchyna": "ua-region-naddniprianshchyna",
    # Naddniprianshchyna -> European Russia
    "ua-region-naddniprianshchyna": "ru-region-european",
    # intra-imperial regions -> European / Asian Russia (Urals & Caucasus are
    # statistically European; the Urals ridge is the Europe/Asia boundary).
    "ru-region-povolzhia": "ru-region-european",
    "ru-region-ural": "ru-region-european",
    "ru-region-kavkaz": "ru-region-european",
    "ru-region-sybir": "ru-region-asian-ri",
    "ru-region-far-east": "ru-region-asian-ri",
    "ru-region-turkestan": "ru-region-asian-ri",
    # European & Asian Russia -> the empire top
    "ru-region-european": "ru-empire",
    "ru-region-asian-ri": "ru-empire",
}

# intra-imperial gubernia/oblast slug -> region slug (from rebuild_intra_imperial_regions.py)
INTRA_MEMBERS: dict[str, list[str]] = {
    "ru-region-sybir": [
        "ri1897-tobolsk-governorate", "ri1897-tomsk-governorate",
        "ri1897-enisei-governorate", "ri1897-irkutsk-governorate",
        "ri1897-yakutsk-region", "ri1897-transbaikal-region",
    ],
    "ru-region-far-east": [
        "ri1897-amur-region", "ri1897-primorskaya-region", "ri1897-sakhalin-island",
    ],
    "ru-region-kavkaz": [
        "ri1897-kuban-region", "ri1897-terek-region", "ri1897-stavropol-governorate",
        "ri1897-dagestan-region", "ri1897-black-sea-governorate",
        "ri1897-tiflis-governorate-incl-zakatalskii-district",
        "ri1897-kutaisi-governorate-incl-sukhumi-district",
        "ri1897-baku-governorate", "ri1897-erevan-governorate",
        "ri1897-elisabethpol-governorate", "ri1897-kars-governorate",
    ],
    "ru-region-turkestan": [
        "ri1897-syr-darya-region", "ri1897-samarkand-region", "ri1897-fergana-region",
        "ri1897-semirechye-region", "ri1897-transcaspian-region",
        "ri1897-bukhara", "ri1897-khiva",
        "ri1897-akmola-region", "ri1897-semipalatinsk-region", "ri1897-turgay-region",
    ],
    "ru-region-povolzhia": [
        "ri1897-samara-governorate", "ri1897-saratov-governorate",
        "ri1897-simbirsk-governorate", "ri1897-kazan-governorate",
        "ri1897-nizhny-novgorod-governorate", "ri1897-penza-governorate",
        "ri1897-astrakhan-governorate",
    ],
    "ru-region-ural": [
        "ri1897-perm-governorate", "ri1897-orenburg-governorate",
        "ri1897-ufa-governorate", "ri1897-viatka-governorate", "ri1897-ural-region",
    ],
}


def _set_parent(db, child_code: str, parent_code: str) -> bool:
    res = db.execute(
        text("""
            UPDATE territories c SET parent_id = p.id
            FROM territories p
            WHERE c.code = :child AND p.code = :parent
            RETURNING c.id
        """),
        {"child": child_code, "parent": parent_code},
    ).first()
    return res is not None


def _ensure_empire_top(db) -> None:
    """Create the conceptual 'Російська імперія' umbrella (top of the place
    tree) if missing. Geometry = union of European + Asian Russia."""
    db.execute(text("""
        INSERT INTO territories (kind, name, name_local, code, empire, is_umbrella_region, notes, geom)
        SELECT 'region', 'Російська імперія', 'Російська імперія', 'ru-empire',
               'russian_empire', true,
               'Conceptual top of the RI place hierarchy (European + Asian Russia).',
               (SELECT ST_Multi(ST_Union(geom)) FROM territories
                WHERE code IN ('ru-region-european','ru-region-asian-ri') AND geom IS NOT NULL)
        WHERE NOT EXISTS (SELECT 1 FROM territories WHERE code = 'ru-empire')
    """))


def run() -> None:
    db = SessionLocal()
    try:
        _ensure_empire_top(db)
        n = 0
        for child, parent in PARENTS.items():
            if _set_parent(db, child, parent):
                n += 1
            else:
                logger.warning("skip %s -> %s (missing row)", child, parent)
        for region, members in INTRA_MEMBERS.items():
            for m in members:
                if _set_parent(db, m, region):
                    n += 1
        # Ungrouped RI gubernias -> European/Asian Russia by centroid (60°E),
        # skipping any already parented above.
        db.execute(text("""
            UPDATE territories c
            SET parent_id = p.id
            FROM territories p
            WHERE c.kind = 'gubernia' AND c.empire = 'russian_empire'
              AND c.is_umbrella_region = false AND c.parent_id IS NULL
              AND c.geom IS NOT NULL
              AND p.code = CASE WHEN ST_X(ST_Centroid(c.geom)) < 60
                                THEN 'ru-region-european' ELSE 'ru-region-asian-ri' END
        """))
        db.commit()
        logger.info("hierarchy: set %d explicit parent edges + centroid fallback", n)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
