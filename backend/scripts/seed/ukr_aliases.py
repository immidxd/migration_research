"""Ukrainian + English aliases for the Russian-named RiStat gubernias, so the
typeahead finds them by their Ukrainian or English forms (Полтавська / Poltava
→ "Полтавская губерния"). Searched via territory_aliases in the search endpoint.

Idempotent on (territory_id, alias, language). Run after ri_1897.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from backend.models.territories import Territory, TerritoryAlias

from ._common import logger, session_scope


# code -> [(alias, language), ...]
ALIASES: dict[str, list[tuple[str, str]]] = {
    "ru-gub-poltava": [("Полтавська губернія", "uk"), ("Полтавщина", "uk"), ("Poltava", "en"), ("Poltava Governorate", "en")],
    "ru-gub-chernihiv": [("Чернігівська губернія", "uk"), ("Чернігівщина", "uk"), ("Chernihiv", "en"), ("Chernigov", "en")],
    "ru-gub-kyiv": [("Київська губернія", "uk"), ("Київщина", "uk"), ("Kyiv", "en"), ("Kiev", "en")],
    "ru-gub-podilska": [("Подільська губернія", "uk"), ("Поділля", "uk"), ("Podolia", "en"), ("Podilia", "en")],
    "ru-gub-volyn": [("Волинська губернія", "uk"), ("Волинь", "uk"), ("Volhynia", "en"), ("Volyn", "en")],
    "ru-gub-kharkiv": [("Харківська губернія", "uk"), ("Харківщина", "uk"), ("Kharkiv", "en"), ("Kharkov", "en")],
    "ru-gub-kherson": [("Херсонська губернія", "uk"), ("Херсонщина", "uk"), ("Kherson", "en")],
    "ru-gub-tavria": [("Таврійська губернія", "uk"), ("Таврія", "uk"), ("Taurida", "en"), ("Tavria", "en")],
    "ru-gub-katerynoslav": [("Катеринославська губернія", "uk"), ("Катеринославщина", "uk"), ("Katerynoslav", "en"), ("Yekaterinoslav", "en")],
    "ru-gub-bessarabia": [("Бессарабська губернія", "uk"), ("Бессарабія", "uk"), ("Bessarabia", "en")],
}


def run() -> None:
    with session_scope() as db:
        added = 0
        for code, aliases in ALIASES.items():
            terr = db.execute(
                select(Territory).where(Territory.code == code)
            ).scalar_one_or_none()
            if terr is None:
                logger.warning("territory %s not found — skipping aliases", code)
                continue
            for alias, lang in aliases:
                exists = db.execute(
                    select(TerritoryAlias).where(
                        TerritoryAlias.territory_id == terr.id,
                        TerritoryAlias.alias == alias,
                        TerritoryAlias.language == lang,
                    )
                ).first()
                if exists:
                    continue
                db.add(TerritoryAlias(territory_id=terr.id, alias=alias, language=lang))
                added += 1
        logger.info("ukr_aliases: added %d aliases", added)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
