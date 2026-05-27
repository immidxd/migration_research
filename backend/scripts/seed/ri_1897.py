"""Import Russian Empire 1897 administrative divisions (RiStat / IISH).

Source: Kessler, Gijs & Andrei Markevich. Electronic Repository of
Russian Historical Statistics, 18th-21st centuries. https://ristat.org/,
Version I (2020). DOI: 10.34894/NQOASN. CC0 with attribution.

Data files (manually downloaded into data/territories/raw/):
  ri-1897-provinces.gpkg — 103 gubernias, EPSG:4326
  ri-1897-districts.gpkg — 824 uezds (districts), EPSG:4326

Strategy:
- For each gubernia in the RiStat file:
  * If a Territory with a matching slug-by-name already exists (e.g. my
    earlier `ru-gub-poltava` hand-drawn placeholder), REPLACE its geom
    with the real RiStat polygon. Keeps the Territory id stable so any
    user flows referencing it remain valid.
  * Otherwise INSERT a new Territory (kind=gubernia, empire=russian_empire).
- For each uezd, INSERT a new Territory (kind=uezd, parent_id=<gubernia.id>).
- Validity range marked as 1860-01-01 → 1917-12-31 (post-1864 reforms,
  through the empire's end). 1897 snapshot is broadly applicable across
  these years; per-year refinements are a follow-up.
- All inserted/updated rows get a territory_sources link to the RiStat
  Source row.

Idempotent: re-running updates only what's new or changed.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from unicodedata import normalize

import pyogrio
from geoalchemy2.shape import from_shape
from shapely.geometry import shape as shapely_shape
from sqlalchemy import select

from backend.app.settings import PROJECT_ROOT
from backend.models.enums import Empire, TerritoryKind
from backend.models.source_links import TerritorySource
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


PROVINCES_GPKG = PROJECT_ROOT / "data" / "territories" / "raw" / "ri-1897-provinces.gpkg"
DISTRICTS_GPKG = PROJECT_ROOT / "data" / "territories" / "raw" / "ri-1897-districts.gpkg"

VALID_FROM = date(1860, 1, 1)   # post-1864 reforms ≈ stable Empire admin
VALID_TO = date(1917, 12, 31)


def _slug(s: str) -> str:
    """Latin-only slug, lower-case, dashes."""
    s = normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    out = []
    last_dash = False
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-")


# Existing slugs from my hand-drawn placeholders that should be REPLACED
# (not duplicated) when their RiStat equivalent loads. Match by English name.
EXISTING_GUBERNIA_REMAP: dict[str, str] = {
    "kiev-governorate":          "ru-gub-kyiv",
    "podolia-governorate":       "ru-gub-podilska",
    "volynia-governorate":       "ru-gub-volyn",
    "chernigov-governorate":     "ru-gub-chernihiv",
    "poltava-governorate":       "ru-gub-poltava",
    "kharkov-governorate":       "ru-gub-kharkiv",
    "ekaterinoslav-governorate": "ru-gub-katerynoslav",
    "kherson-governorate":       "ru-gub-kherson",
    "taurida-governorate":       "ru-gub-tavria",
    "bessarabia-governorate":    "ru-gub-bessarabia",
}


def _gub_slug(eng: str) -> str:
    """Resolve a gubernia's stable slug: prefer the existing hand-drawn slug
    so user flows that reference it stay valid; otherwise generate a fresh
    `ri1897-<english-name>` slug for newly-added gubernias."""
    base = _slug(eng)
    return EXISTING_GUBERNIA_REMAP.get(base, f"ri1897-{base}")


def _import_provinces(db, src_id: int) -> dict[str, int]:
    """Returns mapping {RiStat Gub_ID (str) → our territories.id}."""
    df = pyogrio.read_dataframe(str(PROVINCES_GPKG))
    if df.crs and str(df.crs).lower() != "epsg:4326":
        df = df.to_crs("EPSG:4326")

    gub_id_to_territory_id: dict[str, int] = {}
    updated = inserted = 0

    for row in df.itertuples(index=False):
        ru_name: str = row.prov_RU
        en_name: str = row.prov_ENG
        gub_id: str = str(row.Gub_ID)  # may be "62a", "62b", etc.
        geom = row.geometry
        if geom is None:
            continue

        slug = _gub_slug(en_name)
        existing = db.execute(
            select(Territory).where(Territory.code == slug)
        ).scalar_one_or_none()

        wkb = from_shape(geom, srid=4326)

        if existing:
            existing.geom = wkb
            existing.name = ru_name
            existing.name_local = ru_name
            existing.valid_from = VALID_FROM
            existing.valid_to = VALID_TO
            existing.empire = Empire.RUSSIAN
            existing.kind = TerritoryKind.GUBERNIA
            existing.notes = (
                f"Boundary from RiStat 1897 (DOI 10.34894/NQOASN). "
                f"English name: {en_name}."
            )
            db.flush()
            db.merge(TerritorySource(territory_id=existing.id, source_id=src_id))
            gub_id_to_territory_id[gub_id] = existing.id
            updated += 1
        else:
            t = Territory(
                kind=TerritoryKind.GUBERNIA,
                name=ru_name,
                name_local=ru_name,
                code=slug,
                empire=Empire.RUSSIAN,
                valid_from=VALID_FROM,
                valid_to=VALID_TO,
                geom=wkb,
                notes=(
                    f"Boundary from RiStat 1897 (DOI 10.34894/NQOASN). "
                    f"English name: {en_name}."
                ),
            )
            db.add(t)
            db.flush()
            db.add(TerritorySource(territory_id=t.id, source_id=src_id))
            gub_id_to_territory_id[gub_id] = t.id
            inserted += 1

    logger.info("gubernias: updated=%d inserted=%d", updated, inserted)
    return gub_id_to_territory_id


def _import_districts(db, src_id: int, gub_id_to_id: dict[str, int]) -> None:
    df = pyogrio.read_dataframe(str(DISTRICTS_GPKG))
    if df.crs and str(df.crs).lower() != "epsg:4326":
        df = df.to_crs("EPSG:4326")

    inserted = skipped = 0
    seen_slugs: set[str] = set()

    for row in df.itertuples(index=False):
        gub_id = str(row.Gub_ID)
        ru_name: str = row.Name_RU
        en_name: str = row.Name_ENG
        geom = row.geometry
        if geom is None or ru_name is None:
            continue

        parent_id = gub_id_to_id.get(gub_id)
        if parent_id is None:
            # Province for this district wasn't imported (rare island cases)
            continue

        # Slug must be unique. Some uezds share names across gubernias;
        # prefix with gubernia slug for uniqueness.
        # Find parent slug via DB lookup once per gubernia.
        parent_slug = db.execute(
            select(Territory.code).where(Territory.id == parent_id)
        ).scalar_one()
        slug = f"{parent_slug}-uezd-{_slug(en_name)}"
        # Disambiguate if two uezds in same parent have the same English name
        base_slug = slug
        n = 1
        while slug in seen_slugs:
            n += 1
            slug = f"{base_slug}-{n}"
        seen_slugs.add(slug)

        existing = db.execute(
            select(Territory).where(Territory.code == slug)
        ).scalar_one_or_none()
        if existing:
            skipped += 1
            continue

        t = Territory(
            kind=TerritoryKind.UEZD,
            name=ru_name,
            name_local=ru_name,
            code=slug,
            parent_id=parent_id,
            empire=Empire.RUSSIAN,
            valid_from=VALID_FROM,
            valid_to=VALID_TO,
            geom=from_shape(geom, srid=4326),
            notes=f"Boundary from RiStat 1897. English name: {en_name}.",
        )
        db.add(t)
        db.flush()
        db.add(TerritorySource(territory_id=t.id, source_id=src_id))
        inserted += 1

    logger.info("uezds: inserted=%d skipped=%d", inserted, skipped)


def run() -> None:
    if not PROVINCES_GPKG.exists() or not DISTRICTS_GPKG.exists():
        raise SystemExit(
            f"Missing RiStat gpkg files. Expected at:\n"
            f"  {PROVINCES_GPKG}\n  {DISTRICTS_GPKG}\n"
            "Download from doi:10.34894/NQOASN."
        )

    with session_scope() as db:
        src = get_or_create_source(
            db,
            short_title="RiStat (Kessler & Markevich, 2020) — Russian Empire 1897",
            citation=(
                "Kessler, Gijs and Andrei Markevich. Electronic Repository of "
                "Russian Historical Statistics, 18th–21st centuries. "
                "https://ristat.org/, Version I (2020). "
                "Dataset: 'Russian Empire 1897 - Provinces / Districts', "
                "DOI: 10.34894/NQOASN. International Institute of Social History (IISH). "
                "License: CC0 with attribution."
            ),
            kind="dataset",
            author="Kessler, G. & Markevich, A.",
            year=2020,
            url="https://doi.org/10.34894/NQOASN",
        )
        db.commit()  # ensure src.id is durable

        gub_map = _import_provinces(db, src.id)
        _import_districts(db, src.id, gub_map)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
