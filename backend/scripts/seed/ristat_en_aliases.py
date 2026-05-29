"""Add English aliases to every RiStat unit (gubernias + uezds) so the
typeahead finds them by English name too.

The ri_1897 importer stored each unit's English name inside its notes
("… English name: X."). We parse that out and register it as an `en` alias —
~900 units in one pass, no gpkg re-read or slug matching needed.

Idempotent on (territory_id, alias, language). Run after ri_1897.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy import select, text

from backend.models import SessionLocal
from backend.models.territories import TerritoryAlias

logger = logging.getLogger("migrations.seed")

_EN_RE = re.compile(r"English name:\s*(.+?)\s*\.?\s*$")


def run() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT id, notes FROM territories WHERE notes LIKE '%English name:%'"
        )).mappings().all()
        added = 0
        for r in rows:
            m = _EN_RE.search(r["notes"])
            if not m:
                continue
            en = m.group(1).strip()
            if not en:
                continue
            exists = db.execute(
                select(TerritoryAlias).where(
                    TerritoryAlias.territory_id == r["id"],
                    TerritoryAlias.alias == en,
                    TerritoryAlias.language == "en",
                )
            ).first()
            if exists:
                continue
            db.add(TerritoryAlias(territory_id=r["id"], alias=en, language="en"))
            added += 1
        db.commit()
        logger.info("ristat_en_aliases: added %d English aliases", added)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
