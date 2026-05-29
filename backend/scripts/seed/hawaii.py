"""Hawaii as the worked example of time-varying territory status.

Attaches territory_periods to the existing Hawaii row (US-HI, imported as a US
subdivision from Natural Earth admin_1) so the same geometry/id reads as a
different polity depending on the year:

    1795–1893  Королівство Гаваї
    1894–1898  Республіка Гаваї
    1898–1959  Територія Гаваї (США)    [annexed 1898, organised 1900]
    1959–      Штат Гаваї (США)

Note: the user's shorthand "as a US state by 1900" is, strictly, the *Territory*
of Hawaii (organised 1900); statehood came in 1959. We model the correct
sequence and cite it.

Run after `subdivisions` (which creates the US-HI row). Idempotent: skips if
the Hawaii row already has periods.
"""
from __future__ import annotations

import logging

from sqlalchemy import select, text

from backend.models.source_links import TerritoryPeriodSource
from backend.models.temporal_facts import TerritoryPeriod
from backend.models.territories import Territory

from ._common import get_or_create_source, logger, session_scope


# (year_from, year_to, status, name_local, name, sovereign_code|None)
PERIODS = [
    (1795, 1893, "Незалежне королівство", "Королівство Гаваї", "Kingdom of Hawaii", None),
    (1894, 1898, "Республіка", "Республіка Гаваї", "Republic of Hawaii", None),
    (1898, 1959, "Інкорпорована територія США", "Територія Гаваї", "Territory of Hawaii", "USA"),
    (1959, 2025, "Штат США", "Гаваї (штат США)", "State of Hawaii", "USA"),
]


def run() -> None:
    with session_scope() as db:
        hi = db.execute(
            select(Territory).where(Territory.code == "US-HI")
        ).scalar_one_or_none()
        if hi is None:
            logger.warning("US-HI not found — run the `subdivisions` seeder first; skipping Hawaii periods")
            return

        already = db.execute(
            text("SELECT count(*) FROM territory_periods WHERE territory_id = :i"),
            {"i": hi.id},
        ).scalar()
        if already:
            logger.info("Hawaii already has %d periods, skipping", already)
            return

        usa = db.execute(
            select(Territory).where(Territory.code == "USA")
        ).scalar_one_or_none()
        usa_id = usa.id if usa else None

        src = get_or_create_source(
            db,
            short_title="Manual seed — Hawaii political status timeline",
            citation="Standard reference history of the Hawaiian Islands: "
            "Kingdom of Hawaii (unified 1795) → overthrow 1893 → Republic of "
            "Hawaii (1894) → US annexation 1898 → Territory of Hawaii "
            "(organised 1900) → US statehood 1959.",
            kind="manual",
            year=2026,
            notes="Reproducible: see backend/scripts/seed/hawaii.py",
        )

        for yf, yt, status, name_local, name, sov_code in PERIODS:
            p = TerritoryPeriod(
                territory_id=hi.id,
                year_from=yf,
                year_to=yt,
                status=status,
                name_local=name_local,
                name=name,
                sovereign_id=usa_id if sov_code == "USA" else None,
            )
            db.add(p)
            db.flush()
            db.add(TerritoryPeriodSource(period_id=p.id, source_id=src.id))
        logger.info("seeded %d Hawaii periods on territory %d", len(PERIODS), hi.id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
