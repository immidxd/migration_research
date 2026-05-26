"""Named research periods.

These are *labels* the researcher can attach to flows; they coexist with
raw date ranges on each flow. Easy to extend later.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from backend.models.periods import Period

from ._common import logger, session_scope


PERIODS = [
    {
        "slug": "first-wave",
        "name": "Перша хвиля переселення (1880–1914)",
        "date_from": date(1880, 1, 1),
        "date_to": date(1914, 7, 28),
        "description": "Масова трудова й селянська еміграція до США, Канади, Бразилії, "
        "Аргентини, а також внутрішньоімперські переселення до Сибіру й Далекого Сходу.",
    },
    {
        "slug": "wwi-civil-war",
        "name": "Перша світова та національно-визвольні змагання (1914–1921)",
        "date_from": date(1914, 7, 28),
        "date_to": date(1921, 3, 18),
        "description": "Військові переміщення, біженство, перші політичні еміграції.",
    },
    {
        "slug": "interwar",
        "name": "Міжвоєнний період (1921–1939)",
        "date_from": date(1921, 3, 18),
        "date_to": date(1939, 9, 1),
        "description": "Друга хвиля політичної еміграції; квотні обмеження США (1924) "
        "переорієнтували потоки на Канаду, Аргентину, Францію.",
    },
    {
        "slug": "wwii",
        "name": "Друга світова війна (1939–1945)",
        "date_from": date(1939, 9, 1),
        "date_to": date(1945, 9, 2),
        "description": "Депортації, остарбайтерство, переміщення.",
    },
    {
        "slug": "postwar-dp",
        "name": "Повоєнна еміграція DP (1945–1955)",
        "date_from": date(1945, 9, 2),
        "date_to": date(1955, 12, 31),
        "description": "Третя хвиля — переміщені особи (Displaced Persons).",
    },
]


def run() -> None:
    with session_scope() as db:
        for spec in PERIODS:
            exists = db.execute(
                select(Period).where(Period.slug == spec["slug"])
            ).scalar_one_or_none()
            if exists:
                logger.info("period %s already present, skipping", spec["slug"])
                continue
            db.add(Period(**spec))
            logger.info("seeded period %s", spec["slug"])


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    run()
